// The MIT License (MIT)
//
// Copyright (c) 2014 Erik Hvatum
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include "Common.h"
#include "View.h"

void View::SharedGlObjects::init(QGLContext* context)
{
    if(!inited)
    {
        histoCalcProg.setContext(context);
        histoCalcProg.build();

        histoConsolidateProg.setContext(context);
        histoConsolidateProg.build();

        imageDrawProg.setContext(context);
        imageDrawProg.build();

        histoDrawProg.setContext(context);
        histoDrawProg.build();

        inited = true;
    }
}

View::View(const QGLFormat& format,
                       QWidget* parent,
                       const SharedGlObjectsPtr& sharedGlObjects_,
                       const View* shareWidget,
                       Qt::WindowFlags flags)
  : QGLWidget(format, parent, shareWidget, flags),
    m_sharedGlObjects(sharedGlObjects_)
{
}

View::~View()
{
}

const View::SharedGlObjectsPtr& View::sharedGlObjects()
{
    return m_sharedGlObjects;
}

void View::initializeGL()
{
    m_sharedGlObjects->init(context());
}