"""Run explicitly from INSTALL_ALL.cmd. Downloads only official public assets."""
from pathlib import Path
import gc,hashlib,json,os,shutil,time,urllib.request,zipfile

ROOT=Path(__file__).resolve().parent
HEADERS={'User-Agent':'MangaTranslator-Installer/2.0','Accept-Encoding':'identity'}
REPO='tencent/Hy-MT2-7B-GGUF'
MODEL_NAME='HY-MT2-7B-Q8_0.gguf'
LLAMA_TAG='b10964'


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=90) as response:
        return json.load(response)


def sha256(path):
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def download(url,path,expected_size,expected_sha=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def valid(file):
        return file.exists() and file.stat().st_size==expected_size and (not expected_sha or sha256(file)==expected_sha)
    if valid(path):print(f'Already verified: {path.name}',flush=True);return
    partial=path.with_suffix(path.suffix+'.part')
    if partial.exists() and partial.stat().st_size>expected_size:partial.unlink()
    remaining=expected_size-(partial.stat().st_size if partial.exists() else 0)
    if shutil.disk_usage(path.parent).free<remaining+128*1024*1024:
        raise RuntimeError(f'Not enough disk space to download {path.name}.')
    for attempt in range(1,5):
        try:
            offset=partial.stat().st_size if partial.exists() else 0
            if offset<expected_size:
                headers=dict(HEADERS)
                if offset:headers['Range']=f'bytes={offset}-'
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as response:
                    if response.status==206:
                        if not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                            raise RuntimeError('The server returned an incorrect byte range.')
                    else:offset=0
                    last=0
                    with open(partial,'ab' if offset else 'wb') as stream:
                        while True:
                            block=response.read(4*1024*1024)
                            if not block:break
                            stream.write(block);offset+=len(block)
                            if time.monotonic()-last>2:
                                print(f'{path.name}: {offset/expected_size:.1%} ({offset/1e9:.2f}/{expected_size/1e9:.2f} GB)',flush=True);last=time.monotonic()
            if not valid(partial):
                if partial.stat().st_size>=expected_size:partial.unlink()
                raise RuntimeError('Download incomplete or SHA-256 verification failed.')
            partial.replace(path);print(f'Completed and verified: {path.name}',flush=True);return
        except (OSError,RuntimeError) as error:
            if attempt==4:raise
            print(f'Temporary failure: {error}. Retrying ({attempt}/4)...',flush=True);time.sleep(2*attempt)


def safe_extract(archive,directory):
    root=Path(directory).resolve();root.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            target=(root/info.filename).resolve()
            if not target.is_relative_to(root):raise RuntimeError('Invalid path in the local runtime package.')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as source,open(target,'wb') as dest:shutil.copyfileobj(source,dest)


def main():
    print('Downloading the official translation runtime for Windows x64 CPU...',flush=True)
    release=get_json(f'https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{LLAMA_TAG}')
    assets=[a for a in release['assets'] if 'win-cpu-x64' in a['name'].lower() and a['name'].endswith('.zip')]
    if len(assets)!=1:raise RuntimeError('CPU x64 package not found in the official release. No alternative package was selected.')
    asset=assets[0];archive=ROOT/'downloads'/asset['name']
    digest=asset.get('digest') or ''
    download(asset['browser_download_url'],archive,asset['size'],digest[7:] if digest.startswith('sha256:') else None)
    safe_extract(archive,ROOT/'runtime'/'llama')
    if not list((ROOT/'runtime'/'llama').rglob('llama-server.exe')):raise RuntimeError('The package does not contain llama-server.exe.')
    print('Retrieving verification data for the Hy-MT2-7B Q8 model...',flush=True)
    metadata=get_json(f'https://huggingface.co/api/models/{REPO}?blobs=true')
    info=next(x for x in metadata['siblings'] if x['rfilename']==MODEL_NAME)
    lfs=info.get('lfs',{});digest=lfs.get('sha256');size=lfs.get('size',info.get('size'))
    if not digest or not size:raise RuntimeError('Could not retrieve the official model size and SHA-256.')
    revision=metadata['sha']
    download(f'https://huggingface.co/{REPO}/resolve/{revision}/{MODEL_NAME}',ROOT/'models'/'hy-mt2'/MODEL_NAME,size,digest)
    (ROOT/'models'/'hy-mt2'/'source.json').write_text(json.dumps({'repo':REPO,'revision':revision,'file':MODEL_NAME,'sha256':digest,'llama_release':LLAMA_TAG},indent=2),encoding='utf-8')
    print('Downloading Japanese and Chinese OCR models...',flush=True)
    os.environ.setdefault('TORCH_HOME',str(ROOT/'models'/'torch'))
    import easyocr
    for language in ['ja','ch_sim','ch_tra']:
        reader=easyocr.Reader([language,'en'],gpu=False,verbose=False,
            model_storage_directory=str(ROOT/'models'/'ocr'),user_network_directory=str(ROOT/'models'/'ocr-user'))
        del reader;gc.collect();print(f'OCR {language}: ready.',flush=True)
    from lama_local import install
    install()
    print('Download complete. Testing an actual translation; this may take a while in a VM...',flush=True)
    from translator_hy import HyTranslator
    translator=HyTranslator()
    try:
        answer=translator.translate('博士，欢迎回来。','Chinês',glossary='博士 = Doctor')
        print('Translation test: '+answer,flush=True)
        (ROOT/'logs').mkdir(exist_ok=True)
        (ROOT/'logs'/'translation-test.txt').write_text(answer,encoding='utf-8')
    finally:translator.close()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('\nERROR: '+str(error),flush=True)
        raise SystemExit(1)
