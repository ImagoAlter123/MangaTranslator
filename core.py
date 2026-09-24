"""Local image processing. Project coordinates are always image pixels."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import io, json, zipfile, re, math
from functools import lru_cache
from text_cleanup import normalize_translation
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

DEFAULT_FONT=Path(__file__).resolve().parent/'fonts'/'CC Wild Words Roman.ttf'


@dataclass
class Region:
    erase: list
    text_box: list
    original: str = ''
    translation: str = ''
    size: int = 30
    auto_fit: bool = False
    enabled: bool = False
    transparent: bool = False
    outline: int = 0
    text_color: str = "black"
    outline_color: str = "white"
    text_shape: str = "rectangle"
    erase_shape: str = "rectangle"
    corner_rounding: int = 50
    text_angle: int = 0

    def __post_init__(self):
        self.translation=normalize_translation(self.translation)


@dataclass
class BackgroundPatch:
    box: list
    image: Image.Image


@dataclass
class Page:
    image: Image.Image
    regions: list = field(default_factory=list)
    dpi: float = 144.0
    patches: list = field(default_factory=list)


def load_pages(path):
    if Path(path).suffix.lower() == '.pdf':
        result = []
        with pdfium.PdfDocument(str(path)) as doc:
            for page in doc:
                bitmap = page.render(scale=2)
                result.append(Page(bitmap.to_pil().convert('RGB').copy()))
                bitmap.close()
                page.close()
        return result
    with Image.open(path) as image:
        dpi = image.info.get('dpi', (144, 144))[0]
        return [Page(image.convert('RGB').copy(), dpi=float(dpi or 144))]


def load_multiple(paths):
    """Import full-resolution files in natural filename order, atomically."""
    def order(path):
        return tuple((1,int(part)) if part.isdigit() else (0,part.casefold())
                     for part in re.split(r'(\d+)',Path(path).name))
    result=[]
    for path in sorted(paths,key=order):
        try:result.extend(load_pages(path))
        except Exception as error:
            raise ValueError(f'Could not open {Path(path).name}: {error}. Import canceled; the previous project was kept.') from error
    return result


def detect_bubbles(image):
    """Conservative geometric candidates, NOT a trained speech balloon detector.

    Closed white ovals with dark interior components. Rectangular narration
    boxes and regions touching image edges are excluded. Never erase on detect.
    """
    scale = min(1, 1800 / max(image.size))
    small = image.resize((round(image.width*scale), round(image.height*scale)))
    gray = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2GRAY)
    white = (gray > 235).astype('uint8') * 255
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    found = []
    for contour in contours:
        x,y,bw,bh = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if x < 2 or y < 2 or x+bw >= w-2 or y+bh >= h-2:
            continue
        if area < w*h*.0008 or area > w*h*.08 or min(bw,bh) < 22:
            continue
        fill = area/(bw*bh)
        if not .57 < fill < .91 or not .18 < bw/bh < 5:
            continue
        mask = np.zeros_like(gray)
        cv2.drawContours(mask,[contour],-1,255,-1)
        margin = max(3, round(min(bw,bh)*.09))
        mask = cv2.erode(mask,np.ones((margin*2+1,margin*2+1),np.uint8))
        ink = ((gray < 150) & (mask > 0)).astype('uint8')
        n, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
        parts = [s for s in stats[1:] if s[4] >= 5 and s[2] > 1 and s[3] > 2]
        if len(parts) < 3:
            continue
        left=min(s[0] for s in parts); top=min(s[1] for s in parts)
        right=max(s[0]+s[2] for s in parts); bottom=max(s[1]+s[3] for s in parts)
        rect = [max(x+margin,left-3), max(y+margin,top-3), min(x+bw-margin,right+3), min(y+bh-margin,bottom+3)]
        # Require the entire white cover to stay inside the eroded balloon.
        if not np.all(mask[rect[1]:rect[3],rect[0]:rect[2]]):
            continue
        erase=[round(v/scale) for v in rect]
        text=[round(v/scale) for v in [x+bw*.20,y+bh*.16,x+bw*.80,y+bh*.84]]
        found.append(Region(erase,text,size=max(12,round(bw*.17/scale))))
    return sorted(found,key=lambda r:(r.erase[1],-r.erase[0]))


@lru_cache(maxsize=128)
def font_at(path, size):
    if not path and DEFAULT_FONT.exists():path=str(DEFAULT_FONT)
    if path:
        return ImageFont.truetype(path,size)
    try:
        return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    except OSError:
        return ImageFont.load_default(size=size)


def measurable(text):
    # Reserve supported glyph widths for vector symbols missing in CC Wild Words.
    return text.replace('♥','O').replace('♡','O').replace('—','M').replace('–','N')


def draw_dialogue(draw,xy,text,font,stroke=0,color="black",outline_color=None):
    # Restore all glyph faces after drawing the halos, so thick outlines on
    # later lines or vector symbols cannot cover previously drawn letters.
    if outline_color is None:outline_color="black" if color=="white" else "white"
    if stroke:_draw_dialogue_pass(draw,xy,text,font,stroke,color,outline_color)
    _draw_dialogue_pass(draw,xy,text,font,0,color,outline_color)


def _draw_dialogue_pass(draw,xy,text,font,stroke=0,color="black",edge="white"):
    lines=text.split('\n');widths=[draw.textlength(measurable(line),font=font) for line in lines]
    line_step=draw.textbbox((0,0),'A',font=font)[3]+2
    max_width=max(widths,default=0)
    for number,line in enumerate(lines):
        x=xy[0]+(max_width-widths[number])/2;y=xy[1]+number*line_step
        # Keep normal runs intact so kerning is preserved.
        for run in re.split('([♥♡—–])',line):
            if not run:continue
            if run in ('♥','♡'):
                width=draw.textlength('O',font=font);b=draw.textbbox((0,0),'O',font=font)
                points=[]
                for i in range(121):
                    t=i/120*2*math.pi;hx=16*math.sin(t)**3;hy=-(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))
                    points.append((x+width*(.08+.84*(hx+16)/32),y+b[1]+(b[3]-b[1])*(hy+12)/29))
                if stroke:draw.line(points,fill=edge,width=stroke*2+1,joint='curve')
                if run=='♥':draw.polygon(points,fill=color)
                else:draw.line(points,fill=color,width=max(1,round(font.size*.045)),joint='curve')
                x+=width
            elif run in ('—','–'):
                width=draw.textlength('M' if run=='—' else 'N',font=font)
                b=draw.textbbox((0,0),'O',font=font)
                middle=y+(b[1]+b[3])/2;thickness=max(1,round(font.size*.055))
                box=[x+width*.08,middle-thickness/2,x+width*.92,middle+thickness/2]
                if stroke:draw.rectangle([box[0]-stroke,box[1]-stroke,box[2]+stroke,box[3]+stroke],fill=edge)
                draw.rectangle(box,fill=color);x+=width
            else:
                draw.text((x,y),run,font=font,fill=color,stroke_width=stroke,stroke_fill=edge)
                x+=draw.textlength(run,font=font)


def _wrap(paragraph, font, width, draw):
    """Minimum line count, then balance lengths without breaking words."""
    words=paragraph.split()
    if not words:return ['']
    # Bound DP work for accidentally pasted chapters.
    if len(words)>250:
        lines=[];line=''
        for word in words:
            candidate=(line+' '+word).strip()
            if line and draw.textlength(measurable(candidate),font=font)>width:
                lines.append(line);line=word
            else:line=candidate
        return lines+[line]
    n=len(words); cost=[None]*(n+1);cost[n]=(0,0,[])
    for i in range(n-1,-1,-1):
        for j in range(i+1,n+1):
            line=' '.join(words[i:j]); length=draw.textlength(measurable(line),font=font)
            if length>width and j>i+1:break
            tail=cost[j]
            candidate=(tail[0]+1,tail[1]+(width-length)**2,[line]+tail[2])
            if cost[i] is None or candidate[:2]<cost[i][:2]:cost[i]=candidate
            if length>width:break
    return cost[0][2]


@lru_cache(maxsize=256)
def _layout(text, box, font_path, manual_size, auto_fit):
    margin=max(2,min(14,round(min(box[2]-box[0],box[3]-box[1])*.055)))
    width=max(1,box[2]-box[0]-2*margin);height=max(1,box[3]-box[1]-2*margin)
    draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
    def measure(size):
        font=font_at(font_path,size)
        lines=[line for paragraph in text.split('\n') for line in _wrap(paragraph,font,width,draw)]
        joined='\n'.join(lines)
        bounds=draw.multiline_textbbox((0,0),measurable(joined),font=font,spacing=2,align='center')
        return joined,font,bounds,bounds[2]-bounds[0]<=width and bounds[3]-bounds[1]<=height
    if not auto_fit or not text.strip():return measure(max(6,manual_size))
    # The manual value is NOT an upper limit. Grow to fill the available box.
    lo=6;hi=min(2048,max(6,int(max(width,height)*2)));best=measure(6)
    while lo<=hi:
        middle=(lo+hi)//2;candidate=measure(middle)
        if candidate[3]:best=candidate;lo=middle+1
        else:hi=middle-1
    return best


def layout(text, box, font_path, maximum, auto_fit):
    return _layout(normalize_translation(text),tuple(box),font_path,maximum,auto_fit)


def background_image(page):
    image=page.image.copy()
    for patch in page.patches:image.paste(patch.image,(patch.box[0],patch.box[1]))
    return image


def region_layout(region,font_path):
    b=region.text_box;s=region.outline
    if region.text_shape=='rounded':
        return oval_layout(region.translation,b,font_path,region.size,s,region.corner_rounding)
    if region.text_shape=='oval':
        return oval_layout(region.translation,b,font_path,region.size,s)
    return layout(region.translation,[b[0]+s,b[1]+s,b[2]-s,b[3]-s],font_path,region.size,region.auto_fit)


def oval_layout(text,box,font_path,size,stroke=0,rounding=None):
    """Wrap into centered elliptical rows without shrinking the user's font."""
    font=font_at(font_path,size);draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
    width=max(1,box[2]-box[0]-2*stroke-8);height=max(1,box[3]-box[1]-2*stroke-8)
    step=draw.textbbox((0,0),'A',font=font)[3]+2
    words=normalize_translation(text).split()
    # Explicit line breaks remain authoritative. Bound work on long pasted text.
    if '\n' in normalize_translation(text) or len(words)>100 or not words:
        return layout(text,box,font_path,size,False)
    for count in range(1,min(len(words),max(1,int(height/step)))+1):
        widths=[width*math.sqrt(max(0,1-((2*i-count+1)*step/height)**2)) for i in range(count)]
        if rounding is not None:
            radius=min(width,height)*max(0,min(100,rounding))/200
            widths=[]
            for i in range(count):
                y=abs((2*i-count+1)*step/2)+step/2
                delta=max(0,y-(height/2-radius))
                widths.append(width-2*(radius-math.sqrt(max(0,radius*radius-delta*delta))))
        @lru_cache(None)
        def solve(start,row):
            if row==count:return (0,[]) if start==len(words) else None
            best=None
            for end in range(start+1,len(words)+1):
                line=' '.join(words[start:end]);length=draw.textlength(measurable(line),font=font)
                if length>widths[row]:break
                tail=solve(end,row+1)
                if tail is not None:
                    candidate=((widths[row]-length)**2+tail[0],[line]+tail[1])
                    if best is None or candidate[0]<best[0]:best=candidate
            return best
        result=solve(0,0)
        if result:
            joined='\n'.join(result[1]);bounds=draw.multiline_textbbox((0,0),measurable(joined),font=font,spacing=2,align='center')
            return joined,font,bounds,True
    # Overflow is permitted, exactly as in rectangular mode.
    return layout(text,box,font_path,size,False)


