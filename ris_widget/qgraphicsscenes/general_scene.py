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

from PyQt5 import Qt
from . import base_scene
from ..qgraphicsitems import layer_stack_item

class GeneralScene(base_scene.BaseScene):
    def __init__(self, parent, layer_stack):
        super().__init__(parent)
        self.layer_stack_item = layer_stack_item.LayerStackItem(layer_stack=layer_stack)
        self.layer_stack_item.bounding_rect_changed.connect(self._on_layer_stack_item_bounding_rect_changed)
        self.addItem(self.layer_stack_item)

    def _on_layer_stack_item_bounding_rect_changed(self):
        self.setSceneRect(self.layer_stack_item.boundingRect())
        for view in self.views():
            view._on_layer_stack_item_bounding_rect_changed()
