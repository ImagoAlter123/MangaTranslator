# Manga Translator — Windows / máquina virtual

## Instalação automática na VM

1. Copie o ZIP para dentro da VM e **extraia todos os arquivos** em uma pasta local com permissão de gravação, por exemplo `Documentos\MangaTranslator`. Não execute dentro do ZIP.
2. Dê dois cliques em **INSTALAR_TUDO.cmd** e aguarde. Deixe a janela aberta.
3. Ao terminar, abra **ABRIR.cmd**.
4. A **CC Wild Words Roman** fornecida pelo usuário já vem selecionada como padrão. Você pode escolher outra fonte no editor.

O script instala Python 3.12 se necessário, cria um ambiente isolado, instala as bibliotecas, baixa o mecanismo CPU para Windows x64, o modelo **Hy-MT2-7B Q8** e os modelos de leitura de japonês e chinês. Ao final, executa uma tradução de teste e salva o resultado em `logs\teste-traducao.txt`.

O modelo de tradução tem aproximadamente **8 GB**. Reserve **15 GB de disco livre** para a instalação completa. Como orientação prática, aloque **16 GB ou mais de RAM** à VM; o consumo real depende das páginas abertas e do contexto. Não é necessária GPU. A tradução pelo processador pode demorar, especialmente com poucos núcleos disponíveis.

Se a conexão cair, execute **INSTALAR_TUDO.cmd** novamente. O download grande usa um arquivo parcial e tenta retomar. O modelo final é conferido por SHA-256 antes de ser usado. Bibliotecas já instaladas são reaproveitadas. O log da instalação fica em `logs\instalacao.txt`.

A assinatura digital do instalador Python é verificada antes da execução. Python, bibliotecas, modelos e mecanismo local são obtidos de seus canais oficiais. O script não altera o PATH global e não exige configurar uma chave de API.

## Fundo experimental

A ferramenta separada **Fundo — experimental** limpa texto sobre cor, textura ou desenho com máscara, prévia e desfazer. Os métodos clássicos não exigem modelo adicional; LaMa exige o download pelo instalador. Consulte **FUNDO-EXPERIMENTAL.md** para atualizar a VM e usar pincel, captura de cor, cópia de textura e reconstrução local.

## Correção da leitura vertical

A leitura vertical agora agrupa os traços separados de cada caractere antes de organizar as colunas. Selecione o idioma correto e a ordem das colunas (direita → esquerda ou esquerda → direita). Cada coluna reconhecida aparece em uma linha separada no campo Original. A pontuação ainda precisa de revisão.

Para corrigir um original já preenchido com erros, selecione a região e clique novamente em **Ler original com IA local**. Depois revise e clique em **Traduzir original para inglês**. Retraduzir a página não refaz os originais que já estão preenchidos. A correção foi testada na captura enviada, reconhecendo os caracteres das duas colunas sem os símbolos espúrios anteriores.

## Corações, reticências e fonte padrão

O OCR vertical agora verifica corações e reticências verticais no fim das colunas. As duas imagens enviadas foram testadas: o coração aparece como `♥` e os três pontos como `…`, em vez de dois-pontos. É uma detecção geométrica conservadora, não uma garantia para todos os símbolos ou estilos.

O tradutor recebe instruções explícitas para preservar os sinais e não inventar emoticons. Uma verificação posterior remove emoticons comuns não presentes no original e preserva corações/reticências no fim do texto. O teste dessa verificação foi local; não foi feita uma nova inferência real com Hy-MT2 nesta máquina. Em textos complexos, revise o resultado.

Para regiões já reconhecidas incorretamente, clique em **Ler original com IA local** novamente e depois em **Traduzir original para inglês**. Retraduzir sozinho reutiliza o original antigo.

A fonte padrão está em `fonts/CC Wild Words Roman.ttf`. Copie também a pasta `fonts` ao atualizar. O coração é desenhado como símbolo vetorial porque a fonte não inclui esse glifo.

## Travessão sem quadrado

Os sinais `—` e `–` agora são desenhados separadamente, pois faltam na CC Wild Words fornecida. O texto original da tradução permanece igual; a correção vale para a prévia, tamanho automático e exportação. Não é necessário refazer o OCR ou traduzir novamente: basta reabrir o projeto na versão atualizada.

## Leitura automática de texto com contorno branco

O botão **Ler original com IA local** agora compara a leitura normal com uma imagem temporária que isola letras escuras cercadas por branco. Isso ajuda a separar as colunas do desenho de fundo. O mesmo tratamento funciona na leitura em lote. Não é preciso limpar manualmente o fundo nem instalar outro modelo para essa tentativa.

