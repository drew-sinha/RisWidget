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
from ..image import Image
from ..layer import Layer
from ..layer_stack import LayerList
from ..qdelegates.dropdown_list_delegate import DropdownListDelegate
from ..qdelegates.slider_delegate import SliderDelegate
from ..qdelegates.color_delegate import ColorDelegate
from ..qdelegates.checkbox_delegate import CheckboxDelegate
from ..shared_resources import CHOICES_QITEMDATA_ROLE, FREEIMAGE
from .. import om

class LayerTableView(Qt.QTableView):
    def __init__(self, layer_table_model, parent=None):
        super().__init__(parent)
        self.layer_table_model = layer_table_model
        self.horizontalHeader().setSectionResizeMode(Qt.QHeaderView.Interactive)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsClickable(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setHighlightSections(False)
        self.verticalHeader().setSectionsClickable(False)
        self.setTextElideMode(Qt.Qt.ElideMiddle)
        self.checkbox_delegate = CheckboxDelegate(parent=self)
        self.setItemDelegateForColumn(layer_table_model.property_columns['visible'], self.checkbox_delegate)
        self.setItemDelegateForColumn(layer_table_model.property_columns['auto_min_max'], self.checkbox_delegate)
        self.blend_function_delegate = DropdownListDelegate(self)
        self.setItemDelegateForColumn(layer_table_model.property_columns['blend_function'], self.blend_function_delegate)
        self.tint_delegate = ColorDelegate(self)
        self.setItemDelegateForColumn(layer_table_model.property_columns['tint'], self.tint_delegate)
        self.opacity_delegate = SliderDelegate(0.0, 1.0, self)
        self.setItemDelegateForColumn(layer_table_model.property_columns['opacity'], self.opacity_delegate)
        self.setSelectionBehavior(Qt.QAbstractItemView.SelectRows)
        self.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)
        self.setModel(layer_table_model)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(Qt.QAbstractItemView.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.Qt.LinkAction)
        self.horizontalHeader().resizeSections(Qt.QHeaderView.ResizeToContents)
        # The text 'blend_function' is shorter than 'difference (advanced)', particularly with proportional fonts,
        # so we make it 50% wider to be safe
        col = layer_table_model.property_columns['blend_function']
        self.horizontalHeader().resizeSection(col, self.horizontalHeader().sectionSize(col) * 1.5)
        # The text 'size' is typically somewhat shorter than '2160x2560', so we widen that column
        # by an arbitrary fudge factor...
        col = layer_table_model.property_columns['size']
        self.horizontalHeader().resizeSection(col, self.horizontalHeader().sectionSize(col) * 3)
        # The text 'dtype' is typically somewhat shorter than 'uint16', so we widen that column
        # by an arbitrary fudge factor...
        col = layer_table_model.property_columns['dtype']
        self.horizontalHeader().resizeSection(col, self.horizontalHeader().sectionSize(col) * 1.5)
        # The text 'type' is typically somewhat shorter than 'rgba', so we widen that column
        # by an arbitrary fudge factor...
        col = layer_table_model.property_columns['type']
        self.horizontalHeader().resizeSection(col, self.horizontalHeader().sectionSize(col) * 1.5)
        # Making the opacity column exactly 100 pixels wide gives 1:1 mapping between horizontal
        # position within the column and opacity slider integer % values
        col = layer_table_model.property_columns['opacity']
        self.horizontalHeader().resizeSection(col, 100)

    def contextMenuEvent(self, event):
        focused_midx = self.selectionModel().currentIndex()
        if not focused_midx.isValid():
            return
        row = self.rowAt(event.pos().y())
        col = self.columnAt(event.pos().x())
        if row != focused_midx.row() or col != focused_midx.column():
            return
        try:
            pname = self.layer_table_model.property_names[col]
        except IndexError:
            return
        try:
            psdg = self.layer_table_model._special_data_getters[pname]
        except KeyError:
            return
        if psdg != self.layer_table_model._getd_defaultable_property:
            return
        try:
            layer = self.layer_table_model.layer_stack.layers[-(row+1)]
        except IndexError:
            return
        try:
            p = getattr(type(layer), pname)
        except AttributeError:
            return
        if p.is_default(layer):
            return
        menu = Qt.QMenu(self)
        reset_to_default_action = Qt.QAction('Reset to default value', menu)
        def on_reset_action():
            p.__delete__(layer)
        reset_to_default_action.triggered.connect(on_reset_action)
        menu.addAction(reset_to_default_action)
        menu.exec(event.globalPos())


