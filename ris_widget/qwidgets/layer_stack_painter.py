# The MIT License (MIT)
#
# Copyright (c) 2016 WUSTL ZPLAB
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

import numpy
from PyQt5 import Qt
from ..qgraphicsitems.layer_stack_painter_item import LayerStackPainterBrush, LayerStackPainterItem

class LabelSliderEdit(Qt.QObject):
    value_changed = Qt.pyqtSignal(Qt.QObject)
    FLOAT_MAX = int(1e9)

    def __init__(self, layout, label_text, type_, min_, max_, odd_values_only=False, max_is_hard=True, value=...):
        super().__init__()
        min_, max_ = type_(min_), type_(max_)
        assert type_ is int or type_ is float and not odd_values_only
        assert min_ < max_
        self.odd_values_only = odd_values_only
        self.ignore_change = False
        self.min, self.max = min_, max_
        self.max_is_hard = max_is_hard
        self.type = type_
        r = layout.rowCount()
        self.label = Qt.QLabel(label_text)
        layout.addWidget(self.label, r, 0, Qt.Qt.AlignRight)
        self.slider = Qt.QSlider(Qt.Qt.Horizontal)
        if type_ is float:
            self.factor = (max_ - min_) / self.FLOAT_MAX
            self.slider.setRange(0, self.FLOAT_MAX)
        else:
            self.slider.setRange(min_, max_)
            if odd_values_only:
                assert self.min % 2 == 0
            self.slider.setSingleStep(2)
        self.slider.valueChanged.connect(self._on_slider_value_changed)
        layout.addWidget(self.slider, r, 1)
        self.editbox = Qt.QLineEdit()
        self.editbox.editingFinished.connect(self._on_editbox_editing_finished)
        layout.addWidget(self.editbox, r, 2, Qt.Qt.AlignRight)
        self._value = None
        if value is not ...:
            self.value = value

    def _on_slider_value_changed(self, v):
        if self.ignore_change:
            return
        if self.type is float:
            v *= self.factor
            v += self.min
        if v != self._value:
            if self.odd_values_only:
                v = min(max(v - (1 - v % 2), self.min), self.max)
            self._value = v
            self._update_editbox()
            self.value_changed.emit(self)

    def _on_editbox_editing_finished(self):
        if self.ignore_change:
            return
        try:
            v = self.parse_value(self.editbox.text())
            if v != self._value:
                self._value = v
                self._update_slider()
                self.value_changed.emit(self)
        except ValueError:
            self._update_editbox()

    def _update_slider(self):
        self.ignore_change = True
        try:
            s = self.slider
            if self.type is float:
                sv = min(max(int((self._value - self.min) / self.factor), 0), s.maximum())
            else:
                sv = min(max(self._value, s.minimum()), s.maximum())
            s.setValue(sv)
        finally:
            self.ignore_change = False

    def _update_editbox(self):
        self.ignore_change = True
        try:
            self.editbox.setText(str(self._value))
        finally:
            self.ignore_change = False

    def parse_value(self, v):
        v = self.type(v)
        if v < self.min or self.max_is_hard and v > self.max:
            raise ValueError()
        if self.odd_values_only and v % 2 == 0:
            raise ValueError()
        return v

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        v = self.parse_value(v)
        if self._value != v:
            self._value = v
            self._update_editbox()
            self._update_slider()
            self.value_changed.emit(self)

