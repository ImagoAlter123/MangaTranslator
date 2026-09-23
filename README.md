# MangaTranslator

Aplicativo local para Windows que traduz diálogos de mangás do japonês ou chinês para inglês, com revisão visual antes da aplicação.

## Instalar e abrir

1. Baixe o ZIP completo e extraia a pasta MangaTranslator.
2. Execute `INSTALAR_TUDO.cmd` com conexão à internet.
3. Abra `ABRIR.cmd` após a instalação.

O instalador prepara Python, bibliotecas, OCR, Hy-MT2-7B Q8 e LaMa. Os modelos não estão incluídos no repositório nem no ZIP. Reserve pelo menos 15 GB de disco; recomenda-se 16 GB de RAM na máquina virtual. Funciona na CPU, mas o processamento pode demorar.

## Recursos

- PDF e importação de várias imagens PNG, JPEG e WebP em ordem numérica.
- Sugestão de balões e seleção manual; áreas de apagamento e tradução independentes.
- OCR vertical japonês/chinês, escolha da ordem das colunas e tratamento de texto com contorno.
- Tradução local para inglês, glossário e contexto de diálogos próximos.
- Fonte CC Wild Words Roman fornecida pelo usuário; tamanho automático ou manual.
- Texto preto ou branco, contorno contrastante e texto sobre arte sem caixa branca.
- Aplicação de todos os textos revisados da página; ajuste das fontes da página em passos de 2 pixels.
- Ferramenta de fundo com máscara, captura de cor, cópia de textura, reconstrução clássica e LaMa.
- Ctrl+Z na página e na máscara; nos campos de texto, desfaz a digitação.
- Projetos editáveis, exportação de PDF e PNG.

## Atualizar

Feche o aplicativo e substitua os arquivos, preservando `.venv`, `models`, `runtime` e seus projetos. Para adicionar apenas LaMa a uma instalação existente, execute `BAIXAR_LAMA.cmd`.

## Fluxo de uso

Abra as páginas, selecione ou detecte os balões, escolha o idioma e a ordem de leitura, leia e revise o original, traduza e revise o inglês. Ajuste as áreas e a aparência; aplique os textos aprovados e exporte. A leitura/tradução em lote e os ajustes de fonte se referem à página atual.

Exemplo de glossário: `博士 = Doctor; 阿米娅 = Amiya`.

Para texto sobre desenho, consulte [o guia de fundo](FUNDO-EXPERIMENTAL.md). Marque letras e contorno, incluindo fundo limpo ao redor no recorte. LaMa funciona localmente e altera somente os pixels marcados; pode deformar linhas e exige revisão.

## Limitações

OCR, detecção de balões e tradução podem errar. Revisar é parte do fluxo. O ajuste coletivo de fontes desliga o tamanho automático dos balões da página. A exportação alerta sobre textos que não cabem. O exemplo incluído é material de revisão e não representa a qualidade atual do modelo.

## Componentes e materiais

Interface: PySide6; imagens: Pillow/OpenCV; PDF: pypdfium2; OCR: EasyOCR; tradução: Tencent Hy-MT2 com llama.cpp; reconstrução: LaMa, com exportação TorchScript de Sanster/IOPaint. Cada componente mantém sua própria licença.

A fonte e as páginas do projeto de exemplo são materiais fornecidos pelo usuário; sua inclusão neste repositório privado não concede autorização para redistribuição pública. Não há uma licença geral concedendo direitos sobre esses materiais.

Consulte também [LEIA-ME.md](LEIA-ME.md) e [COMECE-AQUI.txt](COMECE-AQUI.txt).
