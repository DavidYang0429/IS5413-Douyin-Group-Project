"""Copy only public browser assets into Vercel's static output directory."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
shutil.copytree(root / 'static', root / 'public', dirs_exist_ok=True)
