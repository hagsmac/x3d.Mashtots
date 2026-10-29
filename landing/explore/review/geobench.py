#!/usr/bin/env python3
"""Synthetic X_ITE load benchmark: how setup time grows with the size of ONE shape (ComposedShader, unlit), and what splitting it into chunks
does. Writes bench/*.x3d; time each with loadprobe.html?src=bench/NAME.x3d&min=1 (first_frame_ms, main-thread long tasks)."""
import os, random
os.makedirs("bench", exist_ok=True)
VS = "data:x-shader/x-vertex,#version 300 es\nprecision highp float;\nuniform mat4 x3d_ProjectionMatrix; uniform mat4 x3d_ModelViewMatrix; in vec4 x3d_Vertex; in vec4 aA; out vec4 vC;\nvoid main(){ vC = vec4(aA.xyz, 1.0); gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(x3d_Vertex.xyz * 0.01, 1.0); }"
VSL = VS.replace("in vec4 aA; ", "").replace("vC = vec4(aA.xyz, 1.0);", "vC = vec4(1.0);")
FS = "data:x-shader/x-fragment,#version 300 es\nprecision highp float;\nin vec4 vC; out vec4 x3d_FragColor;\nvoid main(){ x3d_FragColor = vC; }"
def shader(defname, vs, use=False):
    if use: return f"<ComposedShader USE='{defname}'/>"
    return f"<ComposedShader DEF='{defname}' language='GLSL'><ShaderPart type='VERTEX'><![CDATA[{vs}]]></ShaderPart><ShaderPart type='FRAGMENT'><![CDATA[{FS}]]></ShaderPart></ComposedShader>"
def quads(n_quads, first):
    r = random.Random(n_quads); pts, idx, att = [], [], []
    for q in range(n_quads):
        x, y = r.uniform(-500, 500), r.uniform(-300, 300); b = len(pts)
        for cx, cy in ((0, 0), (1, 0), (1, 1), (0, 1)): pts.append(f"{x + cx * 3:.2f} {y + cy * 3:.2f} 0"); att.append(f"{r.random():.3f} {r.random():.3f} {r.random():.3f} 0")
        idx.append(f"{b} {b+1} {b+2} {b+3} -1")
    return (f"<Shape><Appearance>{shader('Q', VS, not first)}</Appearance><IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(pts)}'/>"
            f"<FloatVertexAttribute name='aA' numComponents='4' value='{' '.join(att)}'/></IndexedFaceSet></Shape>")
def lines(n_lines, k, first):
    r = random.Random(n_lines); pts, idx = [], []
    for l in range(n_lines):
        b = len(pts); x, y = r.uniform(-500, 500), r.uniform(-300, 300)
        for j in range(k): pts.append(f"{x + j * 2:.2f} {y + (j % 3):.2f} 0")
        idx.append(" ".join(str(b + j) for j in range(k)) + " -1")
    return f"<Shape><Appearance>{shader('L', VSL, not first)}</Appearance><IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(pts)}'/></IndexedLineSet></Shape>"
def scene(name, body):
    open(f"bench/{name}.x3d", "w").write("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'><head><component name='Shaders' level='1'/></head><Scene>"
        "<Viewpoint position='0 0 15'/><TimeSensor DEF='Clock' loop='true' cycleInterval='10'/>" + body + "</Scene></X3D>\n")
for nv in (1000, 2000, 4000, 8000, 16000):
    scene(f"faces_{nv}", quads(nv // 4, True))
    scene(f"lines_{nv}", lines(nv // 17, 17, True))
scene("faces_16000_chunked16", "".join(quads(250, i == 0) for i in range(16)))
scene("lines_16000_chunked16", "".join(lines(59, 17, i == 0) for i in range(16)))
print(sorted(os.listdir("bench")))
