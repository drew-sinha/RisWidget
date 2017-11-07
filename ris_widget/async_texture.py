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

import contextlib
import threading
import queue
import weakref

import numpy
from OpenGL import GL
from PyQt5 import Qt

from . import shared_resources

IMAGE_TYPE_TO_GL_FORMATS = {
    'G': (Qt.QOpenGLTexture.R32F, GL.GL_RED),
    'Ga': (Qt.QOpenGLTexture.RG32F, GL.GL_RG),
    'rgb': (Qt.QOpenGLTexture.RGB32F, GL.GL_RGB),
    'rgba': (Qt.QOpenGLTexture.RGBA32F, GL.GL_RGBA)
}

NUMPY_DTYPE_TO_GL_PIXEL_TYPE = {
    numpy.bool8  : GL.GL_UNSIGNED_BYTE,
    numpy.uint8  : GL.GL_UNSIGNED_BYTE,
    numpy.uint16 : GL.GL_UNSIGNED_SHORT,
    numpy.float32: GL.GL_FLOAT}

USE_BG_UPLOAD_THREAD = True # debug flag for testing with flaky drivers

class AsyncTexture:
    _LIVE_TEXTURES = None
    @classmethod
    def _on_about_to_quit(cls):
        with shared_resources.offscreen_context():
            for t in cls._LIVE_TEXTURES:
                t.destroy()

    def __init__(self, image):
        if self._LIVE_TEXTURES is None:
            # if we used 'self' instead of __class__, would just set _LIVE_TEXTURES for this instance
            __class__._LIVE_TEXTURES = weakref.WeakSet()
            Qt.QApplication.instance().aboutToQuit.connect(self._on_about_to_quit)
        self.data = image.data
        self.format, self.source_format = IMAGE_TYPE_TO_GL_FORMATS[image.type]
        self.source_type = NUMPY_DTYPE_TO_GL_PIXEL_TYPE[self.data.dtype.type]
        self.done = threading.Event()
        self.texture = None

    def upload(self, upload_region=None):
        if self.texture is None and upload_region is not None:
            raise ValueError('The first time the texture is uploaded, the full region must be used.')
        if USE_BG_UPLOAD_THREAD:
            OffscreenContextThread.get().enqueue(self._upload, [upload_region])
        else:
            self._upload_fg(upload_region)

    def bind(self, tex_unit):
        self.done.wait()
        if hasattr(self, 'exception'):
            raise self.exception
        assert self.texture is not None
        self.texture.bind(tex_unit)

    def release(self, tex_unit):
        assert self.texture is not None
        self.texture.release(tex_unit)

    def destroy(self):
        if self.texture is not None:
            # requires a valid context
            assert Qt.QOpenGLContext.currentContext() is not None
            self.texture.destroy()
            self.texture = None

    def _upload_fg(self, upload_region):
        assert Qt.QOpenGLContext.currentContext() is not None
        QGL = shared_resources.QGL()
        orig_unpack_alignment = QGL.glGetIntegerv(QGL.GL_UNPACK_ALIGNMENT)
        QGL.glPixelStorei(QGL.GL_UNPACK_ALIGNMENT, 1)
        try:
            self._upload(upload_region)
        finally:
            # QPainter font rendering for OpenGL surfaces can break if we do not restore GL_UNPACK_ALIGNMENT
            # and this function was called within QPainter's native painting operations
            QGL.glPixelStorei(QGL.GL_UNPACK_ALIGNMENT, orig_unpack_alignment)

    def _upload(self, upload_region):
        try:
            if self.texture is None:
                texture = Qt.QOpenGLTexture(Qt.QOpenGLTexture.Target2D)
                texture.setFormat(self.format)
                texture.setWrapMode(Qt.QOpenGLTexture.ClampToEdge)
                texture.setMipLevels(6)
                texture.setAutoMipMapGenerationEnabled(False)
                data = self.data
                texture.setSize(data.shape[0], data.shape[1], 1)
                texture.allocateStorage()
                texture.setMinMagFilters(Qt.QOpenGLTexture.LinearMipMapLinear, Qt.QOpenGLTexture.Nearest)
                self.texture = texture
                self._LIVE_TEXTURES.add(self)
            self.texture.bind()
            try:
                #TODO: use QOpenGLTexture.setData here, and pixel storage
                # functions to allow strided arrays.
                #TODO: use upload_region to allow updates to only a portion
                # of the texture
                GL.glTexSubImage2D(
                    GL.GL_TEXTURE_2D, 0, 0, 0, data.shape[0], data.shape[1],
                    self.source_format,
                    self.source_type,
                    memoryview(data.swapaxes(0,1).flatten()))
                self.texture.generateMipMaps()
            finally:
                self.texture.release()
        except Exception as e:
            self.exception = e
        finally:
            self.done.set()

class OffscreenContextThread(Qt.QThread):
    _ACTIVE_THREAD = None

    @classmethod
    def get(cls):
        if cls._ACTIVE_THREAD is None:
            cls._ACTIVE_THREAD = cls()
            # TODO: is below necessary ever?
            # Qt.QApplication.instance().aboutToQuit.connect(cls._ACTIVE_THREAD.shut_down)
        return cls._ACTIVE_THREAD

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.running = True
        self.start()

    def enqueue(self, func, args):
        self.queue.put((func, args))

    def shut_down(self):
        self.running = False
        # now wake up the thread if it's blocked waiting for a texture
        self.queue.put(None)
        self.wait()

    def run(self):
        gl_context = Qt.QOpenGLContext()
        gl_context.setShareContext(Qt.QOpenGLContext.globalShareContext())
        gl_context.setFormat(shared_resources.GL_QSURFACE_FORMAT)
        if not gl_context.create():
            raise RuntimeError('Failed to create OpenGL context for background texture upload thread.')
        gl_context.makeCurrent(shared_resources.OFFSCREEN_SURFACE)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        try:
            while self.running:
                func, args = self.queue.get()
                if not self.running:
                    #self.running may go to false while blocked waiting on the queue
                    break
                func(*args)
        finally:
            gl_context.doneCurrent()