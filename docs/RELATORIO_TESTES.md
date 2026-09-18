# Relatório de desenvolvimento — 18/09/2026

## Verificado nesta sessão

| Verificação | Resultado |
|---|---|
| `python -m pytest -q` | **31 testes passaram**, em 3,31 s na última execução |
| Construção de pacote wheel, sem rede/dependências | `ocr_reader-0.1.0-py3-none-any.whl` construído com sucesso |
| Parser PowerShell de `scripts/install.ps1` | 0 erros de sintaxe |
| Parser PowerShell de `scripts/process.ps1` | 0 erros de sintaxe |
| `run.py init` | Pastas operacionais criadas |
| `run.py check` | Executado; Entrada vazia, 0 imagens, nenhum OCR |
| `run.py status` | Sem trabalhos reais registados |
| `run.py doctor` | Identificou Qualcomm/ARM com Python AMD64 emulado e motor ausente |

Ambiente: Python 3.12.8 x64 emulado num processador Qualcomm ARM; Pillow 11.2.1; pytest 8.3.5.

Os testes validam o fluxo com imagens geradas e respostas sintéticas declaradas, incluindo preservação
do original, deduplicação, novas revisões, código com erro intencional, equações, recuperação após interrupção,
proteção contra HTML executável e exclusão de instâncias simultâneas. Não efetuam downloads nem chamadas OCR externas.

## Ainda não verificado

- Instalação completa das dependências PaddleOCR/PaddlePaddle no computador Intel.
- Carregamento dos pesos e reconhecimento real de imagens.
- Precisão de manuscrito, matemática e código do utilizador.
- Tempo por página, utilização máxima de RAM e funcionamento offline depois dos downloads.
- Aceleração na GPU Intel Arc 140V (fora do perfil inicial CPU).

Não foram instalados os motores pesados nem descarregados pesos no Qualcomm. A ausência de inferência real
está explicitamente sinalizada no README e no comando de diagnóstico. OneNote e polling contínuo ainda
pertencem à fase seguinte, conforme a arquitetura experimental acordada.

