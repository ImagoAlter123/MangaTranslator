$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$appRoot = $PSScriptRoot
Set-Location -LiteralPath $appRoot
$logDir = Join-Path $appRoot 'logs'
$downloadDir = Join-Path $appRoot 'downloads'
New-Item -ItemType Directory -Force -Path $logDir, $downloadDir | Out-Null
Start-Transcript -Path (Join-Path $logDir 'instalacao.txt') -Append | Out-Null
try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Requer Windows de 64 bits.' }
    Write-Host 'Manga Translator: instalacao local para Windows / maquina virtual.'
    Write-Host 'Modelo Hy-MT2-7B Q8: aproximadamente 8 GB de download.'
    Write-Host 'Reserve 15 GB de disco livre. Sugestao: 16 GB ou mais de RAM na VM.'
    Write-Host 'Sem GPU obrigatoria; a traducao pode ser lenta pelo processador.'
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
            Write-Host 'Baixando Python do site oficial...'
            Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer
            $signature = Get-AuthenticodeSignature -LiteralPath $installer
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'A assinatura do instalador Python nao foi validada. Nada foi executado.'
            }
            $pythonDir = Join-Path $appRoot 'runtime\python'
            New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
            $installerArgs = '/quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_pip=1 PrependPath=0 Shortcuts=0 TargetDir="' + $pythonDir + '"'
            $process = Start-Process -FilePath $installer -ArgumentList $installerArgs -WindowStyle Hidden -Wait -PassThru
            if ($process.ExitCode -notin 0,3010) { throw "Instalacao do Python falhou: $($process.ExitCode)" }
        }
    }
    $venvPython = Join-Path $appRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $basePython -m venv (Join-Path $appRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente Python.' }
    }
    & $venvPython (Join-Path $appRoot 'reparar_pip.py')
    if ($LASTEXITCODE -ne 0) { throw 'O pip esta ausente ou danificado e o reparo automatico falhou. Veja a mensagem acima.' }
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao atualizar pip.' }
    & $venvPython -m pip install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar o mecanismo de reconhecimento CPU.' }
    & $venvPython -m pip install -r (Join-Path $appRoot 'requirements-ai.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as bibliotecas.' }
    & $venvPython (Join-Path $appRoot 'baixar_modelos.py')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar ou validar os modelos. Execute novamente para retomar.' }
    Write-Host 'Tudo pronto. Use ABRIR.cmd. A fonte CC Wild Words Roman ja vem selecionada.'
} catch {
    Write-Host ('ERRO: ' + $_.Exception.Message) -ForegroundColor Red
    Stop-Transcript | Out-Null
    exit 1
}
Stop-Transcript | Out-Null
exit 0
