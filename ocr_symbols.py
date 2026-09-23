"""Conservative recognition of terminal hearts and vertical ellipses."""
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from functools import lru_cache


def normalized(binary):
    y,x=np.where(binary>0)
    if not len(x):return np.zeros((48,48),bool)
    crop=binary[y.min():y.max()+1,x.min():x.max()+1].astype('uint8')
    return cv2.resize(crop,(48,48),interpolation=cv2.INTER_NEAREST)>0


@lru_cache(maxsize=1)
def hearts():
    templates=[]
    for name in ['C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/seguisym.ttf']:
        try:
            f=ImageFont.truetype(name,80);im=Image.new('L',(120,120),0)
            ImageDraw.Draw(im).text((10,0),'♥',font=f,fill=255)
            templates.append(normalized(np.array(im)>120))
        except OSError:pass
    t=np.linspace(0,2*np.pi,200)
    x=16*np.sin(t)**3;y=-(13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t))
    pts=np.column_stack(((x-x.min())/(x.max()-x.min())*47,(y-y.min())/(y.max()-y.min())*47)).astype('int32')
    a=np.zeros((48,48),np.uint8);cv2.fillPoly(a,[pts],1);templates.append(a>0)
    return templates


def terminal_symbol(ink,width):
    n,labels,stats,centers=cv2.connectedComponentsWithStats(ink.astype('uint8'))
    ids=sorted([i for i in range(1,n) if stats[i,4]>=2],key=lambda i:stats[i,1]+stats[i,3])
    if not ids:return None
    if len(ids)>=3:
        last=ids[-3:];s=stats[last];c=centers[last]
        dots=all(1<=w<=width*.3 and 1<=h<=width*.3 and .45<=w/h<=2 and area/(w*h)>.4 for x,y,w,h,area in s)
        gaps=np.diff(c[:,1])
        if dots and np.ptp(c[:,0])<width*.18 and np.all((gaps>width*.10)&(gaps<width*.65)):
            top=int(s[:,1].min())
            others=[i for i in ids if i not in last]
            if not others or max(stats[i,1]+stats[i,3] for i in others)<top-width*.06:
                return top,'…'
    last=ids[-1];x,y,w,h,area=stats[last]
    if w>=width*.40 and h>=width*.4 and .55<w/h<1.5 and area/(w*h)>.55:
        shape=normalized(labels[y:y+h,x:x+w]==last)
        score=max(np.logical_and(shape,t).sum()/np.logical_or(shape,t).sum() for t in hearts())
        if score>.76:return int(y),'♥'
    return None
