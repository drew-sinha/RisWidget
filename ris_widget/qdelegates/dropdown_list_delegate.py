# This code is licensed under the MIT License (see LICENSE file for details)

from PyQt5 import Qt

CHOICES_QITEMDATA_ROLE = Qt.Qt.UserRole + 1

class DropdownListDelegate(Qt.QStyledItemDelegate):
    def createEditor(self, parent, option, midx):
        # We don't make use of "edit mode".  Returning None here prevents double click, enter keypress, etc, from
        # engaging the default delegate behavior of dropping us into string edit mode, wherein a blinking text cursor
        # is displayed in the cell.
        return None

    def editorEvent(self, event, model, option, midx):
        if not midx.isValid() or option.widget is None:
            return False
        flags = midx.flags()
        item_is_enabled = flags | Qt.Qt.ItemIsEnabled
        item_is_editable = flags | Qt.Qt.ItemIsEditable
        if not item_is_enabled or not item_is_editable:
            return False
        menu = Qt.QMenu(option.widget)
        menu.setAttribute(Qt.Qt.WA_DeleteOnClose)
        choices = midx.data(CHOICES_QITEMDATA_ROLE)
        choice_actions = [menu.addAction(choice) for choice in choices]
        try:
            current_choice = midx.data()
            if isinstance(current_choice, Qt.QVariant):
                current_choice = current_choice.value()
            current_choice_action = choice_actions[choices.index(current_choice)]
            menu.setActiveAction(current_choice_action)
        except ValueError:
            current_choice_action = None
        cell_rect = option.widget.visualRect(midx)
        menu_pos = option.widget.mapToGlobal(Qt.QPoint(cell_rect.left(), (cell_rect.top() + cell_rect.bottom())/2))
        pmidx = Qt.QPersistentModelIndex(midx)
        def on_entry_selected(action):
            if pmidx.isValid():
                model.setData(model.index(pmidx.row(), pmidx.column()), action.text().replace('&',''))
        menu.triggered.connect(on_entry_selected)
        menu.popup(menu_pos, current_choice_action)
        return False
