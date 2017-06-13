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

from PyQt5 import Qt
from . import flipbook

class _BaseField(Qt.QObject):
    widget_value_changed = Qt.pyqtSignal(object)

    def __init__(self, field_tuple, parent):
        super().__init__(parent)
        self.name = field_tuple[0]
        self.type = field_tuple[1]
        self.default = field_tuple[2]
        self.field_tuple = field_tuple
        self._init_widget()

    def _init_widget(self):
        pass

    def _on_widget_change(self):
        self.widget_value_changed.emit(self)

    def refresh(self, value):
        self.widget.setValue(value)

    def value(self):
        return self.widget.value()

class _NoClickToPartialTristateCheckbox(Qt.QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTristate(True)

    def nextCheckState(self):
        # Do not enter partially clicked state in response to checkbox widget manipulation.  Calling
        # setCheckState(Qt.Qt.PartiallyChecked) is not affected (that is, continues to work as normal).
        self.setCheckState(Qt.Qt.Unchecked if self.isChecked() else Qt.Qt.Checked)

class _BoolField(_BaseField):
    CHECK_STATE_VALUES = {
        Qt.Qt.Checked : True,
        Qt.Qt.Unchecked : False,
        Qt.Qt.PartiallyChecked : None
    }
    VALUE_CHECK_STATES = {v : k for k, v in CHECK_STATE_VALUES.items()}

    def _init_widget(self):
        self.widget = _NoClickToPartialTristateCheckbox()
        self.widget.stateChanged.connect(self._on_widget_change)
        self.widget.setFocusPolicy(Qt.Qt.WheelFocus)

    def refresh(self, value):
        self.widget.setCheckState(self.VALUE_CHECK_STATES[value])

    def value(self):
        return self.CHECK_STATE_VALUES[self.widget.checkState()]

class _StringField(_BaseField):
    def _init_widget(self):
        self.widget = Qt.QLineEdit()
        self.widget.textEdited.connect(self._on_widget_change)

    def refresh(self, value):
        self.widget.setText(value)

    def value(self):
        return self.widget.text()

class _NumField(_BaseField):
    def _init_widget(self):
        self.widget = Qt.QLineEdit()
        self.min = self.field_tuple[3] if len(self.field_tuple) >= 4 else None
        self.max = self.field_tuple[4] if len(self.field_tuple) >= 5 else None
        self.widget.textEdited.connect(self._on_widget_change)
        self.widget.editingFinished.connect(self._on_editing_finished)

    def _on_editing_finished(self):
        v = self.value()
        self.refresh(v)

    def refresh(self, value):
        self.widget.setText('' if value is None else str(value))

    def value(self):
        t = self.widget.text()
        if len(t) == 0:
            return None
        try:
            v = self.NUM_TYPE(t)
        except ValueError:
            return self.default
        if self.min is not None and v < self.min:
            return self.min
        elif self.max is not None and v > self.max:
            return self.max
        else:
            return v

class _IntField(_NumField):
    NUM_TYPE = int

class _FloatField(_NumField):
    NUM_TYPE = float

class _ChoiceField(_BaseField):
    def __init__(self, field_tuple, parent):
        choices = tuple(field_tuple[3])
        assert len(set(choices)) == len(choices), "choices must be unique"
        assert field_tuple[2] in choices, "value supplied for default must be a choice"
        self.choices = choices
        super().__init__(field_tuple, parent)

    def _init_widget(self):
        self.widget = Qt.QComboBox()
        for choice in self.choices:
            self.widget.addItem(choice)
        self.widget.currentIndexChanged[str].connect(self._on_widget_change)
        self.widget.setFocusPolicy(Qt.Qt.WheelFocus)

    def refresh(self, value):
        if value is None:
            self.widget.setCurrentIndex(-1)
        else:
            self.widget.setCurrentText(value)

    def value(self):
        i = self.widget.currentIndex()
        return None if i==-1 else self.choices[i]

class FlipbookPageAnnotator(Qt.QWidget):
    """Field widgets are grayed out when no flipbook entry is selected."""
    TYPE_FIELD_CLASSES = {
        bool: _BoolField,
        str: _StringField,
        int: _IntField,
        float : _FloatField,
        tuple : _ChoiceField
    }
    def __init__(self, flipbook, page_metadata_attribute_name, field_descrs, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.Qt.WA_DeleteOnClose)
        self.flipbook = flipbook
        flipbook.page_selection_changed.connect(self._on_page_selection_changed)
        self.page_metadata_attribute_name = page_metadata_attribute_name
        layout = Qt.QFormLayout()
        layout.setFieldGrowthPolicy(layout.ExpandingFieldsGrow)
        self.setLayout(layout)
        self.fields = {}
        self._ignore_gui_change = False
        for field_descr in field_descrs:
            assert field_descr[0] not in self.fields
            field = self._make_field(field_descr)
            field.refresh(field_descr[2])
            field.widget_value_changed.connect(self._on_gui_change)
            layout.addRow(field.name, field.widget)
            self.fields[field_descr[0]] = field
        self.refresh_gui()

    @property
    def data(self):
        data = []
        for page in self.flipbook.pages:
            if hasattr(page, self.page_metadata_attribute_name):
                page_data = getattr(page, self.page_metadata_attribute_name)
            else:
                page_data = {}
                setattr(page, self.page_metadata_attribute_name, page_data)
            for field in self.fields.values():
                if field.name not in page_data:
                    page_data[field.name] = field.default
            data.append(page_data)
        return data

    @data.setter
    def data(self, v):
        # Replace relevant values in annotations of corresponding pages.  In the situation where an incomplete
        # dict is supplied for a page also missing the omitted values, defaults are assigned.
        m_n = self.page_metadata_attribute_name
        for page_v, page in zip(v, self.flipbook.pages):
            old_page_data = getattr(page, m_n, {})
            updated_page_data = {}
            for field in self.fields.values():
                n = field.name
                if n in page_v:
                    updated_page_data[n] = page_v[n]
                elif n in old_page_data:
                    updated_page_data[n] = old_page_data[n]
                else:
                    updated_page_data[n] = field.default
            setattr(page, m_n, updated_page_data)
        self.refresh_gui()

    def _make_field(self, field_descr):
        return self.TYPE_FIELD_CLASSES[field_descr[1]](field_descr, self)

    def _on_page_selection_changed(self):
        self.refresh_gui()

    def _on_gui_change(self, field):
        if not self._ignore_gui_change:
            pages = self.flipbook.selected_pages
            m_n = self.page_metadata_attribute_name
            v = field.value()
            if v is None:
                return
            for page in pages:
                try:
                    data = getattr(page, m_n)
                except AttributeError:
                    continue
                data[field.name] = v

    def refresh_gui(self):
        """Ensures that the currently selected flipbook pages' annotation dicts contain at least default values, and
        updates the annotator GUI with data from the annotation dicts."""
        pages = self.flipbook.selected_pages
        layout = self.layout()
        self._ignore_gui_change = True
        try:
            if len(pages) == 0:
                for field in self.fields.values():
                    field.widget.setEnabled(False)
                    layout.labelForField(field.widget).setEnabled(False)
            elif len(pages) == 1:
                page = pages[0]
                if hasattr(page, self.page_metadata_attribute_name):
                    data = getattr(page, self.page_metadata_attribute_name)
                else:
                    data = {}
                    setattr(page, self.page_metadata_attribute_name, data)
                for field in self.fields.values():
                    if field.name in data:
                        v = data[field.name]
                    else:
                        v = data[field.name] = field.default
                    field.refresh(v)
                    field.widget.setEnabled(True)
                    layout.labelForField(field.widget).setEnabled(True)
            else:
                initial = True
                for page in pages:
                    if not isinstance(page, flipbook.ImageList):
                        continue
                    if hasattr(page, self.page_metadata_attribute_name):
                        data = getattr(page, self.page_metadata_attribute_name)
                    else:
                        data = {}
                        setattr(page, self.page_metadata_attribute_name, data)
                    for field in self.fields.values():
                        if field.name not in data:
                            data[field.name] = field.default
                    if initial:
                        initial = False
                        fvs = {}
                        for field in self.fields.values():
                            v = fvs[field.name] = data[field.name]
                            field.widget.setEnabled(True)
                    else:
                        for field_name, field_value in list(fvs.items()):
                            if data[field_name] != field_value:
                                del fvs[field_name]
                for field in self.fields.values():
                    field.refresh(fvs.get(field.name))
        finally:
            self._ignore_gui_change = False