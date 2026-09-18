# Experiência com uma página manuscrita sobre CTE

Data: 2026-09-18.

## Entrada

- Ficheiro: `Entrada/cte_001.jpg`, cópia da imagem fornecida pelo utilizador.
- Dimensões validadas: 1208 × 1693 píxeis.
- Prefixo SHA-256 apresentado pelo validador: `07cd1a3ff146`.
- Original conservado sem alterações.

## Teste real do programa

A partir da pasta que contém `OCR_reader`:

```powershell
python -X utf8 OCR_reader/run.py check
```

Resultado:

```text
OK: cte_001.jpg | 1208x1693 | SHA256 07cd1a3ff146
1 imagem(ns); 0 por verificar. Não foi executado OCR.
```

Tentativa de reconhecimento:

```powershell
python -X utf8 OCR_reader/run.py process --limit 1
```

Resultado:

```text
OCR indisponível: Este computador é ARM/Qualcomm (mesmo com Python x64 emulado). O perfil inicial é Intel/AMD x64 CPU. Execute o OCR no computador Intel com 32 GB.
```

O processo terminou antes da inferência. Não foi gerada uma transcrição automática. Este resultado indica uma limitação do perfil implementado; não prova que seja impossível executar qualquer motor OCR em ARM. Não foi feita uma chamada a uma API paga nem descarregado um modelo neste teste.

## Referência de leitura

`transcricao-visual.md` contém uma leitura feita pelo assistente nesta conversa, com incertezas explícitas. Não foi colocada em `Resultado`, para que não seja confundida com uma saída do programa. Requer revisão humana antes de servir como referência para medir a precisão.

## Repetir no computador Intel

Copiar a pasta `OCR_reader`, incluindo esta imagem, para o computador Intel. Num terminal PowerShell dentro dessa pasta:

```powershell
.\scripts\install.ps1 -WithOCR
.\scripts\process.ps1 -Limit 1
```

A instalação e a primeira inferência requerem acesso à Internet para obter dependências e modelos gratuitos. Comparar a saída gerada em `Resultado` com a imagem e com a referência revista. Registar tempo de execução, consumo de memória e erros de transcrição. Esses valores e a qualidade do modelo nesta imagem ainda não foram medidos.