class InvertingProxyModel(Qt.QSortFilterProxyModel):
    # Making a full proxy model that reverses/inverts indexes from Qt.QAbstractProxyModel or Qt.QIdentityProxyModel turns
    # out to be tricky but would theoretically be more efficient than this implementation for large lists.  However,
    # a layer stack will never be large enough for the inefficiency to be a concern.
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sort(0, Qt.Qt.DescendingOrder)

    def lessThan(self, lhs, rhs):
        # We want the table upside-down and therefore will be sorting by index (aka row #)
        return lhs.row() < rhs.row()

class LayerTableDragDropBehavior(om.signaling_list.DragDropModelBehavior):
    def _fix_row_for_inversion(self, row):
        if row == -1:
            return 0
        if row == len(self.signaling_list):
            return 0
        return row + 1

    def canDropMimeData(self, mime_data, drop_action, row, column, parent):
        return super().canDropMimeData(mime_data, drop_action, self._fix_row_for_inversion(row), column, parent)

    def dropMimeData(self, mime_data, drop_action, row, column, parent):
        return super().dropMimeData(mime_data, drop_action, self._fix_row_for_inversion(row), column, parent)

    def can_drop_rows(self, src_model, src_rows, dst_row, dst_column, dst_parent):
        return isinstance(src_model, LayerTableModel)

    def can_drop_text(self, txt, dst_row, dst_column, dst_parent):
        return bool(LayerList.from_json(txt))

    def handle_dropped_qimage(self, qimage, name, dst_row, dst_column, dst_parent):
        image = Image.from_qimage(qimage)
        if image is not None:
            layer = Layer(image=image)
            self.layer_stack.layers[dst_row:dst_row] = [layer]
            return True
        return False

    def handle_dropped_files(self, fpaths, dst_row, dst_column, dst_parent):
        freeimage = FREEIMAGE(show_messagebox_on_error=True, error_messagebox_owner=None)
        if freeimage is None:
            return False
        layers = LayerList()
        for fpath in fpaths:
            if fpath.suffix in ('.json', '.jsn'):
                with fpath.open('r') as f:
                    in_layers = LayerList.from_json(f.read())
                    if in_layers:
                        layers.extend(in_layers)
            else:
                fpath_str = str(fpath)
                layers.append(Layer(Image(freeimage.read(fpath_str), name=fpath_str)))
        self.layer_stack.layers[dst_row:dst_row] = layers
        return True

    def handle_dropped_text(self, txt, dst_row, dst_column, dst_parent):
        dropped_layers = LayerList.from_json(txt)
        if dropped_layers:
            self.layer_stack.layers[dst_row:dst_row] = dropped_layers

    def mimeData(self, midxs):
        mime_data = super().mimeData(midxs)
        mime_data.setText(self.layer_stack.layers.to_json())
        return mime_data

