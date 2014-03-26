#version 430 core

uniform mat4 projectionModelViewMatrix;
uniform uint binCount;
uniform float binScale;
layout (binding = 0, r32ui) uniform readonly uimage1D histogram;

in float binIndex;

void main()
{
    gl_Position = projectionModelViewMatrix * vec4((float(binIndex) / float(binCount) - 0.5) * 2.0,
                                                   (log(float(imageLoad(histogram, int(binIndex)).r)) / binScale - 0.5) * 2.0,
                                                    0.4,
                                                    1.0);
}