def render_page(page, font_path='', strict=False):
    image=background_image(page); draw=ImageDraw.Draw(image); warnings=[]
    for idx,r in enumerate(page.regions):
        if not r.enabled:
            continue
        if not r.translation.strip():
            warnings.append(f'Balloon {idx+1}: empty translation; original preserved.'); continue
        text,font,bounds,fits=region_layout(r,font_path)
        # The selection controls positioning, not clipping or export validity.
        # Oversized text is intentionally rendered at the requested size.
        if not r.transparent:
            if r.text_angle:
                ew=max(1,r.erase[2]-r.erase[0]);eh=max(1,r.erase[3]-r.erase[1])
                cover=Image.new('RGBA',(ew+4,eh+4),(0,0,0,0));cover_draw=ImageDraw.Draw(cover);cover_box=[2,2,ew+1,eh+1]
                if r.erase_shape=='oval':cover_draw.ellipse(cover_box,fill='white')
                elif r.erase_shape=='rounded':cover_draw.rounded_rectangle(cover_box,radius=min(ew,eh)*max(0,min(100,r.corner_rounding))/200,fill='white')
                else:cover_draw.rectangle(cover_box,fill='white')
                cover=cover.rotate(-r.text_angle,resample=Image.Resampling.BICUBIC,expand=True)
                ex=(r.erase[0]+r.erase[2])/2;ey=(r.erase[1]+r.erase[3])/2
                image.paste(cover,(round(ex-cover.width/2),round(ey-cover.height/2)),cover)
            elif r.erase_shape=='oval':draw.ellipse(r.erase,fill='white')
            elif r.erase_shape=='rounded':draw.rounded_rectangle(r.erase,radius=min(r.erase[2]-r.erase[0],r.erase[3]-r.erase[1])*max(0,min(100,r.corner_rounding))/200,fill='white')
            else:draw.rectangle(r.erase,fill='white')
        x=(r.text_box[0]+r.text_box[2]-(bounds[2]-bounds[0]))/2-bounds[0]
        y=(r.text_box[1]+r.text_box[3]-(bounds[3]-bounds[1]))/2-bounds[1]
        if r.text_angle:
            # Render a padded transparent tile so glyphs outside the box survive rotation.
            pad=r.outline+4;tw=max(1,math.ceil(bounds[2]-bounds[0])+2*pad);th=max(1,math.ceil(bounds[3]-bounds[1])+2*pad)
            tile=Image.new('RGBA',(tw,th),(0,0,0,0))
            draw_dialogue(ImageDraw.Draw(tile),(pad-bounds[0],pad-bounds[1]),text,font,r.outline,r.text_color,r.outline_color)
            tile=tile.rotate(-r.text_angle,resample=Image.Resampling.BICUBIC,expand=True)
            cx=(r.text_box[0]+r.text_box[2])/2;cy=(r.text_box[1]+r.text_box[3])/2
            image.paste(tile,(round(cx-tile.width/2),round(cy-tile.height/2)),tile)
        else:draw_dialogue(draw,(x,y),text,font,r.outline,r.text_color,r.outline_color)
    return image,warnings


