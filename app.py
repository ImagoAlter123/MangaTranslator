import sys, copy
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, Signal, QThread
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QFontDatabase, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QPushButton,QLabel,QComboBox,QTextEdit,QSpinBox,QCheckBox,QListWidget,QFileDialog,
    QMessageBox,QGraphicsView,QGraphicsScene,QSplitter,QGroupBox,QLineEdit,QScrollArea)
from core import Page, Region, BackgroundPatch, DEFAULT_FONT, background_image, region_layout, load_pages,load_multiple,detect_bubbles,render_page,save_project,load_project,layout
from ai_local import LocalAI
from languages import language_code


class Worker(QThread):
    done=Signal(object); failed=Signal(str)
    def __init__(self,fn): super().__init__(); self.fn=fn
    def run(self):
        try: self.done.emit(self.fn())
        except Exception as e: self.failed.emit(str(e))


class Canvas(QGraphicsView):
    box=Signal(list)
    def __init__(self):
        super().__init__(); self.setScene(QGraphicsScene(self)); self.start=None
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor('#222733')); self.setMinimumSize(400,400)
        self.setDragMode(QGraphicsView.NoDrag)
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:
            self.start=self.mapToScene(e.position().toPoint()); self.rubber=None
        else: super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self.start is not None:
            if self.rubber: self.scene().removeItem(self.rubber)
            self.rubber=self.scene().addRect(QRectF(self.start,self.mapToScene(e.position().toPoint())).normalized(),QPen(QColor('#38d9a9'),2))
        else: super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if self.start is not None:
            rect=QRectF(self.start,self.mapToScene(e.position().toPoint())).normalized().intersected(self.sceneRect())
            self.start=None
            if self.rubber: self.scene().removeItem(self.rubber); self.rubber=None
            if rect.width()>5 and rect.height()>5:
                self.box.emit([round(rect.left()),round(rect.top()),round(rect.right()),round(rect.bottom())])
    def wheelEvent(self,e):
        if e.modifiers() & Qt.ControlModifier:
            self.scale(1.15 if e.angleDelta().y()>0 else 1/1.15,1.15 if e.angleDelta().y()>0 else 1/1.15)
        else: super().wheelEvent(e)


