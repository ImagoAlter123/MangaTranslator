"""Repair pip inside the application's virtual environment, offline."""
import pathlib,subprocess,sys

def main():
    if sys.prefix==sys.base_prefix:
        print('Run this repair tool using .venv\\Scripts\\python.exe. The global Python installation will not be changed.')
        return 1
    def works():
        return subprocess.run([sys.executable,'-m','pip','--version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if works():
        print('pip verified.');return 0
    print('Repairing pip in the app environment, without downloading models...',flush=True)
    subprocess.run([sys.executable,'-m','ensurepip','--upgrade'])
    if works():return 0
    # Incomplete pip installations may retain metadata that confuses ensurepip.
    try:
        import ensurepip
        wheels=sorted((pathlib.Path(ensurepip.__file__).parent/'_bundled').glob('pip-*.whl'))
        if not wheels:raise RuntimeError('Local pip package is missing.')
        bootstrap='import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("pip",run_name="__main__")'
        subprocess.run([sys.executable,'-c',bootstrap,str(wheels[-1]),'install','--no-index','--force-reinstall',str(wheels[-1])])
    except (ImportError,OSError,RuntimeError) as error:
        print('Could not repair using the installed Python: '+str(error))
    if works():return 0
    print('Repair failed. Repair Python 3.12 including pip and run INSTALL_ALL.cmd again. No models or projects were deleted.')
    return 1

if __name__=='__main__':sys.exit(main())
