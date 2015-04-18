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

from ._qt_debug import qtransform_to_numpy
from .image import Image
from .shared_resources import GL, UNIQUE_QGRAPHICSITEM_TYPE
from .shader_scene import ShaderScene, ShaderItem, ShaderQOpenGLTexture
from .shader_view import ShaderView
from contextlib import ExitStack
import html
import math
import numpy
from PyQt5 import Qt
import sys

class ImageScene(ShaderScene):
    def __init__(self, parent):
        super().__init__(parent)
        self.image_item = ImageItem()
        self.addItem(self.image_item)
        self._histogram_scene = None

    def on_image_changing(self, image):
        self.image_item.on_image_changing(image)
        self.setSceneRect(self.image_item.boundingRect())
        for view in self.views():
            view.on_image_changing(image)

    def on_histogram_gamma_or_min_max_changed(self):
        self.image_item.update()

    @property
    def histogram_scene(self):
        return self._histogram_scene

    @histogram_scene.setter
    def histogram_scene(self, histogram_scene):
        if self._histogram_scene is not None:
            self._histogram_scene.gamma_or_min_max_changed.disconnect(self.on_histogram_gamma_or_min_max_changed)
        histogram_scene.gamma_or_min_max_changed.connect(self.on_histogram_gamma_or_min_max_changed)
        self._histogram_scene = histogram_scene
        self.on_histogram_gamma_or_min_max_changed()

class ImageItem(ShaderItem):
    QGRAPHICSITEM_TYPE = UNIQUE_QGRAPHICSITEM_TYPE()
    NUMPY_DTYPE_TO_QOGLTEX_PIXEL_TYPE = {
        numpy.uint8  : Qt.QOpenGLTexture.UInt8,
        numpy.uint16 : Qt.QOpenGLTexture.UInt16,
        numpy.float32: Qt.QOpenGLTexture.Float32}
    IMAGE_TYPE_TO_QOGLTEX_TEX_FORMAT = {
        'g'   : Qt.QOpenGLTexture.R32F,
        'ga'  : Qt.QOpenGLTexture.RG32F,
        'rgb' : Qt.QOpenGLTexture.RGB32F,
        'rgba': Qt.QOpenGLTexture.RGBA32F}
    IMAGE_TYPE_TO_QOGLTEX_SRC_PIX_FORMAT = {
        'g'   : Qt.QOpenGLTexture.Red,
        'ga'  : Qt.QOpenGLTexture.RG,
        'rgb' : Qt.QOpenGLTexture.RGB,
        'rgba': Qt.QOpenGLTexture.RGBA}
    IMAGE_TYPE_TO_COMBINE_VT_COMPONENTS = {
        'g'   : 'vec4(vcomponents, vcomponents, vcomponents, 1.0f)',
        'ga'  : 'vec4(vcomponents, vcomponents, vcomponents, tcomponents.a)',
        'rgb' : 'vec4(vcomponents.rgb, 1.0f)',
        'rgba': 'vec4(vcomponents.rgb, tcomponents.a)'}

    def __init__(self, parent_item=None):
        super().__init__(parent_item)
        self.tex = None
        self._show_frame = False
        self._overlay_items = []
        self._overlay_items_z_sort_is_current = True

    def type(self):
        return ImageItem.QGRAPHICSITEM_TYPE

    def boundingRect(self):
        return Qt.QRectF(0,0,1,1) if self.image is None else Qt.QRectF(Qt.QPointF(), Qt.QSizeF(self.image.size))

    def paint(self, qpainter, option, widget):
        if widget is None:
            print('WARNING: image_view.ImageItem.paint called with widget=None.  Ensure that view caching is disabled.')
        elif self.image is None:
            if self.tex is not None:
                self.tex.destroy()
                self.tex = None
        else:
            with ExitStack() as stack:
                qpainter.beginNativePainting()
                stack.callback(qpainter.endNativePainting)
                gl = GL()
                image = self.image
                if len(self._overlay_items) > 1:
                    raise RuntimeError('Only one overlay per ImageItem is supported at the moment.')
                if len(self._overlay_items) == 1 and self._overlay_items[0].isVisible():
                    overlay_item = self._overlay_items[0]
                    has_overlay = True
                    overlay_type = 'g' if overlay_item.overlay_image.is_grayscale else 'rgb'
                else:
                    overlay_item = None
                    has_overlay = False
                    overlay_type = None
                if (image.type, has_overlay) in self.progs:
                    prog = self.progs[(image.type, overlay_type)]
                else:
                    if image.is_grayscale:
                        vcomponents_t = 'float'
                        extract_vcomponents = 'tcomponents.r'
                        vcomponents_ones_vector = '1.0f'
                    else:
                        vcomponents_t = 'vec3'
                        extract_vcomponents = 'tcomponents.rgb'
                        vcomponents_ones_vector = 'vec3(1.0f, 1.0f, 1.0f)'
                    if has_overlay:
                        overlay_samplers = 'uniform sampler2D overlay0_tex;'
                        overlay_frag_to_texs = 'uniform mat3 overlay0_frag_to_tex;'
                        do_overlay_blending = \
