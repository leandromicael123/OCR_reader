# Arquitetura inicial

```text
Entrada → captura estável → snapshot + SHA-256 → verificação SQLite
                                                 ↓
                               PaddleOCR-VL local, CPU, sequencial
                                                 ↓
                                  JSON de blocos + recortes
                                                 ↓
                                 Markdown + HTML de revisão
                                                 ↓
                          manifesto íntegro → Resultado/ + ParaRever/
```

## Decisões

- Um processo e um worker. Sem broker, servidor web, Docker obrigatório ou APIs pagas.
- Execução manual por lote. Nomes são ordenados naturalmente (`2` antes de `10`), mas **não existe ainda
  uma barreira de sequência**: uma página ausente não bloqueia a seguinte. Não confundir ordem de nomes
  com o futuro contrato de sessões/manifestos.
- `Settings` é carregado de `config/settings.toml`. Diretórios operacionais ficam no projeto;
  SQLite fica no perfil local do utilizador.
- Snapshot byte a byte e SHA-256 antes de inferência. Tamanho/data estáveis são heurística, não protocolo
  infalível de conclusão de upload. O comando `check` permite detetar entradas problemáticas antes do ensaio.
- Orientação EXIF aplicada numa cópia PNG; sem redução arbitrária de resolução ou binarização.
- Adaptador apenas para inferência CPU local PaddleOCR-VL v1.6; não há fallback cloud.
- O motor devolve a ordem de leitura. Blocos desconhecidos são conservados e assinalados.
- Não se inventam níveis de confiança. Equações não são simplificadas; código não é corrigido.
- `original.*`, JSON bruto e recortes permitem comparar o resultado com a evidência.
- Publicação local por rename do diretório de staging **no mesmo filesystem**; manifesto é gravado por último.
- Lock do sistema operativo impede duas execuções concorrentes no mesmo projeto, mesmo com overrides de SQLite.
- Estado `running → needs_review` ou `failed`. Reinício recupera bundles já publicados ou marca `interrupted`.
- Trabalho falhado/interrompido exige `--retry-failed`. Conteúdo já concluído só é reutilizado se os artefactos
  continuam íntegros. Se os resultados forem editados externamente, são preservados e assinalados para nova tentativa.
- A primeira etapa conserva todos os originais em Entrada; não os move para Processados.

## Contrato normalizado

`transcricao.json` contém `schema_version`, `job_id`, `source`, `recognition`, `blocks`, `warnings` e `review`.
Cada bloco guarda `id`, `order`, `type`, `source_label`, `text`, `bbox`, `confidence=null` e `review_status`.
Equações acrescentam `latex`; blocos com coordenadas válidas acrescentam `source_crop`.

Não se afirma que toda a folha foi reconhecida apenas porque o JSON é válido. Uma lista vazia é exportada
como resultado por rever com aviso explícito. Setas, sublinhados, diagramas e código dependem do reconhecimento
do motor; o protótipo preserva a evidência e não os reconstrói de forma garantida.

## Compatibilidade e fontes

Consultadas em 18/09/2026:

- [PaddleOCR-VL: API Python, resultados e CPU x64](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html)
- [Modelo PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)
- [PaddleOCR: repositório oficial](https://github.com/PaddlePaddle/PaddleOCR)
- [Intel Arc: apenas B60 Pro validada no guia](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL-Intel-Arc-GPU.html)

O computador desta sessão é Qualcomm/ARM, apesar de `platform.machine()` apresentar AMD64 devido ao Python
emulado. A deteção considera também o processador e as variáveis do ambiente. A Arc 140V não é usada nesta fase.

