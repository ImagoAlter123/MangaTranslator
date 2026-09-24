from languages import language_code
"""Optional local OCR and translation. No manga images are uploaded."""
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parent/'models'
os.environ.setdefault('HF_HOME',str(ROOT/'huggingface'))
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')
os.environ.setdefault('TORCH_HOME',str(ROOT/'torch'))


class LocalAI:
    def __init__(self):
        self.readers={}
        from translator_hy import HyTranslator
        self.translator=HyTranslator()

    def read(self,image,language,vertical=False,right_to_left=True):
        try:
            import easyocr
            import numpy as np
            import torch
            torch.set_num_threads(min(4,os.cpu_count() or 1))
        except ImportError as e:
            raise RuntimeError('Install AI with INSTALL_AI.cmd and try again.') from e
        code=language_code(language)
        if code not in self.readers:
            self.readers[code]=easyocr.Reader([code,'en'],gpu=False,verbose=False,
                model_storage_directory=str(ROOT/'ocr'),
                user_network_directory=str(ROOT/'ocr-user'))
        reader=self.readers[code]
        from vertical_ocr import vertical_lines
        from ocr_preprocess import outline_view
        import re
        def recognize(view,strength=0):
            columns=[];weighted=0;letters=0
            lines=vertical_lines(view,right_to_left,with_symbols=True,column_strength=strength) if vertical else [(view,'')]
            for strip,suffix in lines:
                results=reader.readtext(np.array(strip),detail=1,paragraph=False) if strip is not None else []
                if vertical:results.sort(key=lambda item:min(point[0] for point in item[0]))
                text=' '.join(item[1] for item in results)
                text=re.sub(r'(?<=[\u3040-\u30ff\u3400-\u9fff])\s+(?=[\u3040-\u30ff\u3400-\u9fff])','',text)
                text=text.strip()+suffix
                if text:columns.append(text)
                for box,token,confidence in results:
                    length=sum(1 if '\u3040'<=c<='\u9fff' else .35 for c in token if c.isalnum())
                    letters+=length;weighted+=float(confidence)*length
            # Length matters, but cannot overwhelm low recognition confidence.
            average=weighted/letters if letters else 0
            score=average*(letters**.5)
            return '\n'.join(columns),score,average,letters
        candidates=[recognize(image)]
        clean=outline_view(image)
        if clean is not None:candidates.append(recognize(clean,.25))
        best=max(candidates,key=lambda candidate:candidate[1])
        if not best[3] or best[2]<.12:
            for candidate in candidates:
                if candidate[0] and re.fullmatch(r'[♥♡…\s]+',candidate[0]):return candidate[0]
            raise ValueError('OCR could not reliably read this selection. Adjust the area to include only text and check the language and vertical option. The previous source text was kept.')
        return best[0]

    def translate(self,text,language,context='',glossary=''):
        return self.translator.translate(text,language,context,glossary)

    def close(self):
        self.translator.close()
