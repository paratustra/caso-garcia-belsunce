# usage: webp_to_pdf.py <volume_dir> <out.pdf> — joins foja-*.webp (folio images) in order into one PDF (JPEG q70)
import sys, glob
from PIL import Image
pages = sorted(glob.glob(sys.argv[1] + "/foja-*.webp"))
def imgs():
    for p in pages[1:]:
        yield Image.open(p).convert("RGB")
first = Image.open(pages[0]).convert("RGB")
first.save(sys.argv[2], "PDF", resolution=200, save_all=True, append_images=imgs(), quality=70)
print(sys.argv[2], len(pages))