A limpeza é apenas uma entrada temporária do OCR: não altera a página nem seus reparos de fundo. A escolha usa confiança do reconhecimento e quantidade de caracteres, não uma transcrição cadastrada. Leituras vazias, símbolos isolados indevidos ou confiança muito baixa geram um aviso e preservam o original anterior. Isso não significa que toda leitura aceita estará correta. Fontes estilizadas, outros tipos de contorno e fundos complexos ainda podem produzir erros.

A imagem enviada com texto contornado foi testada em sua resolução original e ampliada em 2x e 3x, reconhecendo as duas colunas e as reticências. Os exemplos anteriores de balões, coração e reticências também foram verificados. Esses testes não são uma garantia para todas as páginas.

Para uma região já preenchida incorretamente, clique novamente em **Ler original com IA local**. Só retraduzir continua reutilizando o original anterior. Use **Chinês**, **Texto original vertical** e colunas **direita → esquerda** para o exemplo enviado.

## O que mudou

- **Novo tradutor:** Hy-MT2-7B Q8 substitui o OPUS-MT. O aplicativo usa falas vizinhas já reconhecidas como contexto e oferece um glossário opcional para nomes e tratamentos. Não volta silenciosamente ao tradutor antigo caso falte o novo modelo.
- **Fonte automática de verdade:** aumenta ou diminui a fonte até o maior tamanho que cabe na área verde, com margem. O valor antigo, como 30 px, deixou de ser um teto. As quebras buscam linhas equilibradas sem partir palavras; quebras manuais são mantidas.
- **Controle manual:** desmarque “Fonte automática: preencher a área” para escolher um tamanho fixo. Com o modo automático ligado, o campo mostra o tamanho calculado.
- **Retradução:** para substituir traduções antigas, use “Retraduzir toda a página com Hy-MT2”. O texto original revisado é reaproveitado; as novas traduções ficam desmarcadas para revisão. É possível desfazer.

## Abrir várias imagens

Clique em **Abrir PDF / várias imagens**. Na janela de seleção, use **Ctrl+A** para selecionar todas as imagens da pasta, ou Ctrl/Shift para escolher um conjunto. As imagens WebP, PNG ou JPG entram como páginas de um único projeto, em ordem numérica dos nomes (1, 2, 3… 10… 30). A resolução original é preservada. O seletor de páginas permite navegar e **Exportar PDF** reúne todas elas. Abrir arquivos substitui o projeto atual após o aviso de alterações não salvas; não adiciona ao projeto existente. A tradução em lote continua atuando na página atual.

## Fluxo de uso

1. Abra um PDF ou uma imagem e selecione a página.
2. Use **Sugerir balões desta página**, ou escolha **Criar balão manual** e arraste sobre o texto.
3. Selecione um balão na lista. Ajuste separadamente **Área apagada** (azul) e **Área da tradução** (verde). Para reposicionar ou redimensionar, escolha o modo e desenhe o novo retângulo. A fonte automática utiliza a área verde; não altera a área apagada.
4. Selecione japonês ou chinês. Ative a opção vertical para colunas lidas de cima para baixo e da direita para a esquerda.
5. Use **Ler original com IA local**, corrija eventuais erros e traduza. A ação em lote reconhece todos os originais antes de traduzir, para fornecer contexto. O botão normal de lote preserva traduções já preenchidas.
6. Opcionalmente, escreva equivalências no glossário, por exemplo `博士 = Doctor`, quando isso corresponder ao personagem. O glossário vale para a sessão atual e não é salvo no projeto.
7. A CC Wild Words Roman incluída é a fonte padrão. Você ainda pode escolher outra fonte. Limpar/exportar apenas o fundo não exige fonte.
8. Confira a tradução e a fonte. Marque **Aplicar tradução deste balão** para efetuar a substituição. Textos vazios não apagam o original. Ajuste áreas estreitas se palavras longas limitarem o tamanho da fonte.
9. Exporte o PDF completo ou a página atual em PNG. Salve um projeto `.manga` para retomar depois; o projeto contém as páginas originais e as edições, mas referencia o arquivo da fonte por caminho.

Ctrl + roda controla o zoom. As barras de rolagem navegam pela página. O painel direito também pode rolar em telas menores. “Mostrar página original” permite comparar. “Desfazer” restaura edições dos balões, inclusive a retradução em lote.

## Escopo e limites

