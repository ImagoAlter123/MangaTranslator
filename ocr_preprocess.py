"""Disposable OCR views; never modifies the page or its background patches."""
import cv2
import numpy as np
from PIL import Image


def outline_view(image):
    gray=np.array(image.convert('L'))
    white=(gray>235).astype('uint8')
    contours,_=cv2.findContours(white,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    filled=np.zeros_like(gray)
    for contour in contours:
        if cv2.contourArea(contour)>15:cv2.drawContours(filled,[contour],-1,255,-1)
    dark=gray<130;inside=dark&(filled>0)
    if inside.sum()<20 or dark.sum()==0:return None
    # A clean white balloon needs no special treatment. An outlined text view
    # must remove a meaningful amount of outside background ink.
    if (dark.sum()-inside.sum())/dark.sum()<.12:return None
    out=np.full(gray.shape,255,np.uint8);out[inside]=0
    return Image.fromarray(out).convert('RGB')
