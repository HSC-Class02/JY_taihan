"""Create a GitHub-uploadable ZIP without hidden files or folders."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT.parent/'Taihan_OpenDART_Agent.zip'
excluded={'.git','.github','.env','__pycache__','.DS_Store'}
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if p.is_file() and not any(x.startswith('.') or x in excluded for x in rel.parts): z.write(p, Path(ROOT.name)/rel)
print(OUT)
