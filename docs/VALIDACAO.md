# Plano de validação

## Automatizada, sem OCR real

Os testes cobrem snapshot, EXIF, rejeição de imagens inválidas, estabilidade, deduplicação,
alterações sob o mesmo nome, repetição explícita, recuperação entre rename e commit, integridade dos
artefactos, preservação de espaços/código/LaTeX, conteúdo desconhecido, escape HTML e contrato do adaptador.
O backend de testes devolve blocos sintéticos; nenhum resultado de teste deve ser interpretado como OCR medido.

Executar `python -m pytest` na pasta OCR_reader. Resultados da execução deste desenvolvimento ficam em
`docs/RELATORIO_TESTES.md`.

## Obrigatória no Intel com imagens reais

1. Executar `doctor` e `paddle.utils.run_check()`.
2. Usar uma imagem pequena, legível, com texto conhecido; confirmar que há saída real do motor.
3. Ensaiar 5–10 páginas, incluindo PT/EN, código, integral, matriz, fração, nota marginal e diagrama.
4. Registar RAM máxima no Gestor de Tarefas e tempo por imagem (`recognition.duration_seconds` inclui
   carregamento do modelo na primeira imagem).
5. Comparar texto, omissões, símbolos, espaços e ordem. Contabilizar minutos de correção.
6. Voltar a executar o mesmo lote: não deve voltar a chamar o motor para bundles íntegros.
7. Testar interrupção e `--retry-failed`, sem alterar originais.
8. Depois dos downloads, testar sem Internet e confirmar que todas as caches necessárias estão disponíveis.

Só depois decidir se a qualidade justifica automatizar polling e acrescentar OneNote. Não há promessa
de tempo por página nem de aceleração pela Arc 140V nesta fase.

