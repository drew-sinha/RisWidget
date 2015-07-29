# The MIT License (MIT)
#
# Copyright (c) 2015 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum <ice.rikh@gmail.com>

from PyQt5 import Qt

class SliderDelegate(Qt.QStyledItemDelegate):
    def __init__(self, min_value, max_value, parent=None):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value

    def sizeHint(self, option, midx):
        return Qt.QSize(100,10)

    def paint(self, qpainter, option, midx):
        if not midx.isValid():
            return
        d = midx.data()
        if isinstance(d, Qt.QVariant):
            d = d.value()
        pbo = Qt.QStyleOptionProgressBar()
        pbo.minimum, pbo.maximum = 0, 100
        pbo.progress = int( (d-self.min_value)/(self.max_value-self.min_value) * 100.0 )
        pbo.text = '{}%'.format(pbo.progress)
        pbo.textVisible = True
        pbo.rect = option.rect
        style = option.widget.style() if option.widget is not None else Qt.QApplication.style()
        style.drawControl(Qt.QStyle.CE_ProgressBar, pbo, qpainter)

    def editorEvent(self, event, model, option, midx):
        if not midx.isValid() or event.type() not in (Qt.QEvent.MouseButtonPress, Qt.QEvent.MouseMove) or event.buttons() != Qt.Qt.LeftButton:
            return False
        r = option.rect
        mx = event.localPos().x()
        sl, sw = r.left(), r.width()
        v = ((mx - sl) / sw) * (self.max_value - self.min_value) + self.min_value
        if v < self.min_value:
            v = self.min_value
        elif v > self.max_value:
            v = self.max_value
        return model.setData(midx, Qt.QVariant(v), Qt.Qt.EditRole)