"""
    vec2 overlay0_tex_coord = transform_frag_to_tex(overlay0_frag_to_tex);
    if(overlay0_tex_coord.x >= 0 && overlay0_tex_coord.x < 1 && overlay0_tex_coord.y >= 0 && overlay0_tex_coord.y < 1)
    {
        vec4 o = texture2D(overlay0_tex, overlay0_tex_coord);""" + ('\nfloat oc = 1.0f - o.r;' if overlay_item.overlay_image.is_grayscale else '\nvec3 oc = 1.0f - o.rgb;') + """
        vec3 tc = 1.0f - t_transformed.rgb;
        tc *= oc;
        tc = 1.0f - tc;//vec3(1.0f - tc.r, 1.0f - tc.g, 1.0f - tc.b);
        tc = clamp(tc, 0, 1);
        t_transformed.rgb = tc;
    }
"""
                        gl_FragColor = 't_transformed'
                    else:
                        overlay_samplers = ''
                        overlay_frag_to_texs = ''
                        do_overlay_blending = ''
                        gl_FragColor = 't_transformed'
                    prog = self.build_shader_prog((image.type, overlay_type),
                                                  'image_widget_vertex_shader.glsl',
                                                  'image_widget_fragment_shader_template.glsl',
                                                  vcomponents_t=vcomponents_t,
                                                  extract_vcomponents=extract_vcomponents,
                                                  vcomponents_ones_vector=vcomponents_ones_vector,
                                                  combine_vt_components=ImageItem.IMAGE_TYPE_TO_COMBINE_VT_COMPONENTS[image.type],
                                                  overlay_samplers=overlay_samplers,
                                                  overlay_frag_to_texs=overlay_frag_to_texs,
                                                  do_overlay_blending=do_overlay_blending,
                                                  gl_FragColor=gl_FragColor)
                prog.bind()
                stack.callback(prog.release)
                desired_texture_format = ImageItem.IMAGE_TYPE_TO_QOGLTEX_TEX_FORMAT[image.type]
                tex = self.tex
                if tex is not None:
                    if image.size != Qt.QSize(tex.width(), tex.height()) or tex.format() != desired_texture_format:
                        tex.destroy()
                        tex = self.tex = None
                if tex is None:
                    tex = ShaderQOpenGLTexture(Qt.QOpenGLTexture.Target2D)
                    tex.setFormat(desired_texture_format)
                    tex.setWrapMode(Qt.QOpenGLTexture.ClampToEdge)
                    tex.setMipLevels(1)
                    tex.setAutoMipMapGenerationEnabled(False)
                    tex.setSize(image.size.width(), image.size.height(), 1)
                    tex.allocateStorage()
                    tex.setMinMagFilters(Qt.QOpenGLTexture.Linear, Qt.QOpenGLTexture.Nearest)
                    tex.image_id = -1
                tex.bind()
                stack.callback(tex.release)
                if tex.image_id != self._image_id:
