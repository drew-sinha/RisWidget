# The MIT License (MIT)
#
# Copyright (c) 2014 Erik Hvatum
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

TEMPLATE = lib
LANGUAGE = C++
QT += core gui widgets opengl
CONFIG += static c++11 precompile_header exceptions rtti stl thread
CONFIG -= app_bundle
TARGET = RisWidget
INCLUDEPATH += /usr/local/glm

RESOURCES = RisWidget.qrc

PRECOMPILED_HEADER = Common.h

HEADERS += Common.h \
           HistogramWidget.h \
           HistogramView.h \
           ImageWidget.h \
           ImageView.h \
           RisWidget.h \
           RisWidgetException.h \
           View.h \
           GlProgram.h

FORMS +=   RisWidget.ui \
           HistogramWidget.ui \
           ImageWidget.ui

SOURCES += RisWidget.cpp \
           HistogramWidget.cpp \
           HistogramView.cpp \
           ImageWidget.cpp \
           ImageView.cpp \
           RisWidgetException.cpp \
           View.cpp \
           GlProgram.cpp