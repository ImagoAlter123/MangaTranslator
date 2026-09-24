"""Reflow upright vertical glyphs, keeping disconnected strokes together."""
import cv2
import numpy as np
from PIL import Image


def spans(values):
    result=[];start=None
    for i,value in enumerate(list(values)+[False]):
        if value and start is None:start=i
        if not value and start is not None:result.append((start,i));start=None
    return result


def vertical_lines(image,right_to_left=True,with_symbols=False,column_strength=0):
    image=image.convert('RGB')
    gray=np.array(image.convert('L'))
    _,ink=cv2.threshold(gray,0,1,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    # Remove only thin crop-edge frame lines, never interior text components.
    n,labels,stats,_=cv2.connectedComponentsWithStats(ink)
    for i,(x,y,w,h,area) in enumerate(stats[1:],1):
        if (h>image.height*.85 and w<image.width*.08 and (x<3 or x+w>image.width-3)) or (w>image.width*.85 and h<image.height*.03 and (y<3 or y+h>image.height-3)):
            ink[labels==i]=0
    projection=ink.sum(axis=0)
    occupied=(projection>max(1,image.height*.002,float(projection.max())*column_strength)).astype('uint8')[None,:]
    occupied=cv2.morphologyEx(occupied,cv2.MORPH_CLOSE,np.ones((1,max(3,round(image.width*.035))),np.uint8))[0]
    columns=spans(occupied)
    if column_strength:
        columns=[(max(0,a-2),min(image.width,b+2)) for a,b in columns if b-a>=max(4,image.width*.075)]
    if right_to_left:columns.reverse()
    strips=[]
    for x0,x1 in columns:
        if x1-x0<3:continue
        from ocr_symbols import terminal_symbol
        suffix=terminal_symbol(ink[:,x0:x1],x1-x0)
        end=suffix[0] if suffix else image.height
        rows=spans(ink[:end,x0:x1].sum(axis=1)>0)
        if not rows:
            if with_symbols and suffix:strips.append((None,suffix[1]))
            continue
        width=x1-x0;count=len(rows);cost=[None]*(count+1);cost[count]=(0,[])
        for i in range(count-1,-1,-1):
            for j in range(i+1,count+1):
                y0,y1=rows[i][0],rows[j-1][1];height=y1-y0
                if height>width*1.4 and j>i+1:break
                xx=np.where(ink[y0:y1,x0:x1].any(axis=0))[0]
                glyph_width=(xx[-1]-xx[0]+1) if len(xx) else width
                punctuation=height<width*.45 and glyph_width<width*.5
                penalty=.8 if punctuation else 1+4*((height-width*.95)/width)**2
                penalty+=sum(max(0,rows[k+1][0]-rows[k][1]-width*.12) for k in range(i,j-1))/width*3
                candidate=(penalty+cost[j][0],[(y0,y1)]+cost[j][1])
                if cost[i] is None or candidate[0]<cost[i][0]:cost[i]=candidate
        pieces=[image.crop((x0,y0,x1,y1)) for y0,y1 in cost[0][1]]
        cell=max(width,max(p.height for p in pieces))+4
        strip=Image.new('RGB',(cell*len(pieces)+24,cell+24),'white')
        for k,piece in enumerate(pieces):strip.paste(piece,(12+k*cell+(cell-piece.width)//2,12+(cell-piece.height)//2))
        # Upsample small crops for recognition without rotating the glyphs.
        if strip.height<80:strip=strip.resize((strip.width*2,strip.height*2),Image.Resampling.LANCZOS)
        strips.append((strip,suffix[1] if suffix else '') if with_symbols else strip)
    return strips
