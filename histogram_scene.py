# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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

from contextlib import ExitStack
from .gl_resources import GL
import math
import numpy
from PyQt5 import Qt
from .shader_scene import ShaderItem, ShaderScene, ShaderTexture
import sys

class ItemProp:
    def __init__(self, item_props, name, name_in_label=None, channel_name=None):
        self.name = name
        self.full_name = name
        if channel_name is not None:
            self.full_name += '_' + channel_name
        item_props[self.full_name] = self
        self.scene_items = {}

    def instantiate(self, histogram_scene):
        scene_item = self._make_scene_item(histogram_scene)
        self.scene_items[histogram_scene] = scene_item
        scene_item.value_changed.connect(histogram_scene.gamma_or_min_max_changed)

    def _make_scene_item(self, histogram_scene):
        raise NotImplementedError()

    def __get__(self, histogram_scene, objtype=None):
        if histogram_scene is None:
            return self
        return self.scene_items[histogram_scene].value

    def __set__(self, histogram_scene, value):
        if histogram_scene is None:
            raise AttributeError("Can't set instance attribute of class.")
        self.scene_items[histogram_scene].value = value

class MinMaxItemProp(ItemProp):
    def __init__(self, item_props, min_max_item_props, name, name_in_label=None, channel_name=None):
        super().__init__(item_props, name, name_in_label, channel_name)
        min_max_item_props[self.full_name] = self

    def _make_scene_item(self, histogram_scene):
        return MinMaxItem(histogram_scene.histogram_item, self.full_name)

    def propagate_scene_item_value(self, histogram_scene):
        pass

#class GammaItemProp(ItemProp):

class HistogramScene(ShaderScene):
    gamma_or_min_max_changed = Qt.pyqtSignal()

    item_props = {}
    min_max_item_props = {}
    gamma_item_props = {}

    max = MinMaxItemProp(item_props, min_max_item_props, 'max')
    min = MinMaxItemProp(item_props, min_max_item_props, 'min')
#   gamma = GammaItemProp(item_props, gamma_item_props, 'gamma', '\u03b3')

    def __init__(self, parent):
        super().__init__(parent)
        self.setSceneRect(0, 0, 1, 1)
        self.histogram_item = HistogramItem()
        self.addItem(self.histogram_item)
        for item_prop in self.item_props.values():
            item_prop.instantiate(self)
        self.gamma_gamma = 1.0
        self.gamma = 1.0
        self.rescale_enabled = True
        self.min = 0
        self.max = 1
#       self.gamma = 1
        self._channel_controls_visible = False

#       self._allow_inversion = True # Set to True during initialization for convenience...
#       for scalar_prop in HistogramView._scalar_props:
#           scalar_prop.instantiate(self, layout)
#       self._allow_inversion = False # ... and, enough stuff has been initialized that this can now be set to False without trouble

    def on_image_changing(self, image):
        self.histogram_item.on_image_changing(image)

    def get_prop_item(self, full_name):
        return self.item_props[full_name].scene_items[self]

