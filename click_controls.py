"""Controls never change values in response to wheel scrolling."""
from PySide6.QtWidgets import QComboBox as BaseCombo, QSpinBox as BaseSpin

class QComboBox(BaseCombo):
    def wheelEvent(self,event):
        event.ignore()

class QSpinBox(BaseSpin):
    def wheelEvent(self,event):
        event.ignore()
