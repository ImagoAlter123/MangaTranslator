"""Experimental mask-based restoration; classical methods and optional local LaMa."""
import numpy as np
import cv2
from PIL import Image,ImageDraw
from PySide6.QtCore import Qt,Signal,QThread
from PySide6.QtGui import QImage,QPixmap,QColor,QShortcut,QKeySequence
from PySide6.QtWidgets import (QDialog,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QComboBox,
    QSpinBox,QCheckBox,QGraphicsView,QGraphicsScene,QMessageBox,QWidget,QScrollArea)


def restore(image,mask,method,color=(255,255,255),anchor=None,radius=3):
    source=np.array(image.convert('RGB'));m=np.array(mask.convert('L'))>0
    if not m.any():raise ValueError('Mark the letters in red before generating a preview.')
    if method==3:
        from lama_local import inpaint
        return inpaint(image,mask)
    result=source.copy()
    if method==0:
        if m.all():raise ValueError('Leave some background unmasked as a reference.')
        repaired=cv2.inpaint(source,m.astype('uint8')*255,radius,cv2.INPAINT_TELEA)
        result[m]=repaired[m]
    elif method==1:result[m]=color
    else:
        if anchor is None:raise ValueError('Select “Texture source” and click the start of a clean area.')
        yy,xx=np.where(m);sx=xx-xx.min()+anchor[0];sy=yy-yy.min()+anchor[1]
        if sx.min()<0 or sy.min()<0 or sx.max()>=image.width or sy.max()>=image.height:
            raise ValueError('The source texture does not fit in this crop. Choose another point or select a larger area on the page.')
        if m[sy,sx].any():raise ValueError('The texture source overlaps the mask. Choose a clean area outside the marked letters.')
        result[yy,xx]=source[sy,sx]
    return Image.fromarray(result)


class LamaWorker(QThread):
    completed=Signal(object)
    failed=Signal(str)
    def __init__(self,image,mask,parent):
        super().__init__(parent);self.image=image.copy();self.mask=mask.copy()
    def run(self):
        try:self.completed.emit(restore(self.image,self.mask,3))
        except Exception as error:self.failed.emit(str(error))


class MaskView(QGraphicsView):
    point=Signal(int,int,bool)
    def __init__(self):
        super().__init__();self.setScene(QGraphicsScene(self));self.down=False
        self.setMinimumSize(400,400);self.setBackgroundBrush(QColor('#222733'))
    def emit_point(self,event,first):
        p=self.mapToScene(event.position().toPoint());self.point.emit(round(p.x()),round(p.y()),first)
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.down=True;self.emit_point(event,True)
        else:super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self.down:self.emit_point(event,False)
        else:super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):self.down=False
    def wheelEvent(self,event):
        if event.modifiers() & Qt.ControlModifier:
            factor=1.15 if event.angleDelta().y()>0 else 1/1.15;self.scale(factor,factor)
        else:super().wheelEvent(event)


