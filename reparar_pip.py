"""Repair pip inside the application's virtual environment, offline."""
import pathlib,subprocess,sys

def main():
    if sys.prefix==sys.base_prefix:
        print('Execute este reparador usando .venv\\Scripts\\python.exe. O Python global nao sera alterado.')
        return 1
    def works():
        return subprocess.run([sys.executable,'-m','pip','--version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if works():
        print('pip verificado.');return 0
    print('Reparando pip no ambiente do aplicativo, sem baixar modelos...',flush=True)
    subprocess.run([sys.executable,'-m','ensurepip','--upgrade'])
    if works():return 0
    # Incomplete pip installations may retain metadata that confuses ensurepip.
    try:
        import ensurepip
        wheels=sorted((pathlib.Path(ensurepip.__file__).parent/'_bundled').glob('pip-*.whl'))
        if not wheels:raise RuntimeError('Pacote local do pip ausente.')
        bootstrap='import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("pip",run_name="__main__")'
        subprocess.run([sys.executable,'-c',bootstrap,str(wheels[-1]),'install','--no-index','--force-reinstall',str(wheels[-1])])
    except (ImportError,OSError,RuntimeError) as error:
        print('Nao foi possivel reparar usando o Python instalado: '+str(error))
    if works():return 0
    print('Falha no reparo. Repare a instalacao do Python 3.12 incluindo pip e execute INSTALAR_TUDO.cmd novamente. Nenhum modelo ou projeto foi apagado.')
    return 1

if __name__=='__main__':sys.exit(main())
