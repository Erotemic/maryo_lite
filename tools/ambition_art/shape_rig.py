"""Pivot-centered part compositing in the original clockwise-positive convention."""
from PIL import Image

def place(canvas, part, at, degrees, name):
    image, pivot = part
    if not degrees:
        canvas.alpha_composite(image,(round(at[0]-pivot[0]),round(at[1]-pivot[1])))
        return
    # Pillow rotates counterclockwise; authored rig angles are clockwise.
    pad=max(image.width,image.height,round(max(pivot)*2))+8
    side=pad*2
    work=Image.new('RGBA',(side,side),(0,0,0,0))
    cx=cy=pad
    work.alpha_composite(image,(round(cx-pivot[0]),round(cy-pivot[1])))
    turned=work.rotate(-degrees,Image.Resampling.BICUBIC)
    canvas.alpha_composite(turned,(round(at[0]-cx),round(at[1]-cy)))