def export_webp_zip(path,pages,font_path=''):
    """Render one page at a time; publish the archive only after all succeed."""
    import tempfile,os
    from PIL import features
    if not pages:raise ValueError('Open some pages before exporting.')
    if not features.check('webp'):raise RuntimeError('WebP support is unavailable. Run INSTALL.cmd to repair Pillow.')
    path=Path(path)
    fd,temp_name=tempfile.mkstemp(prefix='.webp-export-',suffix='.tmp',dir=path.parent)
    os.close(fd);temp=Path(temp_name)
    try:
        digits=max(3,len(str(len(pages))))
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_STORED) as archive:
            for i,page in enumerate(pages,1):
                rendered,warnings=render_page(page,font_path,strict=True)
                if warnings:raise ValueError(f'Page {i}: '+ '\n'.join(warnings))
                with io.BytesIO() as buffer:
                    rendered.save(buffer,format='WEBP',lossless=True,method=4)
                    archive.writestr(f'page-{i:0{digits}d}.webp',buffer.getvalue())
        temp.replace(path)
    finally:
        if temp.exists():temp.unlink()
    return str(path)


def save_project(path,pages,font_path,settings=None):
    temp=Path(str(path)+'.tmp')
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
            meta={'version':5,'font':font_path,'settings':settings or {},'pages':[]}
            for i,p in enumerate(pages):
                buf=io.BytesIO(); p.image.save(buf,format='PNG')
                z.writestr(f'{i}.png',buf.getvalue())
                patches=[]
                for j,patch in enumerate(p.patches):
                    name=f'patch-{i}-{j}.png';buf=io.BytesIO();patch.image.save(buf,format='PNG');z.writestr(name,buf.getvalue())
                    patches.append({'box':patch.box,'file':name})
                regions=[dict(asdict(r),translation=normalize_translation(r.translation)) for r in p.regions]
                meta['pages'].append({'dpi':p.dpi,'regions':regions,'patches':patches})
            z.writestr('project.json',json.dumps(meta,ensure_ascii=False))
        temp.replace(path)
    finally:
        if temp.exists(): temp.unlink()


def load_project(path,with_settings=False):
    with zipfile.ZipFile(path) as z:
        meta=json.loads(z.read('project.json'))
        if meta['version'] not in (1,2,3,4,5): raise ValueError('Unsupported project version.')
        pages=[]
        for i,p in enumerate(meta['pages']):
            image=Image.open(io.BytesIO(z.read(f'{i}.png'))).convert('RGB')
            patches=[BackgroundPatch(item['box'],Image.open(io.BytesIO(z.read(item['file']))).convert('RGB')) for item in p.get('patches',[])]
            # Preserve the automatic contrast used by older project versions.
            regions=[]
            for r in p['regions']:
                if 'outline_color' not in r:r['outline_color']='black' if r.get('text_color')=='white' else 'white'
                regions.append(Region(**r))
            pages.append(Page(image,regions,p['dpi'],patches))
        result=(pages,meta.get('font',''))
        return result+(meta.get('settings',{}),) if with_settings else result
