"""Small vector toolbar icons, rendered locally at high DPI."""
from PySide6.QtCore import QByteArray,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS={
'create':'<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/>',
'erase':'<path d="m4 14 9-10 8 7-8 10H9zM8 10l8 7M3 21h18"/>',
'text':'<rect x="3" y="3" width="18" height="18" stroke-dasharray="2 2"/><path d="M7 7h10M12 7v11M9 18h6"/>',
'move':'<path d="M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4"/>',
'resize':'<rect x="4" y="4" width="16" height="16" stroke-dasharray="2 2"/><path d="M7 17 17 7M10 7h7v7M7 10v7h7"/>',
'background':'<path d="m4 16 11-12 5 5-11 12H4zM12 7l5 5M3 22h18"/>',
'ocr':'<path d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5M7 16l5-9 5 9M9 13h6"/>',
'translate':'<path d="M3 5h10M8 2v3M5 5c0 6 4 9 8 10M12 5c0 6-4 9-9 10M14 21l4-10 4 10M16 17h4"/>',
'batch':'<path d="M3 4h12v3M3 4v13h3"/><rect x="7" y="8" width="14" height="13" rx="2"/><path d="m10 14 3 3 5-6"/>',
'apply':'<path d="m3 12 6 6L21 5M3 20h18"/>',
'style':'<path d="m6 20 6-16 6 16M8 15h8" stroke="white" stroke-width="6"/><path d="m6 20 6-16 6 16M8 15h8" stroke="black" stroke-width="2"/>',
'undo':'<path d="m9 3-6 6 6 6M3 9h11a7 7 0 0 1 0 14"/>',
'fit':'<path d="M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6"/><rect x="8" y="8" width="8" height="8"/>',
'help':'<circle cx="12" cy="12" r="9"/><path d="M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 4M12 17v1"/>'}
def icon(name):
 svg=('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="#e5e9f0" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+PATHS[name]+'</g></svg>')
 pix=QPixmap(48,48);pix.fill(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.transparent);pix.setDevicePixelRatio(2)
 painter=QPainter(pix);QSvgRenderer(QByteArray(svg.encode())).render(painter,QRectF(0,0,24,24));painter.end();return QIcon(pix)

