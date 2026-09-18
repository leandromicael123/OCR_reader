param(
    [switch]$WithOCR,
    [switch]$Dev
)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectPath '.venv\Scripts\python.exe'

# Verificar a arquitetura física, incluindo Python AMD64 emulado em Qualcomm.
$hostInfo = & python -c "import os,platform,sys,json; print(json.dumps({'arm':any(x in (' '.join([platform.machine(),platform.processor(),os.environ.get('PROCESSOR_IDENTIFIER','')])).lower() for x in ['arm','qualcomm','aarch64']),'supported':(3,11)<=sys.version_info[:2]<(3,14)}))"
if ($LASTEXITCODE -ne 0) { throw 'Python não encontrado. Instale Python 3.11, 3.12 ou 3.13.' }
$hostData = $hostInfo | ConvertFrom-Json
if (-not $hostData.supported) { throw 'Utilize Python 3.11, 3.12 ou 3.13.' }
if ($WithOCR -and $hostData.arm) {
    throw 'O perfil OCR inicial requer Intel/AMD x64. Execute este instalador no computador Intel com 32 GB. O núcleo pode ser instalado aqui sem -WithOCR.'
}

Push-Location $projectPath
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & python -m venv (Join-Path $projectPath '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente virtual.' }
    }
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar pip. Confirme acesso à Internet.' }
    & $venvPython -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar o núcleo.' }
    if ($WithOCR) {
        & $venvPython -m pip install 'paddlepaddle==3.2.1' --index-url 'https://www.paddlepaddle.org.cn/packages/stable/cpu/'
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar PaddlePaddle CPU.' }
        & $venvPython -m pip install -e '.[ocr]'
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar PaddleOCR. Consulte a documentação de compatibilidade.' }
        & $venvPython -c 'import paddle; paddle.utils.run_check()'
        if ($LASTEXITCODE -ne 0) { throw 'O teste nativo PaddlePaddle falhou. Não executar OCR neste ambiente.' }
    }
    if ($Dev) {
        & $venvPython -m pip install -e '.[dev]'
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências de testes.' }
    }
    & $venvPython run.py init
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar pastas.' }
    Write-Output 'Instalação concluída. O primeiro OCR poderá descarregar pesos gratuitos; as imagens são processadas localmente.'
    Write-Output 'Comando: .\.venv\Scripts\python.exe run.py process --limit 5'
} finally {
    Pop-Location
}