class LayerTableModel(LayerTableDragDropBehavior, om.signaling_list.PropertyTableModel):

    PROPERTIES = [
        'visible',
        'blend_function',
        'auto_min_max',
        'tint',
        'opacity',
        # 'getcolor_expression',
        # 'transform_section',
        'histogram_min',
        'histogram_max',
        'dtype',
        'type',
        'size',
        'name'
    ]

    def __init__(
            self,
            layer_stack,
            parent=None
        ):
        super().__init__(property_names=self.PROPERTIES, signaling_list=layer_stack.layers, parent=parent)
        self.layer_stack = layer_stack
        layer_stack.layers_replaced.connect(self._on_layers_replaced)
        layer_stack.solo_layer_mode_action.toggled.connect(self._on_examine_layer_mode_toggled)
        layer_stack.layer_focus_changed.connect(self._on_layer_focus_changed)
        self._focused_row = -1

        # Tack less commonly used / advanced blend function names onto list of dropdown choices without duplicating
        # entries for values that have verbose choice names
        self.blend_function_choices = ['normal', 'screen']
        other_blends = set(Layer.BLEND_FUNCTIONS.keys()) - set(self.blend_function_choices)
        self.blend_function_choices += sorted(other_blends)

        self._special_data_getters = {
            'visible': self._getd_visible,
            'auto_min_max': self._getd_auto_min_max,
            'tint': self._getd_tint,
            'blend_function': self._getd_blend_function,
            'getcolor_expression': self._getd_defaultable_property,
            'transform_section': self._getd_defaultable_property,
            'histogram_min': self._getd_defaultable_property,
            'histogram_max': self._getd_defaultable_property,
            'dtype': self._getd_dtype,
            'type': self._getd_darken_if_no_image,
            'size': self._getd_size,
            'name': self._getd_darken_if_no_image
        }
        self._special_flag_getters = {
            'visible': self._getf_always_checkable,
            'auto_min_max': self._getf_always_checkable,
            'dtype': self._getf_never_editable,
            'type': self._getf_never_editable,
            'size': self._getf_never_editable,
            'name': self._getf_never_editable
        }
        self._special_data_setters = {
            'visible': self._setd_visible,
            'auto_min_max': self._setd_checkable
        }

    # flags #

    def _getf_default(self, midx):
        return super().flags(midx)

    def _getf_always_checkable(self, midx):
        return self._getf_default(midx) & ~Qt.Qt.ItemIsEditable | Qt.Qt.ItemIsUserCheckable

    def _getf_never_editable(self, midx):
        return self._getf_default(midx) & ~Qt.Qt.ItemIsEditable

    def flags(self, midx):
        if midx.isValid():
            return self._special_flag_getters.get(self.property_names[midx.column()], self._getf_default)(midx)
        else:
            return self._getf_default(midx)

    # data #

    def _getd_default(self, midx, role):
        return super().data(midx, role)

    def _getd_defaultable_property(self, midx, role):
        if role == Qt.Qt.FontRole and midx.isValid():
            try:
                pname = self.property_names[midx.column()]
                element = self._signaling_list[midx.row()]
            except IndexError:
                return
            try:
                p = getattr(type(element), pname)
            except AttributeError:
                return
            if p.is_default(element):
                f = Qt.QFont()
                f.setItalic(True)
                return Qt.QVariant(f)
        return self._getd_default(midx, role)

    def _getd_visible(self, midx, role):
        if role == Qt.Qt.CheckStateRole:
            is_checked = self.get_cell(midx)
            if self.layer_stack.solo_layer_mode_action.isChecked():
                if self._focused_row == midx.row():
                    if is_checked:
                        r = Qt.Qt.Checked
                    else:
                        r = Qt.Qt.PartiallyChecked
                else:
                    r = Qt.Qt.Unchecked
            else:
                if is_checked:
                    r = Qt.Qt.Checked
                else:
                    r = Qt.Qt.Unchecked
            return Qt.QVariant(r)

    def _getd_auto_min_max(self, midx, role):
        if role == Qt.Qt.CheckStateRole:
            if self.get_cell(midx):
                r = Qt.Qt.Checked
            else:
                r = Qt.Qt.Unchecked
            return Qt.QVariant(r)

    def _getd_tint(self, midx, role):
        if role == Qt.Qt.DecorationRole:
            return Qt.QVariant(Qt.QColor(*(int(c*255) for c in self.signaling_list[midx.row()].tint)))
        elif role == Qt.Qt.DisplayRole:
            return Qt.QVariant(self.signaling_list[midx.row()].tint)

    def _getd_blend_function(self, midx, role):
        if role == CHOICES_QITEMDATA_ROLE:
            return Qt.QVariant(self.blend_function_choices)
        elif role == Qt.Qt.DisplayRole:
            return Qt.QVariant(self.signaling_list[midx.row()].blend_function)

    def _getd_size(self, midx, role):
        if role == Qt.Qt.DisplayRole:
            sz = self.get_cell(midx)
            if sz is not None:
                return Qt.QVariant('{}x{}'.format(sz.width(), sz.height()))
        else:
            return self._getd_darken_if_no_image(midx, role)

    def _getd_darken_if_no_image(self, midx, role):
        if role == Qt.Qt.BackgroundRole and self.signaling_list[midx.row()].image is None:
            return Qt.QVariant(Qt.QApplication.instance().palette().brush(Qt.QPalette.Disabled, Qt.QPalette.Dark))
        else:
            return self._getd_default(midx, role)

    def _getd_dtype(self, midx, role):
        if role == Qt.Qt.DisplayRole:
            dtype = self.get_cell(midx)
            if dtype is not None:
                return Qt.QVariant(str(dtype))
        else:
            return self._getd_darken_if_no_image(midx, role)

    def data(self, midx, role=Qt.Qt.DisplayRole):
        if midx.isValid():
            d = self._special_data_getters.get(self.property_names[midx.column()], self._getd_default)(midx, role)
            if isinstance(d, Qt.QVariant):
                return d
        else:
            return self._getd_default(midx, role)

    # setData #

    def _setd_checkable(self, midx, value, role):
        if role == Qt.Qt.CheckStateRole:
            if isinstance(value, Qt.QVariant):
                value = value.value()
            return super().setData(midx, value)
        return False

    def _setd_visible(self, midx, value, role):
        if role == Qt.Qt.CheckStateRole:
            if isinstance(value, Qt.QVariant):
                value = value.value()
            if value == Qt.Qt.Checked and self.layer_stack.solo_layer_mode_action.isChecked() and self._focused_row != midx.row():
                # checkbox_delegate is telling us that, as a result of being hit, we should to check a visibility checkbox
                # that is shown as partially checked.  However, it is shown as partially checked because it is actually checked,
                # but the effect of its checkedness is being supressed because we are in "examine layer" mode and the layer
                # containing the visibility checkbox in question is not the current layer in the layer table.  It is nominally
                # checked, and so toggling it actually means unchecking it.  This is the only instance where an override
                # causes something checked to appear partially checked, rather than causing something unchecked to appear
                # partially checked.  And, so, in this one instance, we must special case *setting* of an overridable checkbox
                # property.
                value = Qt.Qt.Unchecked
            return super().setData(midx, value)
        return False

    def setData(self, midx, value, role=Qt.Qt.EditRole):
        if midx.isValid():
            return self._special_data_setters.get(self.property_names[midx.column()], super().setData)(midx, value, role)
        return False

    def _on_layers_replaced(self, layer_stack, old_layers, layers):
        self.signaling_list = layers

    def _refresh_column(self, column):
        if self.signaling_list is not None:
            self.dataChanged.emit(self.createIndex(0, column), self.createIndex(len(self.signaling_list)-1, column))

    def _on_examine_layer_mode_toggled(self):
        self._refresh_column(self.property_columns['visible'])

    def _on_layer_focus_changed(self, layer_stack, old_layer, layer):
        self._handle_layer_focus_change()

    def _handle_layer_focus_change(self):
        self._focused_row = self.layer_stack.focused_layer_idx
        self._on_examine_layer_mode_toggled()