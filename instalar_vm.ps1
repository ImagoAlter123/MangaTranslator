$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$appRoot = $PSScriptRoot
Set-Location -LiteralPath $appRoot
$logDir = Join-Path $appRoot 'logs'
$downloadDir = Join-Path $appRoot 'downloads'
New-Item -ItemType Directory -Force -Path $logDir, $downloadDir | Out-Null
Start-Transcript -Path (Join-Path $logDir 'instalacao.txt') -Append | Out-Null
try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Requires 64-bit Windows.' }
    Write-Host 'Manga Translator: local installation for Windows / virtual machines.'
    Write-Host 'Hy-MT2-7B Q8 model: approximately 8 GB download.'
    Write-Host 'Reserve 15 GB of free disk space. Recommended: 16 GB or more RAM in the VM.'
    Write-Host 'No GPU required; CPU translation may be slow.'
    $basePython = Join-Path $appRoot 'runtime\python\python.exe'
    if (-not (Test-Path -LiteralPath $basePython)) {
        $existingPython = $null
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $found = & py -3.12 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $found) { $existingPython = $found.Trim() }
        }
        if ($existingPython -and (Test-Path -LiteralPath $existingPython)) {
            $basePython = $existingPython
        } else {
            $installer = Join-Path $downloadDir 'python-3.12.10-amd64.exe'
            Write-Host 'Downloading Python from the official website...'
            Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer
            $signature = Get-AuthenticodeSignature -LiteralPath $installer
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'The Python installer signature could not be verified. Nothing was executed.'
            }
            $pythonDir = Join-Path $appRoot 'runtime\python'
            New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
            $installerArgs = '/quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_pip=1 PrependPath=0 Shortcuts=0 TargetDir="' + $pythonDir + '"'
            $process = Start-Process -FilePath $installer -ArgumentList $installerArgs -WindowStyle Hidden -Wait -PassThru
            if ($process.ExitCode -notin 0,3010) { throw "Python installation failed: $($process.ExitCode)" }
        }
    }
    $venvPython = Join-Path $appRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $basePython -m venv (Join-Path $appRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    }
    & $venvPython (Join-Path $appRoot 'reparar_pip.py')
    if ($LASTEXITCODE -ne 0) { throw 'pip is missing or damaged and automatic repair failed. Check the message above.' }
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Failed to update pip.' }
    & $venvPython -m pip install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'Failed to download the CPU recognition runtime.' }
    & $venvPython -m pip install -r (Join-Path $appRoot 'requirements-ai.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install libraries.' }
    & $venvPython (Join-Path $appRoot 'baixar_modelos.py')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to download or verify models. Run again to resume.' }
    Write-Host 'Ready. Use ABRIR.cmd. CC Wild Words Roman is already selected.'
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    Stop-Transcript | Out-Null
    exit 1
}
Stop-Transcript | Out-Null
exit 0
