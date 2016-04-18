#!/usr/bin/env python

import numpy
import os.path
from pathlib import Path
from PyQt5 import Qt
from ris_widget.ris_widget import RisWidget
import freeimage
import sys

argv = sys.argv
#Qt.QCoreApplication.setAttribute(Qt.Qt.AA_ShareOpenGLContexts)
app = Qt.QApplication(argv)
rw = RisWidget()
# rw.main_view.zoom_preset_idx = 27

rw.flipbook.pages.append(numpy.array(list(range(10000)),numpy.float32).reshape((100,100)))
rw.flipbook.pages[0][0].name = 'image'
rw.flipbook.pages[0].append(numpy.zeros((100,10), numpy.bool))
rw.flipbook.pages[0][1].name = 'mask'

from ris_widget.ndimage_statistics import _ndimage_statistics
from matplotlib import pyplot as plt
plt.ion()
fig = plt.figure()

def on_mask_data_changed():
    hist = numpy.zeros((2048,),numpy.uint32)
    range_ = rw.flipbook.pages[0][0].range.copy()
    range_[0] = 4000
    range_[1] = 5000
    _ndimage_statistics.masked_ranged_hist(rw.flipbook.pages[0][0].data, rw.flipbook.pages[0][1].data, range_, hist, True)
    fig.clear()
    plt.scatter(list(range(2048)), hist)
    print(hist[0], hist[-1], hist.max(), hist.argmax())

rw.flipbook_pages[0][1].data_changed.connect(on_mask_data_changed)
on_mask_data_changed()

# rw.image = numpy.zeros((100,100), dtype=numpy.uint8)

# from ris_widget.examples.main_thread_mandelbrot import MandelbrotWidget
# mandelbrot_widget = MandelbrotWidget(rw.image)

# rw_dpath = Path(os.path.expanduser('~')) / 'zplrepo' / 'ris_widget'
# rw.add_image_files_to_flipbook([
#     [rw_dpath / 'Opteron_6300_die_shot_16_core_mod.jpg']#, rw_dpath / 'top_left_g.png'],
#     ['/Volumes/MrSpinny/14/2015-11-18t0948 focus-03_ffc.png']
# ])




# from ris_widget.qwidgets.layer_stack_painter import LayerStackPainter
# lsp = LayerStackPainter(rw.main_scene.layer_stack_item)
# lsp.show()

# plp, plpt = rw.make_poly_line_picker_and_table()

# rw.qt_object.layer_stack.histogram_alternate_column_shading_enabled = True
# rw.layer.histogram_min = 0
# rw.layer.histogram_max = 1
# rw.image = imf
#
# btn = Qt.QPushButton('swap float range setting')
# float_range_state = False
# def on_btn_clicked():
#     global float_range_state
#     rw.image.set(imposed_float_range=[0,255] if float_range_state else [50,100])
#     float_range_state = not float_range_state
# btn.clicked.connect(on_btn_clicked)
# btn.show()

#rw.histogram_view.gl_widget.start_logging()

app.exec_()