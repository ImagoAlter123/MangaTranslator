import sys, copy
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, Signal, QThread, QSize
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QPainterPath, QTransform, QFontDatabase, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QToolBar,QPushButton,QLabel,QComboBox,QTextEdit,QSpinBox,QCheckBox,QListWidget,QFileDialog,
    QMessageBox,QGraphicsView,QGraphicsScene,QSplitter,QGroupBox,QLineEdit,QScrollArea,QColorDialog)
from core import Page, Region, BackgroundPatch, DEFAULT_FONT, background_image, region_layout, load_pages,load_multiple,detect_bubbles,render_page,save_project,load_project,layout
from ai_local import LocalAI
from languages import language_code
from text_cleanup import normalize_translation
from core import export_webp_zip
from click_controls import QComboBox, QSpinBox


class Worker(QThread):
    done=Signal(object); failed=Signal(str)
    def __init__(self,fn): super().__init__(); self.fn=fn
    def run(self):
        try: self.done.emit(self.fn())
        except Exception as e: self.failed.emit(str(e))


class Canvas(QGraphicsView):
    box=Signal(list)
    transformed=Signal(list)
    clicked=Signal(object)
    def __init__(self):
        super().__init__(); self.setScene(QGraphicsScene(self)); self.start=None
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor('#222733')); self.setMinimumSize(400,400)
        self.setDragMode(QGraphicsView.NoDrag)
        self.drag_shapes=lambda:[('rectangle','#38d9a9')]
        self.rubber=[]
        self.rounding=lambda:50
        self.transform_selection=lambda:None
        self.transforming=None
        self.click_origin=None
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:
            self.click_origin=e.position().toPoint()
            self.start=self.mapToScene(e.position().toPoint()); self.rubber=[]
            self.active_shapes=self.drag_shapes()
            self.transforming=self.transform_selection()
            if self.transforming:
                action,bounds=self.transforming
                rect=QRectF(bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1])
                tolerance=10/max(.01,self.transform().m11()) if action=='Resize' else 0
                self.resize_edges=self.pick_resize_edges(self.start,bounds)
                if not rect.adjusted(-tolerance,-tolerance,tolerance,tolerance).contains(self.start):
                    self.start=None;self.transforming=None
        else: super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self.start is not None:
            for item in self.rubber:self.scene().removeItem(item)
            self.rubber=[]
            point=self.mapToScene(e.position().toPoint())
            rect=self.transform_rect(point) if self.transforming else QRectF(self.start,point).normalized()
            for shape,color in self.active_shapes:
                pen=QPen(QColor(color),2);pen.setCosmetic(True)
                self.rubber.append(self.add_shape(rect,pen,shape,self.rounding()))
        else: super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if e.button()!=Qt.LeftButton:return super().mouseReleaseEvent(e)
        if self.click_origin is not None and (e.position().toPoint()-self.click_origin).manhattanLength()<=5:
            point=self.mapToScene(e.position().toPoint())
            self.start=None;self.transforming=None;self.click_origin=None
            for item in self.rubber:self.scene().removeItem(item)
            self.rubber=[]
            self.clicked.emit(point)
            return
        self.click_origin=None
        if self.start is not None:
            point=self.mapToScene(e.position().toPoint())
            rect=self.transform_rect(point) if self.transforming else QRectF(self.start,point).normalized().intersected(self.sceneRect())
            changed=self.transforming is not None
            self.start=None
            for item in self.rubber:self.scene().removeItem(item)
            self.rubber=[]
            if rect.width()>5 and rect.height()>5:
                (self.transformed if changed else self.box).emit([round(rect.left()),round(rect.top()),round(rect.right()),round(rect.bottom())])
            self.transforming=None
    def add_shape(self,rect,pen,shape,rounding):
        if shape=='rounded':
            path=QPainterPath();radius=min(rect.width(),rect.height())*rounding/200
            path.addRoundedRect(rect,radius,radius);return self.scene().addPath(path,pen)
        return (self.scene().addEllipse if shape=='oval' else self.scene().addRect)(rect,pen)

    def transform_rect(self,point):
        action,b=self.transforming;dx=point.x()-self.start.x();dy=point.y()-self.start.y();page=self.sceneRect()
        if action=='Move':
            dx=max(-b[0],min(dx,page.right()-b[2]));dy=max(-b[1],min(dy,page.bottom()-b[3]))
            return QRectF(b[0]+dx,b[1]+dy,b[2]-b[0],b[3]-b[1])
        left,top,right,bottom=b
        horizontal,vertical=self.resize_edges
        if horizontal=='left':left=max(page.left(),min(right-6,left+dx))
        elif horizontal=='right':right=min(page.right(),max(left+6,right+dx))
        if vertical=='top':top=max(page.top(),min(bottom-6,top+dy))
        elif vertical=='bottom':bottom=min(page.bottom(),max(top+6,bottom+dy))
        return QRectF(left,top,right-left,bottom-top)

    @staticmethod
    def pick_resize_edges(point,b):
        x=(point.x()-b[0])/max(1,b[2]-b[0]);y=(point.y()-b[1])/max(1,b[3]-b[1])
        horizontal='left' if x<.25 else ('right' if x>.75 else None)
        vertical='top' if y<.25 else ('bottom' if y>.75 else None)
        if horizontal is None and vertical is None:
            edge=min([(x,'left'),(1-x,'right'),(y,'top'),(1-y,'bottom')])[1]
            if edge in ('left','right'):horizontal=edge
            else:vertical=edge
        return horizontal,vertical

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
        self.button(tools,'Export all as WebP ZIP',self.export_webp)
        self.quick_toolbar=QToolBar('Quick tools');self.quick_toolbar.setIconSize(QSize(24,24));self.quick_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly);main.addWidget(self.quick_toolbar)
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
        self.canvas=Canvas(); self.canvas.box.connect(self.set_box); self.canvas.clicked.connect(self.select_at); split.addWidget(self.canvas)
        right=QWidget(); rr=QVBoxLayout(right)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(right);scroll.setMaximumWidth(385);split.addWidget(scroll)
        rr.addWidget(QLabel('When dragging on the page:'))
        self.mode=QComboBox(); self.mode.addItems(['Create balloon manually','Adjust erase area','Adjust translation area','Select background area']); rr.addWidget(self.mode)
        rr.addWidget(QLabel('Erase shape:'))
        self.erase_shape=QComboBox(); self.erase_shape.addItems(['Rectangle','Oval','Rounded rectangle']); rr.addWidget(self.erase_shape); self.erase_shape.currentIndexChanged.connect(self.edit)
        rr.addWidget(QLabel('Text shape:'))
        self.text_shape=QComboBox(); self.text_shape.addItems(['Rectangle','Oval','Rounded rectangle']); rr.addWidget(self.text_shape); self.text_shape.currentIndexChanged.connect(self.edit)
        rr.addWidget(QLabel('Text + erase angle (degrees, clockwise):'))
        self.text_angle=QSpinBox();self.text_angle.setRange(-180,180);self.text_angle.setSuffix('°');rr.addWidget(self.text_angle);self.text_angle.valueChanged.connect(self.edit)
        rr.addWidget(QLabel('Corner rounding (%):'))
        self.rounding=QSpinBox();self.rounding.setRange(0,100);self.rounding.setValue(50);rr.addWidget(self.rounding);self.rounding.valueChanged.connect(self.edit)
        self.canvas.rounding=lambda:self.rounding.value()
        rr.addWidget(QLabel('Move / resize selected balloon:'))
        self.transform_action=QComboBox();self.transform_action.addItems(['Off','Move','Resize']);rr.addWidget(self.transform_action)
        self.transform_target=QComboBox();self.transform_target.addItems(['Both areas','Text area only','Erase area only']);rr.addWidget(self.transform_target)
        dimensions=QHBoxLayout();rr.addLayout(dimensions)
        dimensions.addWidget(QLabel('Width:'));self.shape_width=QSpinBox();self.shape_width.setRange(6,30000);dimensions.addWidget(self.shape_width)
        dimensions.addWidget(QLabel('Height:'));self.shape_height=QSpinBox();self.shape_height.setRange(6,30000);dimensions.addWidget(self.shape_height)
        self.button(rr,'Apply size (pixels)',self.apply_shape_size)
        self.transform_target.currentIndexChanged.connect(self.update_shape_size)
        transform_hint=QLabel('Select a balloon in the list. Move: drag inside it. Resize: drag a corner or edge handle in any direction. The opposite edge stays fixed.');transform_hint.setWordWrap(True);rr.addWidget(transform_hint)
        self.canvas.transform_selection=self.transform_selection
        self.canvas.transformed.connect(self.transform_balloon)
        self.mode.currentIndexChanged.connect(lambda *_:self.transform_action.setCurrentIndex(0))
        self.mode.activated.connect(self.activate_mode)
        self.canvas.drag_shapes=self.drag_shapes
        self.original_view=QCheckBox('Show original page'); self.original_view.toggled.connect(self.draw); rr.addWidget(self.original_view)
        self.button(rr,'Fit page to window',self.fit)
        rr.addWidget(QLabel('Source language → English'))
        self.language=QComboBox(); self.language.addItem('Japanese','ja'); self.language.addItem('Chinese (Simplified)','ch_sim'); self.language.addItem('Chinese (Traditional)','ch_tra'); rr.addWidget(self.language)
        from translator_hy import MODEL
        model_label=QLabel('Translator: Hy-MT2-7B Q8 • local\n'+('Model downloaded' if MODEL.exists() else 'Run INSTALL_ALL.cmd to download'))
        model_label.setWordWrap(True);rr.addWidget(model_label)
        rr.addWidget(QLabel('Optional glossary (names / titles)'))
        self.glossary=QLineEdit();self.glossary.setPlaceholderText('Example: 博士 = Doctor; 阿米娅 = Amiya');rr.addWidget(self.glossary)
        self.vertical=QCheckBox('Vertical source text'); self.vertical.setChecked(True); rr.addWidget(self.vertical)
        self.column_order=QComboBox();self.column_order.addItems(['Columns: right → left','Columns: left → right']);rr.addWidget(self.column_order)
        self.vertical.toggled.connect(self.column_order.setEnabled)
        self.deskew=QCheckBox('Read diagonal text (slower)'); rr.addWidget(self.deskew)
        self.deskew.toggled.connect(self.settings_changed)
        rr.addWidget(QLabel('Source text • editable'))
        self.source=QTextEdit(); self.source.setMaximumHeight(90); self.source.textChanged.connect(self.edit); rr.addWidget(self.source)
        self.button(rr,'Read source text with local AI',self.ocr)
        rr.addWidget(QLabel('English translation • editable'))
        self.target=QTextEdit(); self.target.setMaximumHeight(90); self.target.textChanged.connect(self.edit); rr.addWidget(self.target)
        self.button(rr,'Translate source text to English',self.translate)
        self.button(rr,'Read and translate all balloons',self.batch)
        self.font_label=QLabel('Font: CC Wild Words Roman (default)' if self.font else 'Fallback font: Arial'); self.font_label.setWordWrap(True); rr.addWidget(self.font_label)
        self.button(rr,'Apply all translations on this page',self.apply_all)
        self.button(rr,'Style: black text with white outline',self.outlined_style)
        fontrow=QHBoxLayout(); rr.addLayout(fontrow); fontrow.addWidget(QLabel('Size in pixels:'))
        self.size=QSpinBox(); self.size.setRange(6,2048); self.size.setValue(30); self.size.valueChanged.connect(self.edit); fontrow.addWidget(self.size)
        rr.addWidget(QLabel('Colors for this balloon:'))
        self.text_color_button=self.button(rr,'Text color: #000000',lambda:self.choose_color('text_color'))
        self.outline_color_button=self.button(rr,'Outline color: #FFFFFF',lambda:self.choose_color('outline_color'))
        self.transparent=QCheckBox('Text over artwork (no white box)');self.transparent.toggled.connect(self.edit);rr.addWidget(self.transparent)
        outline_row=QHBoxLayout();rr.addLayout(outline_row);outline_row.addWidget(QLabel('Contrasting outline (px):'))
        self.outline=QSpinBox();self.outline.setRange(0,32);self.outline.valueChanged.connect(self.edit);outline_row.addWidget(self.outline)
        self.enabled=QCheckBox('Apply translation to this balloon'); self.enabled.toggled.connect(self.edit); rr.addWidget(self.enabled)
        self.button(rr,'Load font (.ttf / .otf)',self.choose_font)
        rr.addWidget(QLabel('All fonts on this page (manual sizes):'))
        sizes=QHBoxLayout();rr.addLayout(sizes)
        self.button(sizes,'Decrease by 2 px',lambda:self.resize_all(-2))
        self.button(sizes,'Increase by 2 px',lambda:self.resize_all(2))
        self.hint=QLabel('Open a file to get started.'); self.hint.setWordWrap(True); rr.addWidget(self.hint); rr.addStretch()
        split.setSizes([205,740,335]); self.statusBar().showMessage('Local • no page uploads • English output')
        self.setStyleSheet('QWidget{background:#171c26;color:#e5e9f0;font-size:13px} QPushButton{background:#303a4e;border:1px solid #44516b;border-radius:5px;padding:8px} QPushButton:hover{background:#43516b} QTextEdit,QListWidget,QComboBox,QSpinBox{background:#222b3a;border:1px solid #44516b;padding:4px} QCheckBox{padding:3px} QSplitter::handle{background:#303a4e}')

        self.transform_action.currentIndexChanged.connect(self.draw)
        self.transform_target.currentIndexChanged.connect(self.draw)
        self.language.currentIndexChanged.connect(self.settings_changed)
        self.glossary.textChanged.connect(self.settings_changed)
        self.vertical.toggled.connect(self.settings_changed)
        self.column_order.currentIndexChanged.connect(self.settings_changed)
        self.command_shortcuts=[]
        for key,action in [('Alt+1',lambda:self.activate_mode(0)),('Alt+2',lambda:self.activate_mode(1)),('Alt+3',lambda:self.activate_mode(2)),('Alt+4',lambda:self.activate_mode(3)),('Alt+M',lambda:self.transform_action.setCurrentText('Move')),('Alt+R',lambda:self.transform_action.setCurrentText('Resize')),('Alt+0',lambda:self.transform_action.setCurrentText('Off'))]:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.activated.connect(lambda fn=action:fn() if self.centralWidget().isEnabled() and self.pages else None)
            self.command_shortcuts.append(shortcut)
        self.button(ll,'Keyboard shortcuts (F1)',self.show_shortcuts)
        from toolbar_icons import icon
        entries=[('create','Create balloon','Alt+1',lambda:self.activate_mode(0)),('erase','Adjust erase area','Alt+2',lambda:self.activate_mode(1)),('text','Adjust text area','Alt+3',lambda:self.activate_mode(2)),('move','Move','Alt+M',lambda:self.transform_action.setCurrentText('Move')),('resize','Resize','Alt+R',lambda:self.transform_action.setCurrentText('Resize')),('background','Background area','Alt+4',self.start_background),('ocr','Read text','Alt+O',self.ocr),('translate','Translate','Alt+T',self.translate),('batch','Read and translate all','Alt+B',self.batch),('apply','Apply all translations','Alt+A',self.apply_all),('style','Black text with white outline','Alt+P',self.outlined_style),('undo','Undo','Ctrl+Z',self.undo),('fit','Fit page','Ctrl+0',self.fit),('help','Keyboard shortcuts','F1',self.show_shortcuts)]
        for name,label,key,callback in entries:
            if name in ('ocr','undo'):self.quick_toolbar.addSeparator()
            action=self.quick_toolbar.addAction(icon(name),label)
            action.setToolTip(f'{label} ({key})');action.setStatusTip(f'{label} ({key})')
            action.triggered.connect(lambda checked=False,fn=callback:fn())



    def activate_mode(self,index):
        self.transform_action.setCurrentIndex(0)
        self.mode.setCurrentIndex(index)

    def settings_changed(self,*_):
        if self.pages and not self.loading:self.dirty=True
    def project_settings(self):
        return {'language':self.language.currentData(),'glossary':self.glossary.text(),
                'deskew':self.deskew.isChecked(),'vertical':self.vertical.isChecked(),'rtl':self.column_order.currentIndex()==0}
    def button(self,layout,label,fn):
        b=QPushButton(label); b.clicked.connect(fn); layout.addWidget(b)
        key={'Open PDF / multiple images':'Ctrl+O','Open project':'Ctrl+Shift+O','Save project':'Ctrl+S','Export PDF':'Ctrl+E','Export page as PNG':'Ctrl+Shift+E','Export all as WebP ZIP':'Ctrl+Alt+E','Read source text with local AI':'Alt+O','Translate source text to English':'Alt+T','Read and translate all balloons':'Alt+B','Apply all translations on this page':'Alt+A','Fit page to window':'Ctrl+0','Style: black text with white outline':'Alt+P','Apply size (pixels)':'Alt+Enter','Keyboard shortcuts (F1)':'F1'}.get(label)
        if key:b.setShortcut(QKeySequence(key));b.setToolTip(f'{label} ({key})')
        return b

    def show_shortcuts(self):
        QMessageBox.information(self,'Keyboard shortcuts',
            'Ctrl+O: Open images / PDF\nCtrl+Shift+O: Open project\nCtrl+S: Save project\nCtrl+E: Export PDF\nCtrl+Shift+E: Export PNG\nCtrl+Alt+E: Export WebP ZIP\nCtrl+Z: Undo\nCtrl+0: Fit page\n\nAlt+1: Create balloon\nAlt+2: Adjust erase area\nAlt+3: Adjust text area\nAlt+4: Background area\nAlt+M: Move\nAlt+R: Resize\nAlt+0: Stop moving / resizing\nAlt+Enter: Apply size\n\nAlt+O: Read text (OCR)\nAlt+T: Translate selected text\nAlt+B: Read and translate all balloons\nAlt+A: Apply all translations\nAlt+P: Black text with white outline\n\nWheel: scroll without changing options. Ctrl+wheel on the page: zoom.')

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
        # Freeze legacy automatic sizes at their rendered size before editing.
        for page in pages:
            for region in page.regions:
                if region.auto_fit:
                    if region.translation.strip():region.size=region_layout(region,self.font)[1].size
                    region.auto_fit=False
        if settings is not None:
            self.loading=True
            language=language_code(settings.get('language','ja'))
            self.language.setCurrentIndex(self.language.findData(language))
            self.glossary.setText(settings.get('glossary',''))
            self.deskew.setChecked(settings.get('deskew',False))
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
        if r:
            self.text_angle.setValue(r.text_angle)
            self.rounding.setValue(r.corner_rounding)
            self.erase_shape.setCurrentIndex(['rectangle','oval','rounded'].index(r.erase_shape))
            self.text_shape.setCurrentIndex(['rectangle','oval','rounded'].index(r.text_shape))
        self.size.setValue(r.size if r else 30); self.enabled.setChecked(r.enabled if r else False)
        for field,button,label,default in [('text_color',self.text_color_button,'Text color','black'),('outline_color',self.outline_color_button,'Outline color','white')]:
            color=QColor(getattr(r,field) if r else default)
            button.setText(f'{label}: {color.name().upper()}')
            button.setStyleSheet(f'border-left: 14px solid {color.name()};')
            button.setEnabled(r is not None)
        self.transparent.setChecked(r.transparent if r else False);self.outline.setValue(r.outline if r else 0)
        self.loading=False; self.update_shape_size(); self.draw()
    def edit(self,*_):
        if self.loading or not self.region(): return
        self.checkpoint(); r=self.region(); r.original=self.source.toPlainText(); r.translation=normalize_translation(self.target.toPlainText()); r.size=self.size.value(); r.auto_fit=False; r.enabled=self.enabled.isChecked()
        if self.target.toPlainText()!=r.translation:
            self.target.blockSignals(True);self.target.setPlainText(r.translation);self.target.blockSignals(False)
        r.text_angle=self.text_angle.value()
        r.corner_rounding=self.rounding.value()
        r.erase_shape=['rectangle','oval','rounded'][self.erase_shape.currentIndex()]
        r.text_shape=['rectangle','oval','rounded'][self.text_shape.currentIndex()]
        r.transparent=self.transparent.isChecked();r.outline=self.outline.value()
        item=self.list.currentItem()
        if item: item.setText(f'Balloon {self.list.currentRow()+1}'+(' • applied' if r.enabled else ' • review'))
        self.draw()
    def choose_color(self,field):
        r=self.region()
        if r is None:return
        title='Choose text color' if field=='text_color' else 'Choose outline color'
        color=QColorDialog.getColor(QColor(getattr(r,field)),self,title,QColorDialog.DontUseNativeDialog)
        if not color.isValid() or color.name()==QColor(getattr(r,field)).name():return
        self.checkpoint();setattr(r,field,color.name());self.select()
    def outlined_style(self):
        r=self.region()
        if r is None:return
        actual=region_layout(r,self.font)[1].size if r.translation.strip() else r.size
        self.checkpoint()
        r.text_color='black';r.outline_color='white';r.transparent=True
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
        self.size.setEnabled(bool(selected))
        self.transform_action.setEnabled(bool(selected));self.transform_target.setEnabled(bool(selected))
        if not selected:self.transform_action.setCurrentIndex(0)
        try: im,warnings=render_page(p,self.font) if not self.original_view.isChecked() else (p.image,[])
        except Exception as e: self.error(str(e)); return
        self.hint.setText('\n'.join(warnings) if warnings else 'Drag to define the selected area. Review the text before applying.')
        data=im.tobytes('raw','RGB'); q=QImage(data,im.width,im.height,im.width*3,QImage.Format_RGB888).copy()
        self.canvas.scene().clear(); self.canvas.scene().addPixmap(QPixmap.fromImage(q)); self.canvas.setSceneRect(0,0,im.width,im.height)
        for i,r in enumerate(p.regions):
            for box,color,shape,angle in [(r.erase,'#49aaff',r.erase_shape,r.text_angle),(r.text_box,'#32d9a4',r.text_shape,r.text_angle)]:
                pen=QPen(QColor(color),3 if i==self.list.currentRow() else 1); pen.setCosmetic(True)
                item=self.canvas.add_shape(QRectF(box[0],box[1],box[2]-box[0],box[3]-box[1]),pen,shape,r.corner_rounding)
                item.setTransformOriginPoint((box[0]+box[2])/2,(box[1]+box[3])/2);item.setRotation(angle)
        selection=self.transform_selection()
        if selection and selection[0]=='Resize':
            _,b=selection;cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
            radius=4/max(.01,self.canvas.transform().m11())
            pen=QPen(QColor('#ffcc66'),2);pen.setCosmetic(True)
            for x,y in [(b[0],b[1]),(cx,b[1]),(b[2],b[1]),(b[0],cy),(b[2],cy),(b[0],b[3]),(cx,b[3]),(b[2],b[3])]:
                self.canvas.scene().addRect(QRectF(x-radius,y-radius,2*radius,2*radius),pen)
    def select_at(self,point):
        if not self.page():return
        hits=[]
        for index,region in enumerate(self.page().regions):
            for box,shape,angle in [(region.erase,region.erase_shape,region.text_angle),(region.text_box,region.text_shape,region.text_angle)]:
                rect=QRectF(box[0],box[1],box[2]-box[0],box[3]-box[1]);path=QPainterPath()
                if shape=='oval':path.addEllipse(rect)
                elif shape=='rounded':
                    radius=min(rect.width(),rect.height())*region.corner_rounding/200
                    path.addRoundedRect(rect,radius,radius)
                else:path.addRect(rect)
                if angle:
                    center=rect.center();transform=QTransform();transform.translate(center.x(),center.y());transform.rotate(angle);transform.translate(-center.x(),-center.y());path=transform.map(path)
                if path.contains(point):hits.append((rect.width()*rect.height(),-index,index))
        if hits:self.list.setCurrentRow(min(hits)[2])

    def fit(self):
        if self.page(): self.canvas.fitInView(self.canvas.sceneRect(),Qt.KeepAspectRatio)
    def update_shape_size(self,*_):
        r=self.region()
        if not r:return
        target=self.transform_target.currentIndex()
        boxes=[r.erase,r.text_box] if target==0 else [r.text_box if target==1 else r.erase]
        self.shape_width.setValue(max(b[2] for b in boxes)-min(b[0] for b in boxes))
        self.shape_height.setValue(max(b[3] for b in boxes)-min(b[1] for b in boxes))

    def apply_shape_size(self):
        if not self.region():return
        previous=self.transform_action.currentIndex();self.transform_action.setCurrentText('Resize')
        _,b=self.transform_selection();p=self.page()
        self.transform_balloon([b[0],b[1],min(p.image.width,b[0]+self.shape_width.value()),min(p.image.height,b[1]+self.shape_height.value())])
        self.transform_action.setCurrentIndex(previous);self.update_shape_size()

    def transform_selection(self):
        r=self.region()
        if not r or self.transform_action.currentIndex()==0:return None
        target=self.transform_target.currentIndex()
        boxes=[r.erase,r.text_box] if target==0 else [r.text_box if target==1 else r.erase]
        bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
        return self.transform_action.currentText(),bounds

    def transform_balloon(self,box):
        selection=self.transform_selection()
        if not selection:return
        action,old=selection
        if old==box:return
        self.checkpoint();r=self.region();target=self.transform_target.currentIndex()
        for field in (['erase','text_box'] if target==0 else ['text_box' if target==1 else 'erase']):
            b=getattr(r,field)
            if action=='Move':
                dx=box[0]-old[0];dy=box[1]-old[1];new=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
            else:
                sx=(box[2]-box[0])/max(1,old[2]-old[0]);sy=(box[3]-box[1])/max(1,old[3]-old[1])
                new=[round(box[0]+(b[0]-old[0])*sx),round(box[1]+(b[1]-old[1])*sy),round(box[0]+(b[2]-old[0])*sx),round(box[1]+(b[3]-old[1])*sy)]
                new[2]=max(new[0]+1,new[2]);new[3]=max(new[1]+1,new[3])
            setattr(r,field,new)
        self.update_shape_size();self.draw()

    def drag_shapes(self):
        erase=['rectangle','oval','rounded'][self.erase_shape.currentIndex()]
        text=['rectangle','oval','rounded'][self.text_shape.currentIndex()]
        mode=self.mode.currentIndex()
        if mode==1:return [(erase,'#49aaff')]
        if mode==2:return [(text,'#32d9a4')]
        if mode==3:return [('rectangle','#38d9a9')]
        return [(text,'#32d9a4')] if erase==text else [(erase,'#49aaff'),(text,'#32d9a4')]

    def set_box(self,box):
        if not self.page(): return
        mode=self.mode.currentIndex()
        if mode==3:self.edit_background(box);return
        if mode and not self.region(): return
        self.checkpoint()
        if mode==0:
            self.page().regions.append(Region(box.copy(),box.copy(),text_angle=self.text_angle.value(),corner_rounding=self.rounding.value(),erase_shape=['rectangle','oval','rounded'][self.erase_shape.currentIndex()],text_shape=['rectangle','oval','rounded'][self.text_shape.currentIndex()])); self.refresh(len(self.page().regions)-1)
        else:
            if mode==1: self.region().erase=box
            else: self.region().text_box=box
            self.draw()
    def start_background(self):
        if not self.page():self.error('Open a page before using the background tool.');return
        self.activate_mode(3)
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
        image=self.page().image.crop(r.erase); language=self.language.currentData(); vertical=self.vertical.isChecked();rtl=self.column_order.currentIndex()==0;deskew=self.deskew.isChecked()
        self.run(lambda:self.ai.read(image,language,vertical,rtl,deskew),lambda text:self.source.setPlainText(text),'Reading text and comparing background preprocessing. First use may download OCR models…')
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
        p=self.page(); language=self.language.currentData(); vertical=self.vertical.isChecked();glossary=self.glossary.text();rtl=self.column_order.currentIndex()==0;deskew=self.deskew.isChecked()
        todo=copy.deepcopy(p.regions)
        page_number=self.index+1
        def job():
            for i,r in enumerate(todo):
                if not r.original.strip():
                    try:r.original=self.ai.read(p.image.crop(r.erase),language,vertical,rtl,deskew)
                    except Exception as error:
                        raise RuntimeError(f'Page {page_number} — Balloon {i+1}: OCR failed.\n\n{error}\n\nSelect Balloon {i+1} in the list to review its area and language. No batch changes were applied.') from error
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
    def export_webp(self):
        if not self.pages or self.worker:return
        if not self.font and any(r.enabled and r.translation.strip() for p in self.pages for r in p.regions):
            self.error('Load a font before exporting.');return
        path,_=QFileDialog.getSaveFileName(self,'Export all pages as WebP ZIP','','ZIP archive (*.zip)')
        if not path:return
        if not path.lower().endswith('.zip'):path+='.zip'
        pages=list(self.pages);font=self.font
        self.run(lambda:export_webp_zip(path,pages,font),
                 lambda saved:self.statusBar().showMessage('WebP ZIP exported: '+saved),
                 f'Exporting {len(pages)} pages as lossless WebP in a ZIP…')
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