class BrushBox(Qt.QGroupBox):
    def __init__(self, brush_size_lse, title, brush_name, painter_item, default_to_min):
        super().__init__(title)
        self.painter_item = painter_item
        self.brush_name = brush_name
        self.default_to_min = default_to_min
        self.setLayout(Qt.QGridLayout())
        painter_item.target_image_changed.connect(self._on_target_image_changed)
        self.channel_value_set_key = None
        self.channel_value_sets = {}
        self.channel_lses = {}
        self.brush_size_lse = brush_size_lse
        self.brush_size_lse.value_changed.connect(self._on_brush_size_lse_value_changed)
        self._on_target_image_changed()

    def _destroy_channel_lses(self):
        l = self.layout()
        for lse in self.channel_lses.values():
            l.removeWidget(lse.label)
            lse.label.deleteLater()
            l.removeWidget(lse.slider)
            lse.slider.deleteLater()
            l.removeWidget(lse.editbox)
            lse.editbox.deleteLater()
        self.channel_lses = {}

    def _on_target_image_changed(self):
        ti = self.painter_item.target_image
        if ti is None:
            self._destroy_channel_lses()
            self.setEnabled(False)
            self.channel_value_set_key = None
            return
        cvsk = ti.data.dtype, ti.type, (ti.valid_range[0], ti.valid_range[1])
        if self.channel_value_set_key != cvsk:
            self.channel_value_set_key = cvsk
            try:
                cvs = self.channel_value_sets[cvsk]
            except KeyError:
                default_value = ti.valid_range[0] if self.default_to_min else ti.valid_range[1]
                cvs = {c : default_value for c in ti.type}
            self._destroy_channel_lses()
            self.setEnabled(True)
            t = float if numpy.issubdtype(ti.data.dtype, numpy.floating) else int
            m, M = ti.valid_range
            self.channel_lses = {c : LabelSliderEdit(self.layout(), c, t, m, M, value=v) for (c, v) in cvs.items()}
            for channel_lse in self.channel_lses.values():
                channel_lse.value_changed.connect(self._on_channel_lse_value_changed)
        self.update_brush()

    def update_brush(self):
        ti = self.painter_item.target_image
        if ti is None:
            self.painter_item.brush = None
        else:
            bs = self.brush_size_lse.value
            channel_count = len(ti.type)
            if channel_count == 1:
                b = numpy.empty((bs, bs), ti.data.dtype, 'F')
                color = self.channel_lses[ti.type].value
            else:
                bpe = ti.data.itemsize
                b = numpy.ndarray((bs, bs, channel_count), strides=(channel_count*bpe, channel_count*bs*bpe, bpe), dtype=ti.data.dtype)
                color = [self.channel_lses[c].value for c in ti.type]
            b[:, :] = color
            m = numpy.zeros((bs, bs), bool, 'F')
            r = int(bs/2)
            y, x = numpy.ogrid[-r:bs-r, -r:bs-r]
            m[y*y + x*x <= r*r] = True
            setattr(self.painter_item, self.brush_name, LayerStackPainterBrush(b, m, (r,r)))

    def _on_brush_size_lse_value_changed(self):
        ti = self.painter_item.target_image
        if ti is None:
            return
        self.update_brush()

    def _on_channel_lse_value_changed(self):
        ti = self.painter_item.target_image
        if ti is None:
            return
        self.update_brush()
        self.channel_value_sets[self.channel_value_set_key] = {c : self.channel_lses[c].value for c in ti.type}

class LayerStackPainter(Qt.QWidget):
    PAINTER_ITEM_TYPE = LayerStackPainterItem

    def __init__(self, layer_stack_item, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Layer Painter')
        self.painter_item = self.PAINTER_ITEM_TYPE(layer_stack_item)
        self.layer_stack = layer_stack_item.layer_stack
        widget_layout = Qt.QVBoxLayout()
        self.setLayout(widget_layout)
        section_layout = Qt.QGridLayout()
        widget_layout.addLayout(section_layout)
        self.brush_size_lse = LabelSliderEdit(section_layout, 'Brush size:', int, 0, 101, odd_values_only=True, max_is_hard=False)
        self.brush_size_lse.value = 5
        self.painter_item.target_image_changed.connect(self._on_target_image_changed)
        self.brush_box = BrushBox(self.brush_size_lse, 'Right click brush', 'brush', self.painter_item, False)
        widget_layout.addWidget(self.brush_box)
        self.alternate_brush_box = BrushBox(self.brush_size_lse, 'Shift right click brush', 'alternate_brush', self.painter_item, True)
        widget_layout.addWidget(self.alternate_brush_box)
        widget_layout.addStretch()

    def _on_target_image_changed(self):
        e = self.painter_item.target_image is not None
        bse = self.brush_size_lse
        bse.label.setEnabled(e)
        bse.slider.setEnabled(e)
        bse.editbox.setEnabled(e)