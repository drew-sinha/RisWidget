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

#pragma once

#include "Common.h"
#include "GlProgram.h"

class View
  : public QGLWidget
{
    Q_OBJECT;

public:
    struct SharedGlObjects
    {
        bool inited{false};

        HistoCalcProg histoCalcProg;
        HistoConsolidateProg histoConsolidateProg;
        ImageDrawProg imageDrawProg;
        HistoDrawProg histoDrawProg;

        void init(QGLContext* context);
    };
    typedef std::shared_ptr<SharedGlObjects> SharedGlObjectsPtr;

    View(const QGLFormat& format,
         QWidget* parent,
         const SharedGlObjectsPtr& sharedGlObjects_,
         const View* shareWidget = nullptr,
         Qt::WindowFlags flags = 0);
    virtual ~View();

    const SharedGlObjectsPtr& sharedGlObjects();

protected:
    SharedGlObjectsPtr m_sharedGlObjects;

    virtual void initializeGL();
};