"""Ambition-style alpha-safe drawing for source procedural sprites."""
from PIL import Image, ImageDraw

def _alpha(ink):
    if ink is None:return None
    return ink[3] if isinstance(ink,(tuple,list)) and len(ink)==4 else 255

class _BlendingDraw:
    INKS={'polygon':('fill','outline'),'line':('fill',),'ellipse':('fill','outline'),
          'rectangle':('fill','outline'),'rounded_rectangle':('fill','outline'),
          'arc':('fill',),'chord':('fill','outline'),'pieslice':('fill','outline'),
          'point':('fill',)}
    POS_FILL={'polygon','line','ellipse','rectangle','point'}
    def __init__(self,img):
        self.img=img
        self.draw=ImageDraw.Draw(img,'RGBA') if img.mode in ('RGB','RGBA') else ImageDraw.Draw(img)
    def __getattr__(self,name):
        if name not in self.INKS:return getattr(self.draw,name)
        def call(*args,**kwargs):
            alphas=[_alpha(kwargs.get(k)) for k in self.INKS[name]]
            if len(args)>1 and name in self.POS_FILL:alphas.append(_alpha(args[1]))
            if self.img.mode=='RGBA' and any(a is not None and 0<a<255 for a in alphas):
                overlay=Image.new('RGBA',self.img.size,(0,0,0,0))
                getattr(ImageDraw.Draw(overlay,'RGBA'),name)(*args,**kwargs)
                self.img.alpha_composite(overlay)
            else:
                getattr(self.draw,name)(*args,**kwargs)
        return call

def blending_draw(img):return _BlendingDraw(img)
