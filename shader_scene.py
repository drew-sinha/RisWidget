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

from pathlib import Path
from PyQt5 import Qt

class ShaderScene(Qt.QGraphicsScene):
    # The update_mouseover_info signal serves to relay mouseover info text change requests
    # from any items in the ShaderScene to every attached Viewport's ViewportOverlayScene's
    # MouseoverTextItem (which is part of ViewportOverlayScene so that the text is view-relative
    # rather than scaling with the shader item).
    update_mouseover_info = Qt.pyqtSignal(str)

class ShaderItem(Qt.QGraphicsItem):
    def __init__(self, parent_item=None):
        super().__init__(parent_item)
        self.view_resources = {}
        self._image = None
        self._image_id = 0

    def build_shader_prog(self, desc, vert_fn, frag_fn, shader_view):
        source_dpath = Path(__file__).parent / 'shaders'
        prog = Qt.QOpenGLShaderProgram(shader_view)
        if not prog.addShaderFromSourceFile(Qt.QOpenGLShader.Vertex, str(source_dpath / vert_fn)):
            raise RuntimeError('Failed to compile vertex shader "{}" for {} {} shader program.'.format(vert_fn, type(self).__name__, desc))
        if not prog.addShaderFromSourceFile(Qt.QOpenGLShader.Fragment, str(source_dpath / frag_fn)):
            raise RuntimeError('Failed to compile fragment shader "{}" for {} {} shader program.'.format(frag_fn, type(self).__name__, desc))
        if not prog.link():
            raise RuntimeError('Failed to link {} {} shader program.'.format(type(self).__name__, desc))
        vrs = self.view_resources[shader_view]
        if 'progs' not in vrs:
            vrs['progs'] = {desc : prog}
        else:
            vrs['progs'][desc] = prog

    def free_shader_view_resources(self, shader_view):
        for item in self.childItems():
            if issubclass(type(item), ShaderItem):
                item.free_shader_view_resources(shader_view)
        if shader_view in self.view_resources:
            vrs = self.view_resources[shader_view]
            if 'progs' in vrs:
                for prog in vrs['progs'].values():
                    prog.removeAllShaders()
            del self.view_resources[shader_view]

    def on_image_changing(self, image):
        self._image = image
        self._image_id += 1
        self.update()

    def _normalize_min_max(self, min_max):
        r = self._image.range
        min_max -= r[0]
        min_max /= r[1] - r[0]
