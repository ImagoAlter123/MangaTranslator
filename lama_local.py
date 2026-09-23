"""Local CPU inference for the LaMa TorchScript export distributed by IOPaint."""
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image

MODEL = Path(__file__).resolve().parent/'models'/'lama'/'big-lama.pt'
URL = 'https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt'
MD5 = 'e3aa4aaa15225a33ec84f9f4bc47e500'


def valid_model():
    if not MODEL.is_file():return False
    with MODEL.open('rb') as f:
        return hashlib.file_digest(f, 'md5').hexdigest() == MD5


def install():
    from baixar_modelos import get_json, download
    if valid_model():
        print('LaMa ja instalado e validado.', flush=True)
        return
    release = get_json('https://api.github.com/repos/Sanster/models/releases/tags/add_big_lama')
    asset = next(a for a in release['assets'] if a['name']=='big-lama.pt')
    digest = asset.get('digest') or ''
    # Replace a corrupt existing file; never accept its size alone.
    if MODEL.exists():MODEL.unlink()
    download(URL, MODEL, asset['size'], digest[7:] if digest.startswith('sha256:') else None)
    if not valid_model():
        MODEL.unlink()
        raise RuntimeError('O modelo LaMa falhou na verificacao. Execute BAIXAR_LAMA.cmd novamente.')


def inpaint(image, mask):
    source = np.array(image.convert('RGB'))
    selected = np.array(mask.convert('L')) > 0
    if mask.size != image.size:raise ValueError('Mascara e imagem devem ter o mesmo tamanho.')
    if not selected.any():raise ValueError('Marque as letras e seu contorno antes de gerar a previa.')
    if selected.all():raise ValueError('Deixe fundo limpo ao redor para servir de referencia.')
    if not valid_model():raise RuntimeError('LaMa ausente ou incompleto. Feche o aplicativo e execute BAIXAR_LAMA.cmd na pasta dele.')
    import torch
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    # Bound CPU memory use; merge only selected pixels at the original resolution.
    scale = min(1., 1024/max(image.size))
    size = tuple(max(1, round(v*scale)) for v in image.size)
    rgb = np.array(image.convert('RGB').resize(size, Image.Resampling.LANCZOS))
    m = np.array(Image.fromarray(selected.astype('uint8')*255).resize(size, Image.Resampling.BOX)) > 0
    h,w = m.shape
    rgb = np.pad(rgb, ((0,(-h)%8),(0,(-w)%8),(0,0)), mode='symmetric')
    m = np.pad(m, ((0,(-h)%8),(0,(-w)%8)), mode='symmetric')
    # File object supports Windows paths with accented characters.
    with MODEL.open('rb') as f:model = torch.jit.load(f, map_location='cpu').eval()
    try:
        with torch.inference_mode():
            result = model(torch.from_numpy(rgb.transpose(2,0,1).copy()).float()[None]/255,
                           torch.from_numpy(m.copy()).float()[None,None])
            result = result[0,:,:h,:w].permute(1,2,0).cpu().numpy()
        if not np.isfinite(result).all():raise RuntimeError('LaMa retornou uma imagem invalida.')
        repaired = Image.fromarray(np.clip(result*255,0,255).astype('uint8')).resize(image.size, Image.Resampling.LANCZOS)
        source[selected] = np.array(repaired)[selected]
        return Image.fromarray(source)
    finally:
        del model


if __name__ == '__main__':
    try:
        install()
        # Exercise actual model loading and inference on the destination machine.
        sample = Image.new('RGB',(64,64),(128,128,128))
        mask = Image.new('L',sample.size);mask.paste(255,(24,24,40,40))
        result = inpaint(sample,mask)
        result.save(MODEL.parent/'teste-lama.png')
        print('LaMa pronto. Teste real de reconstrucao concluido.',flush=True)
    except Exception as error:
        print('ERRO: '+str(error),flush=True)
        raise SystemExit(1)
