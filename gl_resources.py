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

import numpy
from PyQt5 import Qt
import sys

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

_GL_QSURFACE_FORMAT = None

def GL_QSURFACE_FORMAT():
    global _GL_QSURFACE_FORMAT
    if _GL_QSURFACE_FORMAT is None:
        _GL_QSURFACE_FORMAT = Qt.QSurfaceFormat()
        _GL_QSURFACE_FORMAT.setRenderableType(Qt.QSurfaceFormat.OpenGL)
        _GL_QSURFACE_FORMAT.setVersion(2, 1)
        _GL_QSURFACE_FORMAT.setProfile(Qt.QSurfaceFormat.CompatibilityProfile)
        _GL_QSURFACE_FORMAT.setSwapBehavior(Qt.QSurfaceFormat.DoubleBuffer)
        _GL_QSURFACE_FORMAT.setStereo(False)
        _GL_QSURFACE_FORMAT.setSwapInterval(1)

        # Specifically enabling alpha channel is not sufficient for enabling QPainter composition modes that
        # use destination alpha (ie, nothing drawn in CompositionMode_DestinationOver will be visible in
        # a painGL widget).
#       _GL_QSURFACE_FORMAT.setRedBufferSize(8)
#       _GL_QSURFACE_FORMAT.setGreenBufferSize(8)
#       _GL_QSURFACE_FORMAT.setBlueBufferSize(8)
#       _GL_QSURFACE_FORMAT.setAlphaBufferSize(8)
    return _GL_QSURFACE_FORMAT

# _GL is set to instance of QOpenGLFunctions_2_1 (or QOpenGLFunctions_2_0 for old PyQt5 versions) during
# creation of first OpenGL widget.  QOpenGLFunctions_VER are obese namespaces containing all OpenGL
# plain procedural C functions and #define values valid for the associated OpenGL version, in Python
# wrappers.  It doesn't matter which context birthed the QOpenGLFunctions_VER object, only that
# an OpenGL context is current for the thread executing a QOpenGLFunctions_VER method.
_GL = None

def GL():
    global _GL
    if _GL is None:
        context = Qt.QOpenGLContext.currentContext()
        if context is not None:
            try:
                _GL = context.versionFunctions()
            except ImportError:
                # PyQt5 v5.4.0 and v5.4.1 provide access to OpenGL functions up to OpenGL 2.0, but we have made
                # an OpenGL 2.1 context.  QOpenGLContext.versionFunctions(..) will, by default, attempt to return
                # a wrapper around QOpenGLFunctions2_1, which has failed in the try block above.  Therefore,
                # we fall back to explicitly requesting 2.0 functions.  We don't need any of the C _GL 2.1
                # constants or calls, anyway - these address non-square shader uniform transformation matrices and
                # specification of sRGB texture formats, neither of which we use.
                vp = Qt.QOpenGLVersionProfile()
                vp.setProfile(Qt.QSurfaceFormat.CompatibilityProfile)
                vp.setVersion(2, 0)
                _GL = context.versionFunctions(vp)
            if not _GL:
                raise RuntimeError('Failed to retrieve OpenGL wrapper namespace.')
            if not _GL.initializeOpenGLFunctions():
                raise RuntimeError('Failed to initialize OpenGL wrapper namespace.')
    return _GL