class HistogramItem(ShaderItem):
    def __init__(self, graphics_item_parent=None):
        super().__init__(graphics_item_parent)
        self.image = None
        self._image_id = 0
        self._bounding_rect = Qt.QRectF(0, 0, 1, 1)

    def boundingRect(self):
        return self._bounding_rect

    def paint(self, qpainter, option, widget):
        if widget is None:
            print('WARNING: histogram_view.HistogramItem.paint called with widget=None.  Ensure that view caching is disabled.')
        elif self.image is None:
            if widget.view in self.view_resources:
                self._del_tex()
        else:
            image = self.image
            view = widget.view
            scene = self.scene()
            gl = GL()
            with ExitStack() as stack:
                qpainter.beginNativePainting()
                stack.callback(qpainter.endNativePainting)
                if view in self.view_resources:
                    vrs = self.view_resources[view]
                else:
                    self.view_resources[view] = vrs = {}
                    self.build_shader_prog('g',
                                            'histogram_widget_vertex_shader.glsl',
                                            'histogram_widget_fragment_shader_g.glsl',
                                            view)
                    vrs['progs']['ga'] = vrs['progs']['g']
                    self.build_shader_prog('rgb',
                                            'histogram_widget_vertex_shader.glsl',
                                            'histogram_widget_fragment_shader_rgb.glsl',
                                            view)
                    vrs['progs']['rgba'] = vrs['progs']['rgb']
                desired_tex_width = image.histogram.shape[-1]
                if 'tex' in vrs:
                    tex = vrs['tex']
                    if tex.width != desired_tex_width:
                        tex.destroy()
                        del vrs['tex']
                if 'tex' not in vrs:
                    tex = ShaderTexture(gl.GL_TEXTURE_1D)
                    tex.bind()
                    stack.callback(tex.release)
                    gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
                    gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                    # tex stores histogram bin counts - values that are intended to be addressed by element without
                    # interpolation.  Thus, nearest neighbor for texture filtering.
                    gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
                    gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
                    tex.image_id = -1
                    vrs['tex'] = tex
                else:
                    tex.bind()
                    stack.callback(tex.release)
                if image.is_grayscale:
                    if image.type == 'g':
                        histogram = image.histogram
                        max_bin_val = histogram[image.max_histogram_bin]
                    else:
                        histogram = image.histogram[0]
                        max_bin_val = histogram[image.max_histogram_bin[0]]
                    if tex.image_id != self._image_id:
                        orig_unpack_alignment = gl.glGetIntegerv(gl.GL_UNPACK_ALIGNMENT)
                        if orig_unpack_alignment != 1:
                            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
                            # QPainter font rendering for OpenGL surfaces will become broken if we do not restore GL_UNPACK_ALIGNMENT
                            # to whatever QPainter had it set to (when it prepared the OpenGL context for our use as a result of
                            # qpainter.beginNativePainting()).
                            stack.callback(lambda oua=orig_unpack_alignment: gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, oua))
                        gl.glTexImage1D(gl.GL_TEXTURE_1D, 0,
                                        gl.GL_LUMINANCE32UI_EXT, desired_tex_width, 0,
                                        gl.GL_LUMINANCE_INTEGER_EXT, gl.GL_UNSIGNED_INT,
                                        histogram.data)
                        tex.image_id = self._image_id
                        tex.width = desired_tex_width
                    view.quad_buffer.bind()
                    stack.callback(view.quad_buffer.release)
                    view.quad_vao.bind()
                    stack.callback(view.quad_vao.release)
                    prog = vrs['progs'][image.type]
                    prog.bind()
                    stack.callback(prog.release)
                    vert_coord_loc = prog.attributeLocation('vert_coord')
                    prog.enableAttributeArray(vert_coord_loc)
                    prog.setAttributeBuffer(vert_coord_loc, gl.GL_FLOAT, 0, 2, 0)
                    prog.setUniformValue('tex', 0)
                    prog.setUniformValue('inv_view_size', 1/widget.size().width(), 1/widget.size().height())
                    inv_max_transformed_bin_val = max_bin_val**-scene.gamma_gamma
                    prog.setUniformValue('inv_max_transformed_bin_val', inv_max_transformed_bin_val)
                    prog.setUniformValue('gamma_gamma', scene.gamma_gamma)
                    prog.setUniformValue('rescale_enabled', scene.rescale_enabled)
                    if scene.rescale_enabled:
                        prog.setUniformValue('gamma', scene.gamma)
                        min_max = numpy.array((scene.min, scene.max), dtype=float)
                        self._normalize_min_max(min_max)
                        prog.setUniformValue('intensity_rescale_min', min_max[0])
                        prog.setUniformValue('intensity_rescale_range', min_max[1] - min_max[0])
                    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
                    gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)
                else:
                    pass
                    # personal time todo: per-channel RGB histogram support

    def hoverMoveEvent(self, event):
        image = self.image
        if image is not None:
            x = event.pos().x()
            if x >= 0 and x <= 1:
                if image.is_grayscale:
                    image_type = image.type
                    histogram = image.histogram
                    range_ = image.range
                    bin_count = histogram.shape[-1]
                    bin = int(x * (bin_count - 1))
                    bin_width = (range_[1] - range_[0]) / bin_count
                    if image.dtype == numpy.float32:
                        mst = '[{},{}) '.format(bin*bin_width, (bin+1)*bin_width)
                    else:
                        mst = '[{},{}] '.format(math.ceil(bin*bin_width), math.floor((bin+1)*bin_width))
                    vt = '(' + ' '.join((c + ':{}' for c in image_type)) + ')'
                    if len(image_type) == 1:
                        vt = vt.format(histogram[bin])
                    else:
                        vt = vt.format(*histogram[:,bin])
                    self.scene().update_mouseover_info(mst + vt, False, self)
                else:
                    pass
                    # personal time todo: per-channel RGB histogram support

    def on_image_changing(self, image):
        if (self.image is None) != (image is not None) or \
           self.image is not None and image is not None and self.image.histogram.shape[-1] != image.histogram.shape[-1]:
            self.prepareGeometryChange()
        super().on_image_changing(image)