#                   import time
#                   t0=time.time()
                    pixel_transfer_opts = Qt.QOpenGLPixelTransferOptions()
                    pixel_transfer_opts.setAlignment(1)
                    tex.setData(ImageItem.IMAGE_TYPE_TO_QOGLTEX_SRC_PIX_FORMAT[image.type],
                                ImageItem.NUMPY_DTYPE_TO_QOGLTEX_PIXEL_TYPE[image.dtype],
                                image.data.ctypes.data,
                                pixel_transfer_opts)
#                   t1=time.time()
#                   print('tex.setData {}ms / {}fps'.format(1000*(t1-t0), 1/(t1-t0)))
                    tex.image_id = self._image_id
                    # self.tex is updated here and not before so that any failure preparing tex results in a retry the next time self.tex
                    # is needed
                    self.tex = tex
                view = widget.view
                view.quad_buffer.bind()
                stack.callback(view.quad_buffer.release)
                view.quad_vao.bind()
                stack.callback(view.quad_vao.release)
                vert_coord_loc = prog.attributeLocation('vert_coord')
                prog.enableAttributeArray(vert_coord_loc)
                prog.setAttributeBuffer(vert_coord_loc, gl.GL_FLOAT, 0, 2, 0)
                prog.setUniformValue('tex', 0)
                frag_to_tex = Qt.QTransform()
                frame = Qt.QPolygonF(view.mapFromScene(self.boundingRect()))
                if not qpainter.transform().quadToSquare(frame, frag_to_tex):
                    raise RuntimeError('Failed to compute gl_FragCoord to texture coordinate transformation matrix.')
                prog.setUniformValue('frag_to_tex', frag_to_tex)
                prog.setUniformValue('viewport_height', float(widget.size().height()))
                histogram_scene = view.scene().histogram_scene

#               print('qpainter.transform():', qtransform_to_numpy(qpainter.transform()))
#               print('self.deviceTransform(view.viewportTransform()):', qtransform_to_numpy(self.deviceTransform(view.viewportTransform())))

                if image.is_grayscale:
                    gamma = histogram_scene.gamma
                    min_max = numpy.array((histogram_scene.min, histogram_scene.max), dtype=float)
                    if image.dtype != numpy.float32:
                        self._normalize_min_max(min_max)
                    prog.setUniformValue('gammas', gamma)
                    prog.setUniformValue('vcomponent_rescale_mins', min_max[0])
                    prog.setUniformValue('vcomponent_rescale_ranges', min_max[1] - min_max[0])
                else:
                    gammas = (histogram_scene.gamma_red, histogram_scene.gamma_green, histogram_scene.gamma_blue)
                    min_maxs = numpy.array(((histogram_scene.min_red, histogram_scene.min_green, histogram_scene.min_blue),
                                            (histogram_scene.max_red, histogram_scene.max_green, histogram_scene.max_blue)), dtype=float)
                    prog.setUniformValue('gammas', *gammas)
                    if image.dtype != numpy.float32:
                        self._normalize_min_max(min_maxs)
                    prog.setUniformValue('vcomponent_rescale_mins', *min_maxs[0])
                    prog.setUniformValue('vcomponent_rescale_ranges', *(min_maxs[1]-min_maxs[0]))
                if has_overlay:
                    overlay_item.update_tex()
                    overlay_item.tex.bind(1)
                    stack.callback(lambda: overlay_item.tex.release(1))
                    overlay_frag_to_tex = Qt.QTransform()
                    overlay_frame = Qt.QPolygonF(view.mapFromScene(overlay_item.boundingRect()))
                    overlay_qpainter_transform = overlay_item.deviceTransform(view.viewportTransform())
                    if not overlay_qpainter_transform.quadToSquare(overlay_frame, overlay_frag_to_tex):
                        raise RuntimeError('Failed to compute gl_FragCoord to texture coordinate transformation matrix for overlay.')
