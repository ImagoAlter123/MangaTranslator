# Background editor

Select Background — experimental and drag a rectangle around the original text, including some clean background. Mark the letters and their outlines with Mask brush. Use Mask eraser to correct the mask. Red pixels are the only pixels that will change. Brush diameter is saved on this computer, including when you cancel the dialog.

LaMa is the first and default treatment. Install it once with DOWNLOAD_LAMA.cmd if needed. Generate preview, compare the result, then Apply background. CPU processing can take minutes. LaMa can distort lines or tones, so review the result.

Other treatments:
- Reconstruct from nearby pixels: classical inpainting; radius applies only here.
- Fill with color: use Pick color on a clean background pixel.
- Copy nearby texture: select Texture source and click the top-left corner of a clean source area. It must fit in the crop and not overlap the mask.

Suggest mask uses pixel brightness, not text recognition. Check the artwork before applying. Expand mask by 1 pixel can help cover letter outlines. Ctrl+Z undoes mask edits. After applying, the main window Undo restores the previous background.

For the translation, enable Text over artwork or use Style: black text with white outline. Text and outline colors are independent. Font size is manual. Text may extend past the selection box without blocking export. LaMa does not translate text; OCR always reads the original page.
