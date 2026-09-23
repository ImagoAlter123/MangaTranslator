# MangaTranslator

Local Windows manga editor: read Japanese or Chinese dialogue and translate it into English, with visual review before applying changes.

## Install

Download the full ZIP from [Releases](https://github.com/ImagoAlter123/MangaTranslator/releases/latest), extract it, run `INSTALAR_TUDO.cmd`, then launch `ABRIR.cmd`.

The interface and installer messages are in English. Existing script filenames are kept for compatibility. The installer downloads Python, dependencies, EasyOCR, Hy-MT2-7B Q8, llama.cpp and LaMa. These models are not included in the ZIP. Reserve at least 15 GB of disk space; 16 GB or more RAM is recommended for a virtual machine. CPU operation is supported and can be slow.

## Features

- PDF and multiple PNG/JPEG/WebP images, imported in numerical order.
- Automatic balloon suggestions and manual selections; independent erase and translation areas.
- Japanese/Chinese OCR, vertical reading order, and preprocessing for outlined text.
- Local English translation with a glossary and neighboring dialogue context.
- CC Wild Words Roman, automatic font sizing, black/white text and contrasting outlines.
- Black text with white outline preset, page-wide approval and font size adjustments.
- Background editor with mask, color picker, texture copying, classical repair and local LaMa.
- Ctrl+Z, editable projects, PDF and PNG export.
- Project settings retain source language, glossary, vertical reading and column order.

## Workflow

Open pages, detect or select balloons, choose the source language and reading order, then read the source text. Review it before translating. Review the English, adjust the boxes and font, then apply approved translations and export. Batch translation and font controls apply to the current page.

Glossary example: `博士 = Doctor; 阿米娅 = Amiya`.

For text over art, clean the original lettering with the background tool. Mark letters and their outlines, including some clean surrounding background in the crop. Choose **Reconstruct with AI — LaMa (CPU)**, generate a preview, compare, and apply. Then use **Style: black text with white outline** on the translation. Outline thickness remains adjustable.

## Update

Close the app, replace the program files, and preserve `.venv`, `models`, `runtime` and your projects. Run `BAIXAR_LAMA.cmd` only if LaMa has not been installed. Existing downloaded models can be reused.

Older projects remain readable. Portuguese language names in saved settings are migrated automatically. Projects from versions that did not save the glossary cannot recover that missing information: enter it once and save again. Format 3 projects require a compatible recent application version.

## Limitations and components

OCR, translation, balloon detection and reconstructed artwork require review. Collective font adjustments switch the page to manual font sizes. Export warns about text that does not fit.

PySide6, Pillow, OpenCV, pypdfium2, EasyOCR, Tencent Hy-MT2, llama.cpp and LaMa retain their own licenses. The LaMa TorchScript export is distributed by Sanster/IOPaint. Images are processed locally, not uploaded for inference.

The font and example project were supplied by the user for this private repository. Their inclusion does not grant public redistribution rights.
