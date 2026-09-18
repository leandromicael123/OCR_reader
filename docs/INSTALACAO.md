# Instalação e execução

## No computador Intel com 32 GB

Pré-requisitos: Windows x64, Python x64 3.11–3.13, Internet para dependências/pesos e espaço livre suficiente
para vários GB de caches. Não é necessária GPU NVIDIA nem uma conta num serviço OCR.

Na pasta OCR_reader:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install paddlepaddle==3.2.1 --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/
.\.venv\Scripts\python.exe -m pip install -e '.[ocr]'
.\.venv\Scripts\python.exe -c 'import paddle; paddle.utils.run_check()'
.\.venv\Scripts\python.exe run.py init
.\.venv\Scripts\python.exe run.py doctor
```

É equivalente a `scripts/install.ps1 -WithOCR`. Não instalar simultaneamente PaddlePaddle CPU e GPU.
As versões iniciais foram escolhidas a partir da documentação oficial. Ainda é necessário confirmar
que o resolvedor encontra todas as dependências Windows no computador de destino e executar a inferência.
Se ocorrer incompatibilidade de instalação, guardar o erro e ajustar a versão/runtime de forma explícita;
não substituir por uma chamada cloud ou apresentar sucesso sem OCR.

Depois de adicionar imagens:

```powershell
.\.venv\Scripts\python.exe run.py check
.\.venv\Scripts\python.exe run.py process --limit 1
```

O primeiro carregamento pode transferir modelos gratuitos e ser demorado. A imagem é processada na máquina.
O tempo final depende do CPU e da página; não há ainda medições neste projeto.

## No computador Qualcomm

Pode executar validação, consultar o projeto e desenvolver/testar o núcleo. O perfil de inferência atual
recusa este hardware para evitar tratar emulação x64 como suporte nativo validado.

```powershell
python run.py init
python run.py doctor
python run.py check
```

`doctor` devolve código **2** enquanto o ambiente não estiver preparado para OCR. Não instala nada.
Não transferir um ambiente `.venv` entre computadores; recriá-lo no destino.

## Códigos de saída

- `0`: comando/lote concluído sem pendências técnicas; resultados continuam por rever.
- `1`: ficheiros inválidos, indisponíveis ou trabalhos à espera de nova tentativa.
- `2`: hardware, dependências, configuração ou execução indisponível.
- `130`: interrupção pelo utilizador.

