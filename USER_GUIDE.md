# MangaTranslator

Local Windows manga editor: read Japanese or Chinese dialogue and translate it into English, with visual review before applying changes.

## Install

Download the full ZIP from [Releases](https://github.com/ImagoAlter123/MangaTranslator/releases/latest), extract it, run `INSTALL_ALL.cmd`, then launch `RUN.cmd`.

The interface and installer messages are in English. Scripts and supporting filenames are now in English. The installer downloads Python, dependencies, EasyOCR, Hy-MT2-7B Q8, llama.cpp and LaMa. These models are not included in the ZIP. Reserve at least 15 GB of disk space; 16 GB or more RAM is recommended for a virtual machine. CPU operation is supported and can be slow.

## Features

- PDF and multiple PNG/JPEG/WebP images, imported in numerical order.
- Automatic balloon suggestions and manual selections; independent erase and translation areas.
- Japanese/Chinese OCR, vertical reading order, and preprocessing for outlined text.
- Local English translation with a glossary and neighboring dialogue context.
- CC Wild Words Roman, manual font sizing, independent text and outline colors.
- Black text with white outline preset, page-wide approval and font size adjustments.
- Background editor with mask, color picker, texture copying, classical repair and local LaMa.
- Ctrl+Z, editable projects, PDF and PNG export.
- Project settings retain source language, glossary, vertical reading and column order.

## Workflow

Open pages, detect or select balloons, choose the source language and reading order, then read the source text. Review it before translating. Review the English, adjust the boxes and font, then apply approved translations and export. Batch translation and font controls apply to the current page.

Glossary example: `博士 = Doctor; 阿米娅 = Amiya`.

For text over art, clean the original lettering with the background tool. Mark letters and their outlines, including some clean surrounding background in the crop. Choose **Reconstruct with AI — LaMa (CPU)**, generate a preview, compare, and apply. Then use **Style: black text with white outline** on the translation. Outline thickness remains adjustable.

## Update

Close the app, replace the program files, and preserve `.venv`, `models`, `runtime` and your projects. Run `DOWNLOAD_LAMA.cmd` only if LaMa has not been installed. Existing downloaded models can be reused.

Older projects remain readable. Portuguese language names in saved settings are migrated automatically. Projects from versions that did not save the glossary cannot recover that missing information: enter it once and save again. Format 4 projects require a compatible recent application version.

## Limitations and components

OCR, translation, balloon detection and reconstructed artwork require review. Font sizes are manual. Projects with automatic sizes are converted to their current rendered size when opened. Text may extend beyond its selection box; this does not block PDF or PNG export.

PySide6, Pillow, OpenCV, pypdfium2, EasyOCR, Tencent Hy-MT2, llama.cpp and LaMa retain their own licenses. The LaMa TorchScript export is distributed by Sanster/IOPaint. Images are processed locally, not uploaded for inference.

The font and example project were supplied by the user for this private repository. Their inclusion does not grant public redistribution rights.

## Custom colors

Select a balloon and click **Text color** or **Outline color**. Choose a color or enter its hexadecimal code. New balloons use black text and a white outline color; use the outline thickness control to make the outline visible. The black/white style preset restores these colors. Colors are saved in format 4 projects. Older projects retain their previous outline appearance. The redundant page retranslation button has been removed; individual translation and page batch OCR/translation remain available.

## Default background and font controls

LaMa is now the first and default background treatment. The radius control applies only to reconstruction from nearby pixels. The automatic font size checkbox has been removed; use Size in pixels or the page-wide increase/decrease buttons. Existing automatic sizes are preserved visually when a project is opened, then become manual.

## Latest changes

Use RUN.cmd to launch, INSTALL_ALL.cmd for a new installation, and DOWNLOAD_LAMA.cmd to install only LaMa. The mask brush size is remembered across background dialogs and app restarts on this computer. Apply all translations is now above font sizing, with the black/white style preset immediately below it. Load font is below the individual Apply translation checkbox. Text overflow does not block export or shrink the text; pixels outside the page itself remain outside the exported image.


See BACKGROUND_GUIDE.md for background editing instructions.


## Export all pages as WebP ZIP

Click **Export all as WebP ZIP**, choose a ZIP filename and wait for completion. Every page is exported in project order as page-001.webp, page-002.webp, etc. Images use lossless WebP at the original page pixel dimensions, with applied translations and background edits. Unapplied translations remain unapplied. Oversized text does not block export. The archive is only replaced after every page has been exported successfully.