#                   overlay_frag_to_tex.scale(0.5, 2)
                    prog.setUniformValue('overlay0_frag_to_tex', overlay_frag_to_tex)
                    prog.setUniformValue('overlay0_tex', 1)
                gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
                gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)
            if self._show_frame:
                qpainter.setBrush(Qt.QBrush(Qt.Qt.transparent))
                color = Qt.QColor(Qt.Qt.red)
                color.setAlphaF(0.5)
                pen = Qt.QPen(color)
                pen.setWidth(2)
                pen.setCosmetic(True)
                pen.setStyle(Qt.Qt.DotLine)
                qpainter.setPen(pen)
                qpainter.drawRect(0, 0, image.size.width(), image.size.height())

    def hoverMoveEvent(self, event):
        if self.image is not None:
            # NB: event.pos() is a QPointF, and one may call QPointF.toPoint(), as in the following line,
            # to get a QPoint from it.  However, toPoint() rounds x and y coordinates to the nearest int,
            # which would cause us to erroneously report mouse position as being over the pixel to the
            # right and/or below if the view with the mouse cursor is zoomed in such that an image pixel
            # occupies more than one screen pixel and the cursor is over the right and/or bottom half
            # of a pixel.
#           pos = event.pos().toPoint()
            pos = Qt.QPoint(event.pos().x(), event.pos().y())
            cis = []
            ci = self.generate_contextual_info_for_pos(pos)
            if ci is not None:
                cis.append(ci)
            self.update_overlay_items_z_sort()
            for overlay_stack_idx, overlay_item in enumerate(self._overlay_items):
                if overlay_item.isVisible():
                    # For a number of potential reasons including overlay rotation, differing resolution
                    # or scale, and fractional offset relative to parent, it is necessary to project floating
                    # point coordinates and not integer coordinates into overlay item space in order to
                    # accurately determine which overlay image pixel contains the mouse pointer
                    o_pos = self.mapToItem(overlay_item, event.pos())
                    if overlay_item.boundingRect().contains(o_pos):
                        ci = overlay_item.generate_contextual_info_for_pos(o_pos, overlay_stack_idx)
                        if ci is not None:
                            cis.append(ci)
            if cis:
                all_html = True
                any_html = False
                for string, is_html in cis:
                    if is_html:
                        any_html = True
                    else:
                        all_html = False
                    if any_html and not all_html:
                        # all_html and any_html values can not possibly change if we are here, so we can
                        # stop early
                        break
                if any_html and not all_html:
                    cis = (ci if ci[1] else (html.escape(ci[0]), True) for ci in cis)
                    all_html = True
                if all_html:
                    self.scene().update_contextual_info('<br>'.join((ci[0] for ci in cis)), True, self)
                else:
                    self.scene().update_contextual_info('\n'.join((ci[0] for ci in cis)), False, self)

    def generate_contextual_info_for_pos(self, pos):
        if Qt.QRect(Qt.QPoint(), self.image.size).contains(pos):
            mst = 'x:{} y:{} '.format(pos.x(), pos.y())
            image_type = self.image.type
            vt = '(' + ' '.join((c + ':{}' for c in image_type)) + ')'
            if len(image_type) == 1:
                vt = vt.format(self.image.data[pos.x(), pos.y()])
            else:
                vt = vt.format(*self.image.data[pos.x(), pos.y()])
            return mst+vt, False

    def hoverLeaveEvent(self, event):
        self.scene().clear_contextual_info(self)

    def on_image_changing(self, image):
        if self.image is None and image is not None or \
           self.image is not None and (image is None or self.image.size != image.size):
            self.prepareGeometryChange()
        super().on_image_changing(image)

    def attach_overlay(self, overlay_item):
        assert overlay_item not in self._overlay_items
        if not isinstance(overlay_item, ImageOverlayItem):
            raise ValueError('overlay_item argument must be or must be derived from ris_widget.image_scene.ImageOverlayItem.')
        if overlay_item.parentItem() is not self:
            raise RuntimeError('ImageItem must be parent of overlay_item to be attached.')
        self._overlay_items.append(overlay_item)
        self._overlay_items_z_sort_is_current = False
        self.update()

    def detach_overlay(self, overlay_item):
        idx = self._overlay_items.index(overlay_item)
        del self._overlay_items[idx]
        self.update()

    def update_overlay_items_z_sort(self):
        if not self._overlay_items_z_sort_is_current:
            self._overlay_items.sort(key=lambda i: i.zValue())
            self._overlay_items_z_sort_is_current = True

    @property
    def show_frame(self):
        return self._show_frame

    @show_frame.setter
    def show_frame(self, show_frame):
        if show_frame != self.show_frame:
            self._show_frame = show_frame
            self.update()

