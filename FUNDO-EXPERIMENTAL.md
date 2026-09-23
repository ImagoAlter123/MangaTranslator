# Fundo — experimental

Esta opção é independente da tradução. Funciona na CPU. A opção LaMa exige baixar um modelo adicional; os três tratamentos anteriores continuam funcionando sem ele. Você pode apenas limpar a página e exportar, sem escolher uma fonte.

## Atualizar sua instalação na VM

Feche o programa. Extraia o pacote e copie os arquivos da pasta `MangaTranslator` sobre os da instalação existente. Mantenha as pastas `.venv`, `models` e `runtime`, além dos seus projetos. Abra `ABRIR.cmd`. Para habilitar LaMa, execute BAIXAR_LAMA.cmd uma vez. Não é necessário baixar novamente os modelos de tradução ou OCR.

## Usar a ferramenta

1. Abra a página e clique em **Fundo — experimental**, na coluna esquerda.
2. Arraste um retângulo em volta do texto. Inclua um pouco de fundo limpo para a reconstrução; para copiar textura, inclua também a área que servirá de origem.
3. Na janela separada, pinte **somente as letras e seus contornos**. O vermelho mostra exatamente onde haverá alteração. Ajuste o tamanho do pincel e use a borracha para retirar partes da arte da máscara.
4. Opcionalmente, use **Sugerir máscara**: escolha pixels escuros ou claros e ajuste o limiar. Essa sugestão é baseada em contraste, não reconhece letras; ela pode marcar partes do desenho. Revise com a borracha antes de continuar. **Engrossar máscara** acrescenta um pixel ao redor para cobrir bordas das letras.
5. Escolha um tratamento:
   - **Reconstruir com IA — LaMa (CPU):** reconstrói a área marcada usando Big LaMa local. Inclua fundo limpo ao redor no recorte. Pode levar minutos na VM; aguarde a prévia. O raio não afeta LaMa. Recortes maiores que 1024 pixels são reduzidos internamente para limitar a memória. Os pixels fora da máscara permanecem intactos. A IA pode deformar linhas; compare antes de aplicar.
   - **Reconstruir pela vizinhança:** preenche as letras usando os pixels próximos. Ajuste o raio se necessário. Não é IA generativa e pode borrar linhas ou retículas.
   - **Preencher com cor:** selecione a ferramenta **Capturar cor** e clique em um ponto limpo do fundo. Depois gere a prévia. A cor inicial é branca.
   - **Copiar textura próxima:** selecione **Origem da textura** e clique no canto superior esquerdo de uma área limpa. Esse ponto corresponde ao canto superior esquerdo do conjunto de pixels marcados. A cópia não redimensiona a textura e altera somente os pixels da máscara. Se a origem ficar fora do recorte ou cruzar a máscara, escolha outra área. A cruz azul indica a origem.
6. Clique em **Gerar prévia**. Alterne **Ver resultado** para comparar com o recorte anterior e **Mostrar máscara** para revisar a área marcada.
7. Clique em **Aplicar fundo**. Cancelar não altera a página. Qualquer mudança na máscara ou no tratamento invalida a prévia, exigindo gerar outra antes de aplicar.

Ctrl + roda controla o zoom. Use as barras de rolagem para navegar pelo recorte e pelos controles em telas pequenas.

## Colocar a tradução sobre a arte

Depois de limpar, crie ou selecione uma região de texto na tela principal. Marque **Texto sobre arte (sem caixa branca)**. Escolha a tradução, ative a fonte automática e ajuste o **Contorno branco (px)** para facilitar a leitura. Marque **Aplicar tradução deste balão** depois de revisar. A opção sem caixa branca é independente da limpeza e também pode ser usada sem um reparo de fundo.

## Salvar e voltar atrás

- **Desfazer última alteração** também desfaz aplicações de fundo durante a sessão.
- **Restaurar fundo original** remove todos os reparos de fundo da página atual, sem apagar os textos de tradução. Essa ação também pode ser desfeita.
- O projeto `.manga` guarda a imagem original, os reparos aplicados e os controles de texto. O arquivo fonte do PDF/imagem não é alterado.
- A máscara de trabalho é temporária: depois de fechar a janela, o projeto preserva o resultado do reparo, não a máscara nem o histórico do pincel.
- Os projetos antigos continuam abrindo na versão nova. Projetos salvos com reparos de fundo exigem esta versão ou posterior.

## Limites e verificação

Rostos, contornos de personagens, perspectiva e retículas complexas podem precisar de retoque externo. Trabalhe em recortes pequenos e compare a prévia. Esta versão não usa um modelo generativo especializado em reconstrução.

Foram testados preenchimento por cor, reconstrução local, clonagem, preservação dos pixels fora da máscara, pincel/borracha, prévia, aplicar/cancelar, desfazer, exportação sem fonte quando não há tradução e salvamento/reabertura dos reparos. A interface também foi renderizada e inspecionada.

## Origem do modelo

LaMa: https://github.com/advimman/lama (Apache-2.0). Exportação TorchScript distribuída por Sanster/IOPaint: https://github.com/Sanster/models/releases/tag/add_big_lama . O instalador verifica o MD5 publicado pelo IOPaint e o SHA-256 quando fornecido pela API do GitHub. Nenhuma imagem é enviada à internet.