class ControlItem(Qt.QGraphicsObject):
    value_changed = Qt.pyqtSignal(HistogramScene, float)

class MinMaxItem(ControlItem):
    def __init__(self, histogram_item, prop_full_name):
        super().__init__(histogram_item)
        self.prop_full_name = prop_full_name
        self._bounding_rect = Qt.QRectF(-0.1, 0, .2, 1)
        self._ignore_x_change = False
        self.xChanged.connect(self.on_x_changed)
        self.yChanged.connect(self.on_y_changed)
        self.setFlag(Qt.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(Qt.QGraphicsItem.ItemIsSelectable, True)

    def on_x_changed(self):
        if not self._ignore_x_change:
            x = self.x()
            if x < 0:
                self.setX(0)
            elif x > 1:
                self.setX(1)
            else:
                self.scene().update_mouseover_info('{}: {}'.format(self.prop_full_name, self.value), False, self)
                self.value_changed.emit(self.scene(), self.x_to_value(x))

    def on_y_changed(self):
        if self.y() != 0:
            self.setY(0)

    def boundingRect(self):
        return self._bounding_rect

    def paint(self, qpainter, option, widget):
        c = Qt.QColor(Qt.Qt.red)
        c.setAlphaF(0.5)
        pen = Qt.QPen(c)
        pen.setWidth(0)
        qpainter.setPen(pen)
        br = self.boundingRect()
        x = (br.left() + br.right()) / 2
        qpainter.drawLine(x, br.top(), x, br.bottom())

    @property
    def x_to_value(self):
        offset = 0; range_width = 1; is_fp = True
        scene = self.scene()
        if scene is not None:
            image = scene.histogram_item.image
            if image is not None:
                is_fp = image.dtype == numpy.float32
                range_ = image.range
                offset = range_[0]
                range_width = range_[1] - range_[0]
        if is_fp:
            def _x_to_value(x):
                return x * range_width + offset
        else:
            def _x_to_value(x):
                return int(x * range_width + offset)
        return _x_to_value

    @property
    def value_to_x(self):
        offset = 0; range_width = 1
        scene = self.scene()
        if scene is not None:
            image = scene.histogram_item.image
            if image is not None:
                range_ = image.range
                offset = range_[0]
                range_width = range_[1] - range_[0]
        def _value_to_x(value):
            return (value - offset) / range_width
        return _value_to_x

    @property
    def value(self):
        return self.x_to_value(self.x())

    @value.setter
    def value(self, value):
        value_to_x = self.value_to_x
        x = value_to_x(value)
        if x < 0 or x > 1:
            x_to_value = self.x_to_value
            raise ValueError('MinMaxItem.value must be in the range [{}, {}].'.format(x_to_value(0), x_to_value(1)))
        if x != self.x():
            self._ignore_x_change = True
            try:
                self.setX(x)
            finally:
                self._ignore_x_change = False
            self.value_changed.emit(self.scene(), value)

class GammaItem(ControlItem):
    def __init__(self, histogram_item):
        super().__init__(histogram_item)