# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
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
import numpy
import pyagg
import sys

from . import canvas
from . import image_canvas
from . import histogram_canvas
from .image import Image

class RisWidget(Qt.QMainWindow):
    # The image_changed signal is emitted when a new value is successfully assigned to the
    # RisWidget.image property
    image_changed = Qt.pyqtSignal()

    def __init__(self, window_title='RisWidget', parent=None, window_flags=Qt.Qt.WindowFlags(0)):
        super().__init__(parent, window_flags)
        if sys.platform == 'darwin': # workaround for https://bugreports.qt.io/browse/QTBUG-44230
            hs = Qt.QSlider(Qt.Qt.Horizontal)
            hs.show()
            hs.hide()
            hs.destroy()
            del hs
        if window_title is not None:
            self.setWindowTitle(window_title)
        self.setAcceptDrops(True)
        self._init_views()
        self._init_actions()
        self._init_toolbars()
        self._image = None

    def _init_actions(self):
        self._image_view_zoom_to_fit_action = Qt.QAction(self)
        self._image_view_zoom_to_fit_action.setCheckable(True)
        self._image_view_zoom_to_fit_action.setText('Zoom to Fit')

    @staticmethod
    def _format_zoom(zoom):
        if int(zoom) == zoom:
            return '{}'.format(int(zoom))
        else:
            txt = '{:.2f}'.format(zoom)
            if txt[-2:] == '00':
                return txt[:-3]
            if txt[-1:] == '0':
                return txt[:-1]
            return txt

    def _init_toolbars(self):
        self._image_view_toolbar = self.addToolBar('View')
        self._image_view_zoom_combo = Qt.QComboBox(self)
        self._image_view_toolbar.addWidget(self._image_view_zoom_combo)
        self._image_view_zoom_combo.setEditable(True)
        self._image_view_zoom_combo.setInsertPolicy(Qt.QComboBox.NoInsert)
        self._image_view_zoom_combo.setDuplicatesEnabled(True)
        self._image_view_zoom_combo.setSizeAdjustPolicy(Qt.QComboBox.AdjustToContents)
        for zoom in image_canvas.ImageView._ZOOM_PRESETS:
            self._image_view_zoom_combo.addItem(self._format_zoom(zoom * 100) + '%')
        self._image_view_zoom_combo.setCurrentIndex(image_canvas.ImageView._ZOOM_DEFAULT_PRESET_IDX)
        self._image_view_zoom_combo.activated[int].connect(self._image_view_zoom_combo_changed)
        self._image_view_zoom_combo.lineEdit().returnPressed.connect(self._image_view_zoom_combo_custom_value_entered)
        self.image_view.zoom_changed.connect(self._image_view_zoom_changed)
        self._image_view_toolbar.addAction(self._image_view_zoom_to_fit_action)
        self._image_view_zoom_to_fit_action.triggered[bool].connect(self._image_view_zoom_to_fit_action_toggled)
        self.image_view.zoom_to_fit_changed.connect(self._image_view_zoom_to_fit_changed)

    def _init_views(self):
        self.image_scene = image_canvas.ImageScene(self)
        self.image_view = image_canvas.ImageView(self.image_scene, self)
        self.setCentralWidget(self.image_view)
        self.histogram_scene = histogram_canvas.HistogramScene(self)
        self._histogram_dock_widget = Qt.QDockWidget('Histogram', self)
        self.histogram_view, self._histogram_container_widget = histogram_canvas.HistogramView.make_histogram_and_container_widgets(self.histogram_scene, self._histogram_dock_widget)
        self.image_view.histogram_view = self.histogram_view
        self._histogram_dock_widget.setWidget(self._histogram_container_widget)
        self._histogram_dock_widget.setAllowedAreas(Qt.Qt.BottomDockWidgetArea | Qt.Qt.TopDockWidgetArea)
        self._histogram_dock_widget.setFeatures(Qt.QDockWidget.DockWidgetFloatable | Qt.QDockWidget.DockWidgetMovable | Qt.QDockWidget.DockWidgetVerticalTitleBar)
        self.addDockWidget(Qt.Qt.BottomDockWidgetArea, self._histogram_dock_widget)
        self.histogram_view.gamma_or_min_max_changed.connect(self.image_scene.image_item.update)
        self.histogram_scene.request_mouseover_info_status_text_change.connect(self.histogram_view._on_request_mouseover_info_status_text_change)
        self.image_scene.request_mouseover_info_status_text_change.connect(self.histogram_view._on_request_mouseover_info_status_text_change)

    @property
    def image_data(self):
        """image_data property:
        The input assigned to this property may be None, in which case the current image and histogram views are cleared,
        and otherwise must be convertable to a 2D or 3D numpy array of shape (w, h) or (w, h, c), respectively*.  2D input
        is interpreted as grayscale.  3D input, depending on the value of c, is iterpreted as grayscale & alpha (c of 2),
        red & blue & green (c of 3), or red & blue & green & alpha (c of 4).

        The following dtypes are directly supported (data of any other type is converted to 32-bit floating point,
        and an exception is thrown if conversion fails):
        numpy.uint8
        numpy.uint16
        numpy.float32

        Supplying a numpy array of one of the above types as input may avoid an intermediate copy step by allowing RisWidget
        to keep a reference to the supplied array, allowing its data to be accessed directly.


        * IE, the iterable assigned to the image property is interpreted as an iterable of columns (image left to right), each
        containing an iterable of rows (image top to bottom), each of which is either a grayscale intensity value or an
        iterable of color channel intensity values (gray & alpha, or red & green & blue, or red & green & blue & alpha)."""
        return None if self._image is None else self._image.data

    @image_data.setter
    def image_data(self, image_data):
        self.image = None if image_data is None else Image(image_data)

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        if image is not None and not issubclass(type(image), Image):
            raise ValueError('The value assigned to the image property must either be derived from ris_widget.image.Image or must be None.  Did you mean to assign to the image_data property?')
        self.image_scene._on_image_changed(image)
        self.image_view._on_image_changed(image)
        self.histogram_view._on_image_changed(image)
        self._image = image
        self.image_changed.emit()

    def _image_view_zoom_changed(self, zoom_preset_idx, custom_zoom):
        assert zoom_preset_idx == -1 and custom_zoom != 0 or zoom_preset_idx != -1 and custom_zoom == 0, 'zoom_preset_idx XOR custom_zoom must be set.'
        if zoom_preset_idx == -1:
            self._image_view_zoom_combo.lineEdit().setText(self._format_zoom(custom_zoom * 100) + '%')
        else:
            self._image_view_zoom_combo.setCurrentIndex(zoom_preset_idx)

    def _image_view_zoom_to_fit_changed(self, zoom_to_fit):
        """Handle self.image_view.zoom_to_fit property change."""
        if zoom_to_fit != self._image_view_zoom_to_fit_action.isChecked():
            self._image_view_zoom_to_fit_action.setChecked(zoom_to_fit)
            self._image_view_zoom_combo.setEnabled(not zoom_to_fit)

    def _image_view_zoom_combo_changed(self, idx):
        self.image_view.zoom_preset_idx = idx

    def _image_view_zoom_to_fit_action_toggled(self, zoom_to_fit):
        """Change self._image_widget.zoom_to_fit property value in response to GUI manipulation."""
        self._image_view_zoom_combo.setEnabled(not zoom_to_fit)
        self.image_view.zoom_to_fit = zoom_to_fit

    def _image_view_zoom_combo_custom_value_entered(self):
        txt = self._image_view_zoom_combo.lineEdit().text()
        percent_pos = txt.find('%')
        scale_txt = txt if percent_pos == -1 else txt[:percent_pos]
        try:
            self.image_view.custom_zoom = float(scale_txt) * 0.01
        except ValueError:
            Qt.QMessageBox.information(self, self.windowTitle(), 'Please enter a number between {} and {}.'.format(self._format_zoom(image_canvas.ImageView._ZOOM_MIN_MAX[0] * 100),
                                                                                                                   self._format_zoom(image_canvas.ImageView._ZOOM_MIN_MAX[1] * 100)))
            self._image_view_zoom_combo.setFocus()
            self._image_view_zoom_combo.lineEdit().selectAll()

if __name__ == '__main__':
    import sys
    app = Qt.QApplication(sys.argv)
    rw = RisWidget()
    rw.show()
    app.exec_()
