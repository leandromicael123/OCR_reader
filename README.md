# OCR_reader

Protótipo local para experimentar transcrição de notas manuscritas, sem APIs pagas.
O primeiro alvo é o **computador Intel com 32 GB de RAM**, usando CPU e uma imagem de cada vez.

## Estado desta versão

Implementado: validação JPG/PNG, espera por estabilidade, snapshot dos originais, orientação EXIF, SHA-256,
estado SQLite fora da pasta sincronizada, adaptador PaddleOCR-VL, JSON/Markdown, recortes por bloco,
pré-visualização HTML offline, índice ParaRever e novas tentativas explícitas.

O adaptador usa a API documentada PaddleOCR-VL v1.6. **A inferência real ainda precisa de ser validada no
computador Intel e com imagens reais.** O ambiente de desenvolvimento atual é Qualcomm/ARM com Python
x64 emulado; o programa deteta esse caso e não tenta carregar o motor nativo.

Os testes usam respostas sintéticas declaradas para verificar o fluxo. Não são um benchmark OCR nem
demonstram qualidade em manuscrito. Não existe fallback que apresente texto simulado como reconhecimento.

## Pastas

```text
OCR_reader/
├── Entrada/                Imagens JPG/JPEG/PNG; nunca movidas ou apagadas nesta fase
├── Resultado/              Um diretório independente por execução
├── ParaRever/              index.html com ligações para os resultados
├── Processados/            Reservada para uma futura etapa de aprovação/arquivo
├── Erros/                  Diagnóstico das imagens/trabalhos que falharam
├── logs/                   Eventos operacionais, sem conteúdo da transcrição
├── config/                 Configuração do protótipo
├── docs/                   Arquitetura, decisões e plano de validação
├── scripts/                Instalação e execução em PowerShell
├── src/ocr_reader/
│   ├── ingestion/          Descoberta e captura estável
│   ├── recognition/        Adaptador PaddleOCR-VL local
│   ├── processing/        Estrutura de blocos e recortes de evidência
│   ├── exporters/          Markdown, JSON, HTML e manifesto de integridade
│   └── storage/            SQLite, lock e eventos
└── tests/                  Testes de integridade, falhas, exportação e deduplicação
```

## Primeiro ensaio no computador Intel

1. Copiar a pasta `OCR_reader` para o computador Intel. Não copiar `.venv`, caches ou ficheiros de runtime.
2. Instalar Python **x64 3.11–3.13** (3.12 é a versão usada no desenvolvimento).
3. Abrir PowerShell dentro de `OCR_reader` e executar:

```powershell
.\scripts\install.ps1 -WithOCR
```

Se a política PowerShell bloquear scripts, usar os comandos manuais de [instalação](docs/INSTALACAO.md),
sem necessidade de alterar permanentemente a política do computador.

4. Colocar 5–10 imagens representativas em `Entrada`.
5. Diagnosticar e validar as imagens:

```powershell
.\.venv\Scripts\python.exe run.py doctor
.\.venv\Scripts\python.exe run.py check
```

6. Processar primeiro **uma** imagem; depois um lote:

```powershell
.\.venv\Scripts\python.exe run.py process --limit 1
.\.venv\Scripts\python.exe run.py process --limit 5
```

7. Abrir `ParaRever/index.html`. O original aparece ao lado dos blocos reconhecidos e respetivos recortes.
As fórmulas são apresentadas em **LaTeX literal** nesta versão; ainda não existe renderização matemática.

O primeiro reconhecimento poderá descarregar pesos e demorar mais. Há consumo de Internet para instalação
e download, espaço em disco e energia; não há cobrança por página ou chave API. O programa usa inferência local,
sem endpoint remoto de OCR. Depois de obter todos os pesos, validar um ensaio com rede desligada antes de
assumir operação offline num ambiente específico. As caches do fornecedor ficam normalmente no perfil do utilizador.

## Resultados

```text
Resultado/<hash-curto>-<id-execucao>/
├── original.jpg             Bytes originais (ou original.png/.jpeg)
├── normalized.png           Orientação EXIF aplicada; imagem usada no OCR
├── backend/paddle-result.json
├── transcricao.json         Blocos, coordenadas, LaTeX, evidência e avisos
├── transcricao.md
├── preview.html
├── assets/                  Recortes de todos os blocos com região válida
└── manifest.json            Identidade e hashes de todos os artefactos
```

As coordenadas pertencem a `normalized.png`. A transcrição é sempre **por rever**. Não se corrige nem executa código.
O modelo pode falhar em matemática, indentação, margens e leitura integral. O JSON conserva o texto recebido;
a exportação acrescenta apenas estrutura e avisos. Diagramas são preservados por recortes quando localizados.

O HTML escapa o texto do motor, não carrega scripts externos e não executa HTML/código reconhecido. O Markdown
e o JSON conservam o conteúdo literal; abrir Markdown externo com execução de HTML/scripts desativada.

## Duplicados, erros e novas tentativas

Conteúdo igual e mesmo motor/configuração reutilizam o resultado, mesmo com outro nome. Conteúdo alterado
sob o mesmo nome cria uma execução nova. Nesta fase, deduplicação é por conteúdo: associar a mesma imagem
a várias aulas intencionalmente ficará para o modelo de sessões futuro.

```powershell
.\.venv\Scripts\python.exe run.py status
.\.venv\Scripts\python.exe run.py process --retry-failed
.\.venv\Scripts\python.exe run.py process --force --limit 1
```

`--force` cria novos resultados sem substituir os anteriores. `--retry-failed` inclui trabalhos interrompidos
e artefactos alterados/ausentes. Ficheiros ainda em sincronização voltam a ser tentados na execução seguinte.
Uma imagem corrompida permanece em Entrada com relatório em Erros; não é apagada ou movida automaticamente.

A base fica em `%LOCALAPPDATA%/OCR_reader/<id-do-projeto>/state.sqlite`. `doctor` mostra o caminho exato.
Não sincronizar a base em uso pelo OneDrive. É possível indicar `--state-dir` **antes** do subcomando para testes.
Se mover a pasta para outra localização/máquina, a identidade de instalação muda; migrar estado cuidadosamente
ou assumir que as imagens poderão voltar a ser processadas. Ainda não há publicações remotas para duplicar.

## Desenvolvimento

```powershell
.\scripts\install.ps1 -Dev
.\.venv\Scripts\python.exe -m pytest
```

Também se pode executar `python run.py init`, `doctor` e `check` com Python e Pillow já instalados.
Os testes não descarregam modelos nem enviam imagens. O adaptador é testado com objetos que imitam o contrato
oficial; o teste de integração real é um passo separado no Intel.

## Próximos incrementos

1. Medir qualidade, memória e latência no Intel com 5–10 páginas.
2. Acrescentar revisão/aprovação, renderização matemática e regras de ordem por sessão.
3. Automatizar polling e tratar fecho explícito de lotes.
4. Integrar OneNote com autenticação delegada e outbox/reconciliação.

OneNote, polling contínuo, aprovação e transferência para Processados **não estão implementados** nesta versão.
Ver [arquitetura](docs/ARQUITETURA.md), [instalação](docs/INSTALACAO.md) e [validação](docs/VALIDACAO.md).

