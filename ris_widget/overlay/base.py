# This code is licensed under the MIT License (see LICENSE file for details)

from PyQt5 import Qt

from .. import shared_resources

class RWGeometryItemMixin:
    def __init__(self, ris_widget, pen=None, geometry=None):
        """Class for drawing a geometry on a ris_widget.

        To remove from the ris_widget, call remove().

        Subclasses must implement a geometry property that calls _geometry_changed(),
        which takes care of calling geometry-changed callbacks.

        Parameters:
            ris_widget: a ris_widget instance to draw geometry on
            pen: a QPen with which to draw the geometry
            geometry: interpreted by subclasses for drawing the overlay

        Class variables:
            geometry_change_callbacks: list of callbacks that will be called
                when geometry is changed, with the new geometry as the parameter
                or None if the geometry is deleted. NB: a callback is *not* called
                when the geometry is set directly via the .geometry attribute.
                The callback is only called when the geometry changes from the
                GUI.
        """
        layer_stack = ris_widget.image_scene.layer_stack_item
        super().__init__(layer_stack)
        if pen is None:
            pen = Qt.QPen(Qt.Qt.green)
            pen.setWidth(2)
        self.display_pen = Qt.QPen(pen)
        self.display_pen.setCosmetic(True)
        self.selected_pen = Qt.QPen(self.display_pen)
        self.selected_pen.setColor(Qt.Qt.red)
        self.ris_widget = ris_widget
        self.setPen(self.display_pen)
        self.geometry_change_callbacks = []
        self._mouse_connected = False
        layer_stack.installSceneEventFilter(self)
        self.geometry = geometry

    # all subclasses must define their own unique QGRAPHICSITEM_TYPE
    QGRAPHICSITEM_TYPE = shared_resources.generate_unique_qgraphicsitem_type()
    def type(self):
        return self.QGRAPHICSITEM_TYPE

    def _geometry_changed(self):
        # subclass MUST call after changing geometry from  GUI. Subclass
        # MUST NOT call in response to changing geometry from setter.
        for callback in self.geometry_change_callbacks:
            callback(self.geometry)

    def remove(self):
        self.parentItem().removeSceneEventFilter(self)
        if self._mouse_connected:
            self.ris_widget.image_view.mouse_release.disconnect(self._view_mouse_release)
        self.ris_widget.image_scene.removeItem(self)
        del self.ris_widget

    def shape(self):
        # make the shape larger than the visible lines to make it easier to click on
        s = Qt.QPainterPathStroker()
        s.setWidth(12/self.scene().views()[0].zoom)
        return s.createStroke(super().shape())

    def boundingRect(self):
        # need to return a bounding rect around the enlarged shape
        return self.shape().boundingRect()

    def paint(self, painter, option, widget):
        option = Qt.QStyleOptionGraphicsItem(option)
        option.state &= ~Qt.QStyle.State_Selected
        super().paint(painter, option, widget)

    def _view_mouse_release(self, pos, modifiers):
        # Called when ROI item is visible, and a mouse-up on the underlying
        # view occurs. (I.e. not on this item itself)
        pass

    def itemChange(self, change, value):
        if change == Qt.QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self._selected()
            else:
                self._deselected()
        elif change == Qt.QGraphicsItem.ItemVisibleHasChanged:
            if value:
                # Usually when the item is constructed we get a "made visible" event first thing,
                # so this is where we'll connect the mouse function.
                self.ris_widget.image_view.mouse_release.connect(self._view_mouse_release)
                self._mouse_connected = True
            elif self._mouse_connected:
                # if the item is constructed and immediately hidden, a visibility change
                # to invisible will be the first change! So there will be no
                # connection made and the disconnect below will be an error unless
                # we make sure only to disconnect after a connect has occured
                self.ris_widget.image_view.mouse_release.disconnect(self._view_mouse_release)
                self._mouse_connected = False
        return value

    def _selected(self):
        self.setPen(self.selected_pen)

    def _deselected(self):
        self.setPen(self.display_pen)

    def sceneEventFilter(self, watched, event):
        if (event.type() == Qt.QEvent.KeyPress and self.isSelected()
              and event.key() in {Qt.Qt.Key_Delete, Qt.Qt.Key_Backspace}):
            self.geometry = None
            self._geometry_changed()
            return True
        return False


class SceneListener(Qt.QGraphicsItem):
    def __init__(self, ris_widget):
        super().__init__(ris_widget.image_scene.layer_stack_item)
        self.setFlag(Qt.QGraphicsItem.ItemHasNoContents)
        self.parentItem().installSceneEventFilter(self)

    QGRAPHICSITEM_TYPE = shared_resources.generate_unique_qgraphicsitem_type()
    def type(self):
        return self.QGRAPHICSITEM_TYPE

    def remove(self):
        self.parentItem().removeSceneEventFilter(self)

    def boundingRect(self):
        return Qt.QRectF()


class Handle(Qt.QGraphicsRectItem):
    RECT = (-3, -3, 6, 6)
    def __init__(self, parent, layer_stack, brush, pen=None):
        super().__init__(*self.RECT, parent=parent)
        self.layer_stack = layer_stack
        view = self.scene().views()[0]
        self._zoom_changed(view.zoom)
        view.zoom_changed.connect(self._zoom_changed)
        if pen is None:
            pen = Qt.Qt.NoPen
        self.setPen(Qt.QPen(pen))
        self.setBrush(Qt.QBrush(brush))
        self.setFlag(Qt.QGraphicsItem.ItemIsMovable)

    QGRAPHICSITEM_TYPE = shared_resources.generate_unique_qgraphicsitem_type()
    def type(self):
        return self.QGRAPHICSITEM_TYPE

    def remove(self):
        scene = self.scene()
        scene.views()[0].zoom_changed.disconnect(self._zoom_changed)
        scene.removeItem(self)

    def _zoom_changed(self, z):
        self.setScale(1/z)

    def shape(self):
        # make the shape larger than the visible rect to make it easier to click on
        path = Qt.QPainterPath()
        path.addRect(self.rect().adjusted(-4, -4, 4, 4))
        return path

    def boundingRect(self):
        # need to return a bounding rect around the enlarged shape
        return self.shape().boundingRect()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.layer_stack.contextual_info_pos = self.pos()
        self.layer_stack._update_contextual_info()


class SelectableHandle(Handle):
    QGRAPHICSITEM_TYPE = shared_resources.generate_unique_qgraphicsitem_type()

    def __init__(self, parent, layer_stack, brush, pen=None):
        super().__init__(parent, layer_stack, brush, pen)
        self.display_brush = self.brush() # set in superclass init
        self.selected_brush = Qt.QBrush(Qt.Qt.red)
        self.setFlag(Qt.QGraphicsItem.ItemIsSelectable)

    def itemChange(self, change, value):
        if change == Qt.QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self._selected()
            else:
                self._deselected()
        return value

    def paint(self, painter, option, widget):
        option = Qt.QStyleOptionGraphicsItem(option)
        option.state &= ~Qt.QStyle.State_Selected
        super().paint(painter, option, widget)

    def _selected(self):
        self.setBrush(self.selected_brush)

    def _deselected(self):
        self.setBrush(self.display_brush)
