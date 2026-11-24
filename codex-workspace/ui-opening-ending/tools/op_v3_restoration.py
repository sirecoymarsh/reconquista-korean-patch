"""Frame registration and masked video restoration. Hidden original RGB is not claimed."""
from pathlib import Path
from functools import lru_cache
import cv2,numpy as np
from PIL import Image
U=Path(__file__).resolve().parents[1];R=U/'research/op-all-japanese-v3';O=U/'candidates/opening-video-ko-v3';P=O/'build-source/restoration';cv2.setNumThreads(2)
Y,X=np.mgrid[:600,:800];CLIP=(Y>=72)&(Y<525);SIFT=cv2.SIFT_create(nfeatures=2200,contrastThreshold=.012);BF=cv2.BFMatcher()
def read(n):
 p=R/'dense-frames'/f'{n:04d}.png'
 if not p.exists():p=R/'source-frames'/f'{n:04d}.png'
 return np.array(Image.open(p).convert('RGB'))
def load(p):return np.array(Image.open(p).convert('RGB'))
def mask(k):return np.array(Image.open(P/(k+'-mask.png')).convert('L'))>0
def features(a,exclude=None):
 g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);g=cv2.createCLAHE(2,(8,8)).apply(g);m=None if exclude is None else (~exclude).astype('uint8')*255;return SIFT.detectAndCompute(g,m)
def register(src,dst,exclude=None,src_exclude=None):
 ka,da=features(src,src_exclude);kb,db=features(dst,exclude)
 if da is None or db is None:return None,0
 mm=[a for a,b in BF.knnMatch(da,db,k=2) if a.distance<.76*b.distance];unique={}
 for m in sorted(mm,key=lambda x:x.distance):unique.setdefault(m.trainIdx,m)
 mm=list(unique.values())
 if len(mm)<5:return None,0
 H,inl=cv2.estimateAffine2D(np.float32([ka[m.queryIdx].pt for m in mm]),np.float32([kb[m.trainIdx].pt for m in mm]),method=cv2.RANSAC,ransacReprojThreshold=2.2,maxIters=3000)
 if H is None:return None,0
 count=int(inl.sum());sv=np.linalg.svd(H[:,:2])[1]
 if count<5 or not .03<abs(np.linalg.det(H[:,:2]))<30 or sv[0]/max(.001,sv[-1])>2:return None,count
 return H,count

def warp(a,H,nearest=False):return cv2.warpAffine(a,H,(800,600),flags=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
def global_tone(src,target,valid):
 # Robust affine color fit. Saturated text outliers are rejected at each step.
 yy,xx=np.where(valid);step=max(1,len(yy)//18000);yy=yy[::step];xx=xx[::step];A=np.c_[src[yy,xx].astype('float32'),np.ones(len(yy),np.float32)];B=target[yy,xx].astype('float32');keep=np.ones(len(yy),bool)
 if len(yy)<20:return np.eye(4,3,dtype='float32')
 for _ in range(5):
  c=np.linalg.lstsq(A[keep],B[keep],rcond=.0001)[0];err=np.max(np.abs(A@c-B),1);keep=err<max(2,np.quantile(err,.72))
 return c

def toned(src,donor,target,m,source_mask=None,H=None,local=True):
 if H is not None:
  src=warp(src,H);donor=warp(donor,H)
  if source_mask is not None:source_mask=warp(source_mask.astype('uint8'),H,True)>0
 valid=CLIP&~m
 if source_mask is not None:valid&=~source_mask
 c=global_tone(src,target,valid);pred=donor.astype('float32')@c[:3]+c[3];baseline=src.astype('float32')@c[:3]+c[3]
 if local:
  vv=valid.astype('float32');den=np.maximum(cv2.GaussianBlur(vv,(0,0),14),1e-5)
  for ch in range(3):pred[:,:,ch]+=np.clip(cv2.GaussianBlur((target[:,:,ch]-baseline[:,:,ch])*vv,(0,0),14)/den,-20,20)
 return np.clip(pred,0,255)

def merge(target,pred,m,feather=4):
 m=m&CLIP;dist=cv2.distanceTransform(m.astype('uint8'),cv2.DIST_L2,3);w=np.clip(dist/feather,0,1);out=np.clip(np.rint(target*(1-w[:,:,None])+pred*w[:,:,None]),0,255).astype('uint8');assert np.array_equal(out[~m],target[~m]);return out

def poly_background(a,m,limit=260):
 x=X/800.;y=Y/600.;terms=np.stack([x**i*y**j for i in range(4) for j in range(4-i)],2);valid=CLIP&(X<limit)&~cv2.dilate(m.astype('uint8'),np.ones((11,11),np.uint8)).astype(bool);A=terms[valid][::2];B=a[valid][::2];keep=np.ones(len(A),bool)
 for _ in range(4):
  c=np.linalg.lstsq(A[keep],B[keep],rcond=None)[0];e=np.max(abs(A@c-B),1);keep=e<np.quantile(e,.8)
 return np.clip(terms@c,0,255)