class ImageOverlayItem(Qt.QGraphicsObject):
    QGRAPHICSITEM_TYPE = UNIQUE_QGRAPHICSITEM_TYPE()

    def __init__(self, overlayed_image_item, overlay_image=None, overlay_name=None):
        super().__init__(overlayed_image_item)
        self._show_frame = False
        self.overlay_image_id = 0
        self.tex = None
        self._overlay_image = None
        self.overlay_image = overlay_image
        self.setFlag(Qt.QGraphicsItem.ItemIgnoresParentOpacity)
        self.overlay_name = overlay_name
        if overlayed_image_item is not None:
            overlayed_image_item.attach_overlay(self)

    def type(self):
        return ImageOverlayItem.QGRAPHICSITEM_TYPE

    def boundingRect(self):
        return Qt.QRectF() if self._overlay_image is None else Qt.QRectF(Qt.QPointF(), Qt.QSizeF(self._overlay_image.size))

    def itemChange(self, change, value):
        if change == Qt.QGraphicsItem.ItemParentChange:
            parent = self.parentItem()
            if parent is not None:
                parent.detach_overlay(self)
            if self.tex is not None and self.tex.isCreated():
                scene = self.scene()
                if scene is not None:
                    views = scene.views()
                    if views:
                        views[0].makeCurrent()
                        try:
                            self.tex.destroy()
                        finally:
                            views[0].doneCurrent()
        elif change == Qt.QGraphicsItem.ItemParentHasChanged:
            parent = value
            if parent is not None:
                parent.attach_overlay(self)
        # Omitting the following line results in numerous subtle misbehaviors such as being unable to make this item visible
        # after hiding it.  This is a result of the return value from itemChange sometimes mattering: certain item changes
        # may be cancelled or modified by returning something other than the value argument.  In the case of
        # Qt.QGraphicsItem.ItemVisibleChange, returning something that casts to False overrides a visibility -> True state
        # change, causing the item to remain hidden.
        return value

    def paint(self, qpainter, option, widget):
        """This QGraphicsItem (from which QGraphicsObject is derived, from which this class, in turn, is derived) is primarily
        drawn by its parent, an ImageItem, in order that it may be composited with that ImageItem in more advanced ways than
        supported by QPainter when rendering to an OpenGL context (QPainter in software mode supports a galaxy of various blend
        modes, but QPainter in software mode is far too slow for our purposes, namely, drawing full screen images transformed
        in real time - not unlike AGG, which would also be too slow.  Use matplotlib.pyplot.imshow to see how slow is slow).
        
        The only drawing that ImageOverlayItem actually does in its own right is to paint a stippled border two pixels wide,
        with one pixel inside and one pixel outside, and it only does this if the show_frame attribute has been set to True
        or something that evaluated to True when coerced to bool."""
        if self._show_frame and self.overlay_image is not None and (self.parentItem() is None or self.parentItem().image is not None):
            qpainter.setBrush(Qt.QBrush(Qt.Qt.transparent))
            color = Qt.QColor(Qt.Qt.blue)
            color.setAlphaF(0.5)
            pen = Qt.QPen(color)
            pen.setWidth(2)
            pen.setCosmetic(True)
            pen.setStyle(Qt.Qt.DotLine)
            qpainter.setPen(pen)
            qpainter.drawRect(self.boundingRect())

    def update_tex(self):
        """This function is intended to be called from ImageItem's paint function and relies upon an OpenGL context being
        current (eg, via QOpenGLWidget.setCurrent, QOpenGLContext.setCurrent, QPainter.beginNativePainting, glXMakeCurrent
        C call on *nix, WglMakeCurrent C call on win32, [NSOpenGLContext makeCurrent] obj-C method on Darwin, or any other
        equivalent)."""
        if self._overlay_image is None:
            if self.tex is not None:
                self.tex.destroy()
                self.tex = None
        else:
            oimage = self._overlay_image
            tex = self.tex
            desired_texture_format = ImageItem.IMAGE_TYPE_TO_QOGLTEX_TEX_FORMAT[oimage.type]
            if tex is not None:
                if oimage.size != Qt.QSize(tex.width(), tex.height()) or tex.format() != desired_texture_format:
                    tex.destroy()
                    tex = self.tex = None
            if tex is None:
                tex = Qt.QOpenGLTexture(Qt.QOpenGLTexture.Target2D)
                tex.setFormat(desired_texture_format)
                tex.setWrapMode(Qt.QOpenGLTexture.ClampToEdge)
                tex.setMipLevels(6)
                tex.setAutoMipMapGenerationEnabled(True)
                tex.setSize(oimage.size.width(), oimage.size.height(), 1)
                tex.allocateStorage()
                # Overylay display should be as accurate as reasonably possible.  Trilinear filtering for normal
                # images is not reasonably possible - the required mipmap computation is too slow for live mode
                # viewing of 2560x2160 16bpp grayscale images.  Trilinear filtering for overlay images, however,
                # is fine so long as the overlay is not updated with every 2560x2160 16bpp image, which is not
                # expected to occur for live streams.
                tex.setMinMagFilters(Qt.QOpenGLTexture.LinearMipMapLinear, Qt.QOpenGLTexture.Nearest)
                tex.overlay_image_id = -1
            if tex.overlay_image_id != self.overlay_image_id:
                with ExitStack() as stack:
                    tex.bind()
                    stack.callback(lambda: tex.release(0))
                    pixel_transfer_opts = Qt.QOpenGLPixelTransferOptions()
                    pixel_transfer_opts.setAlignment(1)
                    tex.setData(ImageItem.IMAGE_TYPE_TO_QOGLTEX_SRC_PIX_FORMAT[oimage.type],
                                ImageItem.NUMPY_DTYPE_TO_QOGLTEX_PIXEL_TYPE[oimage.dtype],
                                oimage.data.ctypes.data,
                                pixel_transfer_opts)
                    tex.overlay_image_id = self.overlay_image_id
                    # self.tex is updated here and not before so that any failure preparing tex results in a retry the next time self.tex
                    # is needed
                    self.tex = tex

    def generate_contextual_info_for_pos(self, pos, overlay_stack_idx):
        pos = Qt.QPoint(pos.x(), pos.y())
        oimage = self._overlay_image
        if Qt.QRect(Qt.QPoint(), oimage.size).contains(pos):
            mst = 'overlay {}: '.format(overlay_stack_idx) if self.overlay_name is None else (self.overlay_name + ': ')
            mst+= 'x:{} y:{} '.format(pos.x(), pos.y())
            oimage_type = oimage.type
            vt = '(' + ' '.join((c + ':{}' for c in oimage_type)) + ')'
            if len(oimage_type) == 1:
                vt = vt.format(oimage.data[pos.x(), pos.y()])
            else:
                vt = vt.format(*oimage.data[pos.x(), pos.y()])
            return mst+vt, False

    @property
    def overlay_image(self):
        return self._overlay_image

    @overlay_image.setter
    def overlay_image(self, overlay_image):
        if overlay_image is self._overlay_image:
            if overlay_image is not None:
                self.overlay_image_id += 1
                self.parentItem().update()
        else:
            if self._overlay_image is None and overlay_image is not None or \
               self._overlay_image is not None and (overlay_image is None or self._overlay_image.size != overlay_image.size):
                self.prepareGeometryChange()
            if overlay_image is None or issubclass(type(overlay_image), Image):
                self._overlay_image = overlay_image
            else:
                self._overlay_image = Image(overlay_image)
            self.parentItem().update()

    @property
    def show_frame(self):
        return self._show_frame

    @show_frame.setter
    def show_frame(self, show_frame):
        if show_frame != self.show_frame:
            self._show_frame = show_frame
            self.update()