class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Manga Translator • local editor'); self.resize(1320,900)
        self.pages=[]; self.index=0; self.font=str(DEFAULT_FONT) if DEFAULT_FONT.exists() else ''; self.dirty=False; self.loading=False; self.worker=None; self.ai=LocalAI(); self.history=[]
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root)
        title=QLabel('MANGA TRANSLATOR'); title.setStyleSheet('font-size:24px;font-weight:700;color:#66e0be;padding:6px'); main.addWidget(title)
        tools=QHBoxLayout(); main.addLayout(tools)
        self.button(tools,'Open PDF / multiple images',self.open)
        self.button(tools,'Open project',self.open_saved)
        self.button(tools,'Save project',self.save)
        self.button(tools,'Export PDF',self.export_pdf)
        self.button(tools,'Export page as PNG',self.export_png)
        split=QSplitter(); main.addWidget(split,1)
        left=QWidget(); left.setMaximumWidth(255); ll=QVBoxLayout(left); split.addWidget(left)
        self.page_combo=QComboBox(); self.page_combo.currentIndexChanged.connect(self.change_page); ll.addWidget(self.page_combo)
        self.button(ll,'Detect balloons on this page',self.detect)
        self.button(ll,'Background — experimental',self.start_background)
        self.button(ll,'Restore original background',self.reset_background)
        self.list=QListWidget(); self.list.currentRowChanged.connect(self.select); ll.addWidget(self.list)
        self.button(ll,'Delete selection',self.remove)
        self.button(ll,'Undo last change (Ctrl+Z)',self.undo)
        self.undo_shortcut=QShortcut(QKeySequence('Ctrl+Z'),self)
        self.undo_shortcut.setContext(Qt.WindowShortcut)
        self.undo_shortcut.activated.connect(self.undo)
        info=QLabel('Suggestions do not erase the page.\nReview and check “Apply translation”.\n\nBlue: erase area\nGreen: translation area\n\nCtrl + wheel: zoom\nScrollbars: pan'); info.setWordWrap(True); ll.addWidget(info)
        self.canvas=Canvas(); self.canvas.box.connect(self.set_box); split.addWidget(self.canvas)
        right=QWidget(); rr=QVBoxLayout(right)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(right);scroll.setMaximumWidth(385);split.addWidget(scroll)
        rr.addWidget(QLabel('When dragging on the page:'))
        self.mode=QComboBox(); self.mode.addItems(['Create balloon manually','Adjust erase area','Adjust translation area','Select background area']); rr.addWidget(self.mode)
        self.original_view=QCheckBox('Show original page'); self.original_view.toggled.connect(self.draw); rr.addWidget(self.original_view)
        self.button(rr,'Fit page to window',self.fit)
        rr.addWidget(QLabel('Source language → English'))
        self.language=QComboBox(); self.language.addItem('Japanese','ja'); self.language.addItem('Chinese','ch_sim'); rr.addWidget(self.language)
        from translator_hy import MODEL
        model_label=QLabel('Translator: Hy-MT2-7B Q8 • local\n'+('Model downloaded' if MODEL.exists() else 'Run INSTALAR_TUDO.cmd to download'))
        model_label.setWordWrap(True);rr.addWidget(model_label)
        rr.addWidget(QLabel('Optional glossary (names / titles)'))
        self.glossary=QLineEdit();self.glossary.setPlaceholderText('Example: 博士 = Doctor; 阿米娅 = Amiya');rr.addWidget(self.glossary)
        self.vertical=QCheckBox('Vertical source text'); self.vertical.setChecked(True); rr.addWidget(self.vertical)
        self.column_order=QComboBox();self.column_order.addItems(['Columns: right → left','Columns: left → right']);rr.addWidget(self.column_order)
        self.vertical.toggled.connect(self.column_order.setEnabled)
        rr.addWidget(QLabel('Source text • editable'))
        self.source=QTextEdit(); self.source.setMaximumHeight(90); self.source.textChanged.connect(self.edit); rr.addWidget(self.source)
        self.button(rr,'Read source text with local AI',self.ocr)
        rr.addWidget(QLabel('English translation • editable'))
        self.target=QTextEdit(); self.target.setMaximumHeight(90); self.target.textChanged.connect(self.edit); rr.addWidget(self.target)
        self.button(rr,'Translate source text to English',self.translate)
        self.button(rr,'Read and translate all balloons',self.batch)
        self.button(rr,'Retranslate this page with Hy-MT2',lambda:self.batch(True))
        self.font_label=QLabel('Font: CC Wild Words Roman (default)' if self.font else 'Fallback font: Arial'); self.font_label.setWordWrap(True); rr.addWidget(self.font_label)
        self.button(rr,'Load font (.ttf / .otf)',self.choose_font)
        fontrow=QHBoxLayout(); rr.addLayout(fontrow); fontrow.addWidget(QLabel('Size in pixels:'))
        self.size=QSpinBox(); self.size.setRange(6,2048); self.size.setValue(30); self.size.valueChanged.connect(self.edit); fontrow.addWidget(self.size)
        self.auto=QCheckBox('Auto font size: fit to area'); self.auto.setChecked(True); self.auto.toggled.connect(self.edit); rr.addWidget(self.auto)
        rr.addWidget(QLabel('Text color for this balloon:'))
        self.text_color=QComboBox();self.text_color.addItems(['Black','White']);self.text_color.currentIndexChanged.connect(self.edit);rr.addWidget(self.text_color)
        self.transparent=QCheckBox('Text over artwork (no white box)');self.transparent.toggled.connect(self.edit);rr.addWidget(self.transparent)
        outline_row=QHBoxLayout();rr.addLayout(outline_row);outline_row.addWidget(QLabel('Contrasting outline (px):'))
        self.outline=QSpinBox();self.outline.setRange(0,32);self.outline.valueChanged.connect(self.edit);outline_row.addWidget(self.outline)
        self.button(rr,'Style: black text with white outline',self.outlined_style)
        self.enabled=QCheckBox('Apply translation to this balloon'); self.enabled.toggled.connect(self.edit); rr.addWidget(self.enabled)
        self.button(rr,'Apply all translations on this page',self.apply_all)
        rr.addWidget(QLabel('All fonts on this page (manual sizes):'))
        sizes=QHBoxLayout();rr.addLayout(sizes)
        self.button(sizes,'Decrease by 2 px',lambda:self.resize_all(-2))
        self.button(sizes,'Increase by 2 px',lambda:self.resize_all(2))
        self.hint=QLabel('Open a file to get started.'); self.hint.setWordWrap(True); rr.addWidget(self.hint); rr.addStretch()
        split.setSizes([205,740,335]); self.statusBar().showMessage('Local • no page uploads • English output')
        self.setStyleSheet('QWidget{background:#171c26;color:#e5e9f0;font-size:13px} QPushButton{background:#303a4e;border:1px solid #44516b;border-radius:5px;padding:8px} QPushButton:hover{background:#43516b} QTextEdit,QListWidget,QComboBox,QSpinBox{background:#222b3a;border:1px solid #44516b;padding:4px} QCheckBox{padding:3px} QSplitter::handle{background:#303a4e}')

        self.language.currentIndexChanged.connect(self.settings_changed)
        self.glossary.textChanged.connect(self.settings_changed)
        self.vertical.toggled.connect(self.settings_changed)
        self.column_order.currentIndexChanged.connect(self.settings_changed)

    def settings_changed(self,*_):
        if self.pages and not self.loading:self.dirty=True
    def project_settings(self):
        return {'language':self.language.currentData(),'glossary':self.glossary.text(),
                'vertical':self.vertical.isChecked(),'rtl':self.column_order.currentIndex()==0}
    def button(self,layout,label,fn):
        b=QPushButton(label); b.clicked.connect(fn); layout.addWidget(b); return b
    def page(self): return self.pages[self.index] if self.pages else None
    def region(self):
        p=self.page(); idx=self.list.currentRow()
        return p.regions[idx] if p and 0<=idx<len(p.regions) else None
    def checkpoint(self):
        self.history.append((self.index,self.list.currentRow(),copy.deepcopy(self.page().regions),list(self.page().patches))); self.history=self.history[-30:]; self.dirty=True
    def undo(self):
        if self.history:
            i,selected,regions,patches=self.history.pop(); self.pages[i].regions=regions;self.pages[i].patches=patches; self.page_combo.setCurrentIndex(i); self.refresh(selected); self.dirty=True
    def discard(self):
        return not self.dirty or QMessageBox.question(self,'Unsaved changes','Discard unsaved changes?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes
    def install_pages(self,pages,font='',settings=None):
        self.pages=pages; self.font=font if font and Path(font).exists() else (str(DEFAULT_FONT) if DEFAULT_FONT.exists() else ''); self.history=[]; self.dirty=False
        if settings is not None:
            self.loading=True
            language=language_code(settings.get('language','ja'))
            self.language.setCurrentIndex(self.language.findData(language))
            self.glossary.setText(settings.get('glossary',''))
            self.vertical.setChecked(settings.get('vertical',True))
            self.column_order.setCurrentIndex(0 if settings.get('rtl',True) else 1)
            self.loading=False
        self.font_label.setText(Path(self.font).name if self.font else 'Fallback font: Arial')
        self.page_combo.blockSignals(True); self.page_combo.clear(); self.page_combo.addItems([f'Page {i+1} of {len(pages)}' for i in range(len(pages))]); self.page_combo.blockSignals(False)
        self.index=0; self.refresh(); self.fit()
    def open(self):
        if not self.discard(): return
        paths,_=QFileDialog.getOpenFileNames(self,'Select a PDF or multiple images — use Ctrl+A, Ctrl or Shift','','PDF and images (*.pdf *.png *.jpg *.jpeg *.webp)')
        if paths: self.run(lambda:load_multiple(paths),self.install_pages,f'Opening {len(paths)} file(s) in numerical order…')
    def open_saved(self):
        if not self.discard(): return
        path,_=QFileDialog.getOpenFileName(self,'Open project','','Project (*.manga)')
        if path: self.run(lambda:load_project(path,with_settings=True),lambda x:self.install_pages(*x),'Opening project…')
    def save(self):
        if not self.pages: return
        path,_=QFileDialog.getSaveFileName(self,'Save project','','Project (*.manga)')
        if path:
            try: save_project(path,self.pages,self.font,self.project_settings()); self.dirty=False; self.statusBar().showMessage('Project saved, including language, glossary and reading settings.')
            except Exception as e: self.error(str(e))
    def change_page(self,index):
        if index>=0 and self.pages: self.index=index; self.refresh(); self.fit()
    def refresh(self,selected=0):
        self.list.blockSignals(True); self.list.clear()
        if self.page(): self.list.addItems([f'Balloon {i+1}'+(' • applied' if r.enabled else ' • review') for i,r in enumerate(self.page().regions)])
        self.list.blockSignals(False); self.list.setCurrentRow(selected); self.select(); self.draw()
    def select(self,*_):
        r=self.region(); self.loading=True
        self.source.setPlainText(r.original if r else ''); self.target.setPlainText(r.translation if r else '')
        self.size.setValue(r.size if r else 30); self.auto.setChecked(r.auto_fit if r else True); self.enabled.setChecked(r.enabled if r else False)
        self.text_color.setCurrentIndex(1 if r and r.text_color=="white" else 0)
        self.transparent.setChecked(r.transparent if r else False);self.outline.setValue(r.outline if r else 0)
        self.loading=False; self.draw()
    def edit(self,*_):
        if self.loading or not self.region(): return
        self.checkpoint(); r=self.region(); r.original=self.source.toPlainText(); r.translation=self.target.toPlainText(); r.size=self.size.value(); r.auto_fit=self.auto.isChecked(); r.enabled=self.enabled.isChecked()
        r.text_color="white" if self.text_color.currentIndex()==1 else "black"
        r.transparent=self.transparent.isChecked();r.outline=self.outline.value()
        item=self.list.currentItem()
        if item: item.setText(f'Balloon {self.list.currentRow()+1}'+(' • applied' if r.enabled else ' • review'))
        self.draw()
    def outlined_style(self):
        r=self.region()
        if r is None:return
        actual=region_layout(r,self.font)[1].size if r.translation.strip() else r.size
        self.checkpoint()
        r.text_color='black';r.transparent=True
        r.outline=max(2,min(32,round(actual*.10)))
        self.select()
        self.statusBar().showMessage('Style set for this balloon. Adjust Contrasting outline for thickness and check Apply translation to display it.')
    def apply_all(self):
        p=self.page()
        if not p:return
        regions=[r for r in p.regions if r.translation.strip() and not r.enabled]
        if not regions:return
        self.checkpoint()
        for r in regions:r.enabled=True
        self.refresh(self.list.currentRow())
        self.statusBar().showMessage(f'Applied {len(regions)} translation(s) on this page. Empty texts were skipped. Use Undo to revert.')
    def resize_all(self,delta):
        p=self.page()
        if not p or not p.regions:return
        sizes=[max(6,min(2048,(region_layout(r,self.font)[1].size if r.translation.strip() else r.size)+delta)) for r in p.regions]
        self.checkpoint()
        for r,size in zip(p.regions,sizes):r.size=size;r.auto_fit=False
        self.refresh(self.list.currentRow())
        self.statusBar().showMessage('Fonts adjusted on this page; sizes are now manual. Use Undo to revert.')
    def draw(self,*_):
        p=self.page()
        if not p: return
        selected=self.region()
        self.size.setEnabled(bool(selected) and not selected.auto_fit)
        if selected and selected.auto_fit and selected.translation.strip():
            actual=region_layout(selected,self.font)[1].size
            self.size.blockSignals(True);self.size.setMaximum(2048);self.size.setValue(actual);self.size.blockSignals(False)
        try: im,warnings=render_page(p,self.font) if not self.original_view.isChecked() else (p.image,[])
        except Exception as e: self.error(str(e)); return
        self.hint.setText('\n'.join(warnings) if warnings else 'Drag to define the selected area. Review the text before applying.')
        data=im.tobytes('raw','RGB'); q=QImage(data,im.width,im.height,im.width*3,QImage.Format_RGB888).copy()
        self.canvas.scene().clear(); self.canvas.scene().addPixmap(QPixmap.fromImage(q)); self.canvas.setSceneRect(0,0,im.width,im.height)
        for i,r in enumerate(p.regions):
            for box,color in [(r.erase,'#49aaff'),(r.text_box,'#32d9a4')]:
                pen=QPen(QColor(color),3 if i==self.list.currentRow() else 1); pen.setCosmetic(True)
                self.canvas.scene().addRect(QRectF(box[0],box[1],box[2]-box[0],box[3]-box[1]),pen)
    def fit(self):
        if self.page(): self.canvas.fitInView(self.canvas.sceneRect(),Qt.KeepAspectRatio)
    def set_box(self,box):
        if not self.page(): return
        mode=self.mode.currentIndex()
        if mode==3:self.edit_background(box);return
        if mode and not self.region(): return
        self.checkpoint()
        if mode==0:
            self.page().regions.append(Region(box.copy(),box.copy())); self.refresh(len(self.page().regions)-1)
        else:
            if mode==1: self.region().erase=box
            else: self.region().text_box=box
            self.draw()
    def start_background(self):
        if not self.page():self.error('Open a page before using the background tool.');return
        self.mode.setCurrentIndex(3)
        self.statusBar().showMessage('Experimental background: drag a rectangle around the text, including some clean background.')
    def edit_background(self,box):
        from background_editor import BackgroundEditor
        dialog=BackgroundEditor(background_image(self.page()).crop(box),self)
        if dialog.exec()==BackgroundEditor.DialogCode.Accepted:
            self.checkpoint();self.page().patches.append(BackgroundPatch(box.copy(),dialog.result.copy()));self.draw()
            self.statusBar().showMessage('Background applied. Use Undo to revert; check “Text over artwork” to place the translation on the art.')
    def reset_background(self):
        if self.page() and self.page().patches:
            self.checkpoint();self.page().patches=[];self.draw()
            self.statusBar().showMessage('Background repairs removed from this page. You can undo this action.')
    def remove(self):
        if self.region(): self.checkpoint(); del self.page().regions[self.list.currentRow()]; self.refresh()
    def detect(self):
        if not self.page(): return
        image=self.page().image.copy()
        def done(regions):
            self.checkpoint(); existing=self.page().regions
            for r in regions:
                if not any(abs(r.erase[0]-e.erase[0])+abs(r.erase[1]-e.erase[1])<25 for e in existing): existing.append(r)
            self.refresh(); self.statusBar().showMessage(f'{len(regions)} suggestion(s). Review them: white artwork may be mistaken for balloons.')
        self.run(lambda:detect_bubbles(image),done,'Detecting white balloons…')
    def choose_font(self):
        path,_=QFileDialog.getOpenFileName(self,'Select a font','','Fonts (*.ttf *.otf)')
        if path:
            try:
                from core import font_at
                font_at(path,30); self.font=path; self.font_label.setText(Path(path).name); self.dirty=True; self.draw()
            except Exception as e: self.error(str(e))
    def ocr(self):
        r=self.region()
        if not r:return
        image=self.page().image.crop(r.erase); language=self.language.currentData(); vertical=self.vertical.isChecked();rtl=self.column_order.currentIndex()==0
        self.run(lambda:self.ai.read(image,language,vertical,rtl),lambda text:self.source.setPlainText(text),'Reading text and comparing background preprocessing. First use may download OCR models…')
    def translate(self):
        if not self.region(): return
        source=self.source.toPlainText(); language=self.language.currentData();glossary=self.glossary.text()
        context=self.neighbor_context(self.page().regions,self.list.currentRow())
        self.run(lambda:self.ai.translate(source,language,context,glossary),lambda text:self.target.setPlainText(text),'Translating with Hy-MT2-7B on CPU. This may take a while in a VM…')
    @staticmethod
    def neighbor_context(regions,index):
        return '\n'.join(f'Other dialogue {i+1}: {regions[i].original}' for i in range(max(0,index-2),min(len(regions),index+3)) if i!=index and regions[i].original.strip())[:5000]
    def batch(self,replace=False):
        if not self.page() or not self.page().regions:return
        p=self.page(); language=self.language.currentData(); vertical=self.vertical.isChecked();glossary=self.glossary.text();rtl=self.column_order.currentIndex()==0
        todo=copy.deepcopy(p.regions)
        def job():
            for r in todo:
                if not r.original.strip():r.original=self.ai.read(p.image.crop(r.erase),language,vertical,rtl)
            for i,r in enumerate(todo):
                if replace or not r.translation.strip():
                    r.translation=self.ai.translate(r.original,language,self.neighbor_context(todo,i),glossary)
                    r.enabled=False
            return todo
        def done(regions): self.checkpoint(); p.regions=regions; self.refresh(); self.statusBar().showMessage('Translations are ready for review. Apply approved balloons individually or use Apply all translations on this page.')
        self.run(job,done,'Reading and translating balloons on this page…')
    def run(self,fn,done,message):
        if self.worker: return
        self.busy_message=message; self.centralWidget().setEnabled(False); self.statusBar().showMessage(message)
        self.worker=Worker(fn)
        self.worker.done.connect(done); self.worker.failed.connect(self.error); self.worker.finished.connect(self.finished); self.worker.start()
    def finished(self):
        self.centralWidget().setEnabled(True); self.worker.deleteLater(); self.worker=None
        if self.statusBar().currentMessage()==self.busy_message:self.statusBar().showMessage('Operation finished. Review the result before applying.')
    def error(self,message): QMessageBox.warning(self,'Unable to complete operation',message)
    def export_images(self,indices=None):
        if not self.pages:return None
        selected_pages=list(range(len(self.pages)) if indices is None else indices)
        if not self.font and any(r.enabled and r.translation.strip() for i in selected_pages for r in self.pages[i].regions):
            self.error('Load the CC Wild Words font before exporting. The preview currently uses Arial.');return None
        images=[]
        for i in selected_pages:
            p=self.pages[i]
            im,warnings=render_page(p,self.font,strict=True)
            if warnings:self.error(f'Page {i+1}:\n'+'\n'.join(warnings));return None
            images.append(im)
        return images
    def export_pdf(self):
        try:
            images=self.export_images()
            if not images:return
            path,_=QFileDialog.getSaveFileName(self,'Export PDF','','PDF (*.pdf)')
            if not path:return
            # Per-page DPI preserves physical page dimensions, even for mixed inputs.
            import io
            with __import__('pypdfium2').PdfDocument.new() as out:
                for im,p in zip(images,self.pages):
                    buf=io.BytesIO(); im.save(buf,format='PDF',resolution=p.dpi)
                    with __import__('pypdfium2').PdfDocument(buf.getvalue()) as part:out.import_pages(part)
                out.save(path)
            self.statusBar().showMessage('PDF exported: '+path)
        except Exception as e:self.error(str(e))
    def export_png(self):
        try:
            images=self.export_images([self.index])
            if images:
                path,_=QFileDialog.getSaveFileName(self,'Export page','','PNG (*.png)')
                if path:images[0].save(path,dpi=(self.page().dpi,self.page().dpi))
        except Exception as e:self.error(str(e))
    def closeEvent(self,event):
        if self.worker:
            self.error('Wait for the current operation to finish before closing.');event.ignore()
        elif self.discard():self.ai.close();event.accept()
        else:event.ignore()


if __name__=='__main__':
    app=QApplication(sys.argv)
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    app.setFont(QFont('Segoe UI',10))
    window=Window();window.show();sys.exit(app.exec())
