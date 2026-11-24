from pathlib import Path
import urllib.request,re,json
p=Path('research/op-all-japanese-v3/official-reference/wallpaper-page.html')
with urllib.request.urlopen('https://life1001.blog50.fc2.com/blog-entry-1049.html',timeout=15) as r:b=r.read()
p.write_bytes(b);s=b.decode('utf-8','replace');print('\n'.join(list(dict.fromkeys(re.findall(r'(?:href|src)=[\"\']([^\"\']+\.(?:jpe?g|png)(?:[^\"\']*)?)',s,re.I)))))