from pathlib import Path
from PIL import Image
import numpy as np,json,hashlib
U=Path.cwd();E=U/'evidence/op-ed-source';D=U/'research/op-ed';ps=sorted((U/'source/decoded').glob('staffrollb_*.rct.png'));a=np.stack([np.asarray(Image.open(p)) for p in ps])
bands={1:[(224,251),(270,271),(295,320),(329,356)],2:[(209,234),(252,253),(278,305),(313,340),(348,375)],3:[(74,97),(116,117),(143,168),(178,203),(213,238),(248,273),(282,309),(317,343),(388,413),(422,449),(458,483),(492,519)],4:[(84,104),(124,125),(149,176),(219,246),(254,281),(289,316),(359,386),(394,421),(429,456),(499,526)],5:[(133,160),(179,180),(205,228),(240,263),(275,298),(310,333),(343,370),(378,405),(413,439)],6:[(52,75),(87,88),(105,127),(131,154),(157,180),(184,207),(236,258),(262,284),(289,312),(314,338),(341,364),(369,390),(420,443),(453,454),(474,493),(500,521),(525,547)],7:[(72,95),(101,102),(114,137),(203,227),(233,234),(244,267),(274,298),(364,386),(393,394),(404,429),(434,459),(464,488),(494,517)],8:[(106,129),(135,136),(149,172),(178,203),(238,261),(267,268),(280,304),(339,363),(369,370),(381,404),(441,465),(471,472),(482,506)],9:[(124,149),(154,155),(166,192),(257,281),(285,286),(297,322),(328,351),(358,381),(388,409),(417,440),(447,470)],10:[(130,153),(158,159),(171,196),(260,284),(289,290),(303,327),(392,415),(420,421),(434,458)],11:[(262,289),(297,298),(310,335)]}
blank=np.ones((11,600,800),bool)
for i in range(11):
 for y0,y1 in bands[i+1]:blank[i,max(0,y0-1):min(600,y1+1),198:603]=False
n=blank.sum(0);idx=blank.argmax(0);base=np.take_along_axis(a,idx[None,:,:,None],axis=0)[0];mismatch=np.any(a!=base,3)&blank;report={'blank_donor_count_distribution':{str(v):int((n==v).sum()) for v in np.unique(n)},'uncovered_pixels':int((n==0).sum()),'blank_disagreement_pixels_per_source':[int(x.sum()) for x in mismatch],'source_text_and_rule_bands':{str(i):bands[i] for i in bands},'source_text_x_exclusion':[198,603],'vertical_padding':1,'method':'Each pixel copied from a source whose separately identified glyph/rule bands do not occupy that row; all other blank donors must be byte-identical. No interpolation or generated texture.'}
(D/'staffrollb-blank-donor-study.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if not mismatch.any() and n.min()>0:
 Image.fromarray(base).save(E/'staffrollb-proven-clean.png');assert np.array_equal(np.asarray(Image.open(E/'staffrollb-proven-clean.png')),base);Image.fromarray(idx.astype('uint8')).save(E/'staffrollb-donor-index.png')
else:
 for i,m in enumerate(mismatch):
  if m.any():
   yy,xx=np.nonzero(m);print('conflict',i+1,list(zip(xx.tolist(),yy.tolist()))[:15])
