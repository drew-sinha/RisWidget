# This code is licensed under the MIT License (see LICENSE file for details)

from PyQt5 import Qt
from .. import shared_resources

class ContextualInfoItem(Qt.QGraphicsSimpleTextItem):
    QGRAPHICSITEM_TYPE = shared_resources.generate_unique_qgraphicsitem_type()

    def __init__(self, parent_item):
        super().__init__(parent_item)
        self.contextual_info = None
        font = Qt.QFont('Courier', pointSize=16, weight=Qt.QFont.Bold)
        font.setKerning(False)
        font.setStyleHint(Qt.QFont.Monospace, Qt.QFont.OpenGLCompatible | Qt.QFont.PreferQuality)
        self.setFont(font)
        self.setBrush(Qt.QColor(45,220,255))
        # below is useful if you want a pen behind the brush (also uncomment paint())
        # self.brush = Qt.QBrush(Qt.QColor(45,220,255))
        # self.pen = Qt.QPen(Qt.QColor(Qt.Qt.black))
        # self.pen.setWidth(2)
        # self.pen.setCosmetic(True)
        # # self.no_pen = Qt.QPen(Qt.Qt.NoPen)
        # # self.no_brush = Qt.QBrush(Qt.Qt.NoBrush)
        # # Disabling brush/pen via setting to transparent color causes less problems on OS X for some reason
        # transparent_color = Qt.QColor(Qt.QColor(255, 255, 255, 0))
        # self.no_pen = Qt.QPen(transparent_color)
        # self.no_brush = Qt.QBrush(transparent_color)

        # Necessary to prevent context information from disappearing when mouse pointer passes over
        # context info text
        self.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(Qt.Qt.NoButton)
        self.hide()

    def type(self):
        return self.QGRAPHICSITEM_TYPE

    def set_info_text(self, text):
        if not text:
            self.hide()
        else:
            self.setText(text)
            self.show()

    # def paint(self, qpainter, option, widget):
    #     # To ensure that character outlines never obscure the entirety of character interior, outline
    #     # is drawn first and interior second.  If both brush and pen are nonempty, Qt draws interior first
    #     # and outline second.
    #     self.setBrush(self.no_brush)
    #     self.setPen(self.pen)
    #     super().paint(qpainter, option, widget)
    #     self.setBrush(self.brush)
    #     self.setPen(self.no_pen)
    #     super().paint(qpainter, option, widget)