class BackgroundEditor(QDialog):
    def __init__(self,image,parent=None):
        super().__init__(parent);self.setWindowTitle('Background — experimental');self.resize(1080,760)
        self.image=image.convert('RGB').copy();self.mask=Image.new('L',image.size,0);self.result=None
        self.color=(255,255,255);self.anchor=None;self.previous=None;self.history=[];self.worker=None
        row=QHBoxLayout(self);self.view=MaskView();row.addWidget(self.view,1)
        panel_widget=QWidget();panel=QVBoxLayout(panel_widget);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(panel_widget);scroll.setFixedWidth(350);row.addWidget(scroll)
        intro=QLabel('1. Mark the letters and their outlines.\n2. Choose a treatment.\n3. Generate a preview and apply.\n\nRed = pixels that will change.');intro.setWordWrap(True);panel.addWidget(intro)
        self.tool=QComboBox();self.tool.addItems(['Mask brush','Mask eraser','Pick color','Texture source']);panel.addWidget(self.tool)
        panel.addWidget(QLabel('Brush diameter (pixels)'));self.brush=QSpinBox();self.brush.setRange(1,150);self.brush.setValue(12);panel.addWidget(self.brush)
        panel.addWidget(QLabel('Contrast-based suggestion (check artwork):'))
        self.ink=QComboBox();self.ink.addItems(['Dark pixels','Light pixels']);panel.addWidget(self.ink)
        self.threshold=QSpinBox();self.threshold.setRange(0,255);self.threshold.setValue(100);panel.addWidget(self.threshold)
        self.button(panel,'Suggest mask',self.suggest)
        self.button(panel,'Expand mask by 1 pixel',self.grow)
        self.button(panel,'Clear mask',self.clear)
        self.button(panel,'Undo mask (Ctrl+Z)',self.undo)
        self.undo_shortcut=QShortcut(QKeySequence('Ctrl+Z'),self)
        self.undo_shortcut.setContext(Qt.WindowShortcut)
        self.undo_shortcut.activated.connect(self.undo)
        panel.addWidget(QLabel('Background treatment:'))
        self.method=QComboBox();self.method.addItems(['Reconstruct from nearby pixels','Fill with color','Copy nearby texture','Reconstruct with AI — LaMa (CPU)']);self.method.currentIndexChanged.connect(self.invalidate);panel.addWidget(self.method)
        panel.addWidget(QLabel('Reconstruction radius (pixels)'));self.radius=QSpinBox();self.radius.setRange(1,15);self.radius.setValue(3);self.radius.valueChanged.connect(self.invalidate);panel.addWidget(self.radius)
        self.sample_label=QLabel('Color: white • source: not set');self.sample_label.setWordWrap(True);panel.addWidget(self.sample_label)
        self.preview_button=self.button(panel,'Generate preview',self.preview)
        self.status=QLabel('LaMa: run BAIXAR_LAMA.cmd once to install.');self.status.setWordWrap(True);panel.addWidget(self.status)
        self.show_result=QCheckBox('Show result (uncheck to compare)');self.show_result.toggled.connect(self.draw);panel.addWidget(self.show_result)
        self.show_mask=QCheckBox('Show red mask');self.show_mask.setChecked(True);self.show_mask.toggled.connect(self.draw);panel.addWidget(self.show_mask)
        self.apply_button=self.button(panel,'Apply background',self.accept);self.apply_button.setEnabled(False)
        self.button(panel,'Cancel',self.reject)
        note=QLabel('Experimental. LaMa may take minutes on CPU.\nAll methods may alter tones and lines.\nReview before applying.\nCtrl + wheel: zoom. Scrollbars: pan.');note.setWordWrap(True);panel.addWidget(note);panel.addStretch()
        self.view.point.connect(self.paint);self.draw()
    def showEvent(self,event):
        super().showEvent(event);self.view.fitInView(self.view.sceneRect(),Qt.KeepAspectRatio)
    def button(self,panel,text,fn):
        b=QPushButton(text);b.clicked.connect(fn);panel.addWidget(b);return b
    def checkpoint(self):
        self.history.append(self.mask.copy());self.history=self.history[-15:]
    def invalidate(self,*_):
        self.result=None;self.apply_button.setEnabled(False);self.show_result.setChecked(False);self.draw()
    def paint(self,x,y,first):
        if not (0<=x<self.image.width and 0<=y<self.image.height):self.previous=None;return
        mode=self.tool.currentIndex()
        if mode>1:
            if not first:return
            if mode==2:self.color=self.image.getpixel((x,y))
            else:self.anchor=(x,y)
            self.sample_label.setText(f'Color: {self.color}\nSource: {self.anchor or "not set"}');self.invalidate();return
        if first:self.checkpoint();self.previous=None
        self.show_mask.setChecked(True)
        d=ImageDraw.Draw(self.mask);size=self.brush.value();r=size/2;value=255 if mode==0 else 0
        if self.previous:d.line([self.previous,(x,y)],fill=value,width=size)
        d.ellipse((x-r,y-r,x+r,y+r),fill=value);self.previous=(x,y);self.invalidate()
    def suggest(self):
        self.checkpoint();gray=np.array(self.image.convert('L'));level=self.threshold.value()
        self.mask=Image.fromarray(((gray<level) if self.ink.currentIndex()==0 else (gray>level)).astype('uint8')*255);self.invalidate()
    def grow(self):
        self.checkpoint();self.mask=Image.fromarray(cv2.dilate(np.array(self.mask),np.ones((3,3),np.uint8)));self.invalidate()
    def clear(self):self.checkpoint();self.mask=Image.new('L',self.image.size,0);self.invalidate()
    def undo(self):
        if self.history:self.mask=self.history.pop();self.invalidate()
    def preview(self):
        if self.worker is not None:return
        if self.method.currentIndex()==3:
            self.invalidate()
            self.status.setText('LaMa is reconstructing on CPU. Please wait; this may take minutes in a VM.')
            self.setEnabled(False)
            self.worker=LamaWorker(self.image,self.mask,self)
            self.worker.completed.connect(self.lama_done)
            self.worker.failed.connect(self.lama_failed)
            self.worker.finished.connect(self.lama_finished)
            self.worker.start();return
        try:self.result=restore(self.image,self.mask,self.method.currentIndex(),self.color,self.anchor,self.radius.value())
        except Exception as error:QMessageBox.warning(self,'Review the selection',str(error));return
        self.show_mask.setChecked(False);self.show_result.setChecked(True);self.apply_button.setEnabled(True);self.draw()
    def lama_done(self,result):
        self.result=result;self.show_mask.setChecked(False);self.show_result.setChecked(True)
        self.apply_button.setEnabled(True);self.status.setText('LaMa preview ready. Compare before applying.');self.draw()
    def lama_failed(self,message):
        self.status.setText('Unable to generate the LaMa preview.')
        QMessageBox.warning(self,'LaMa',message)
    def lama_finished(self):
        self.worker.deleteLater();self.worker=None;self.setEnabled(True)
    def reject(self):
        if self.worker is None:super().reject()
    def closeEvent(self,event):
        if self.worker is not None:event.ignore()
        else:super().closeEvent(event)
    def accept(self):
        if self.result is not None:super().accept()
    def draw(self,*_):
        im=(self.result if self.show_result.isChecked() and self.result is not None else self.image).copy()
        if self.show_mask.isChecked():
            mask=np.array(self.mask)>0;a=np.array(im);a[mask]=(a[mask]*.45+np.array([255,35,55])*.55).astype('uint8');im=Image.fromarray(a)
        if self.anchor:
            x,y=self.anchor;d=ImageDraw.Draw(im);d.line((x-7,y,x+7,y),fill=(40,130,255),width=2);d.line((x,y-7,x,y+7),fill=(40,130,255),width=2)
        data=im.tobytes();q=QImage(data,im.width,im.height,im.width*3,QImage.Format_RGB888).copy()
        self.view.scene().clear();self.view.scene().addPixmap(QPixmap.fromImage(q));self.view.setSceneRect(0,0,im.width,im.height)