- O aplicativo trabalha nos balões de fala. A detecção procura áreas brancas fechadas e arredondadas; caixas de narração retangulares e fundos desenhados ficam fora da detecção pretendida. Ainda pode haver sugestões incorretas ou balões perdidos.
- O modo normal usa cobertura branca. A opção **Fundo — experimental** oferece limpeza por máscara, cor, clonagem e reconstrução pela vizinhança. Áreas complexas ainda podem exigir retoque externo.
- O OCR vertical é experimental. Um original reconhecido incorretamente prejudica qualquer tradutor; revise o campo original.
- O modelo recebe texto e contexto, mas não vê a imagem. Traduções precisam de revisão, especialmente para ambiguidades, nomes e estilo de personagem.
- O modo chinês do OCR é simplificado. Não há um modo dedicado a chinês tradicional.
- PDFs são renderizados a 144 dpi. A exportação gera páginas rasterizadas, sem preservar texto vetorial ou camadas. Capítulos grandes consomem mais memória; processe em partes se necessário.
- O mecanismo de tradução abre somente um endereço local `127.0.0.1`, com chave temporária, e é encerrado ao fechar o editor. Nenhuma página ou fala é enviada a um serviço externo de tradução.
- Ainda é um aplicativo Python iniciado por atalho, sem instalador `.exe` único.

## Verificações desta atualização

Foram testados localmente: crescimento automático da fonte, tamanho manual, limites da área, avisos de excesso, edição independente, desfazer, salvamento, detecção dos dois balões do PDF de referência, estrutura do contexto de tradução, tratamento de modelo ausente e de respostas truncadas. A retomada do download, sua verificação e a proteção de caminhos do ZIP foram testadas com respostas simuladas. A sintaxe do script PowerShell foi validada.

**O download completo e a execução real do Hy-MT2 não foram testados nesta máquina**, pois o acesso à rede para instalação não foi concedido. O instalador executa esse teste real na VM ao terminar. Não se trata de uma comparação de qualidade já realizada. Nesta atualização, a CC Wild Words enviada foi incluída e a composição foi testada com essa fonte. Como ela não possui o glifo de coração, o editor desenha ♥/♡ separadamente, com tamanho e posição integrados ao texto.

O projeto `Exemplo-para-revisar.manga` contém traduções da versão antiga. Para comparar o novo modelo, escolha chinês e use o botão de retraduzir a página.

## Fontes e componentes

- Hy-MT2-7B e instruções de tradução/contexto: https://huggingface.co/tencent/Hy-MT2-7B
- Pesos oficiais Q8: https://huggingface.co/tencent/Hy-MT2-7B-GGUF
- Mecanismo CPU: https://github.com/ggml-org/llama.cpp/releases/tag/b10964
- OCR: https://github.com/JaidedAI/EasyOCR
- Python Windows: https://www.python.org/downloads/release/python-31210/

As dependências e os modelos mantêm suas próprias licenças. O arquivo de fonte incluído foi fornecido pelo usuário para este aplicativo.


NOVO: LaMa para reconstruir fundos com IA local na CPU.
Ao atualizar, execute BAIXAR_LAMA.cmd uma vez e depois ABRIR.cmd.
No editor de fundo, escolha Reconstruir com IA — LaMa (CPU).
O modelo (aproximadamente 205 MB) não está incluído no ZIP. Consulte FUNDO-EXPERIMENTAL.md.


COR E REVISÃO EM LOTE
- Cor da fonte deste balão: Preto ou Branco. O contorno usa a cor oposta.
- Para texto branco sobre o desenho, marque Texto sobre arte (sem caixa branca).
- Aplicar todos os textos desta página: aplica as traduções preenchidas; ignora campos vazios. Não executa nova tradução.
- Diminuir/Aumentar 2 px: ajusta todos os balões da página a partir do tamanho atual e desliga o ajuste automático deles.
- As operações em lote afetam somente a página atual e podem ser desfeitas. O aviso de texto que não cabe continua ativo.
- A cor fica salva no projeto. Projetos antigos usam preto por padrão.


## Estilo preto com contorno branco

Selecione um balão e clique em **Estilo: preto com contorno branco**. O botão escolhe preto, retira a caixa branca e define um contorno branco proporcional ao tamanho atual da fonte. Ajuste **Contorno contrastante (px)** de 0 a 32 para mudar a espessura. Marque **Aplicar tradução deste balão** para exibir. Ctrl+Z desfaz o estilo. O estilo não remove as letras originais: use a ferramenta de fundo antes, quando necessário.


## Idioma e glossário salvos no projeto

O projeto agora guarda idioma original, glossário, leitura vertical e ordem das colunas. Alterar essas opções marca o projeto como não salvo. Projetos antigos continuam abrindo, mas não contêm esses dados: selecione o idioma e preencha o glossário novamente, depois salve com esta versão. Projetos novos usam formato 3 e devem ser abertos nesta versão ou em versões posteriores.
