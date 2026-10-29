# Stage 2, run headless:  Blender -b --python tessellate_blender.py
# Uses Blender's own polygon tessellator (handles holes). Input contours.json, output tris.json: per glyph, 2D verts + triangle index triples.
import json, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
d = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
G = json.load(open(os.path.join(d, "contours.json")))
res = []
for g in G:
    polys = [[Vector((x, y, 0.0)) for x, y in c] for c in g["contours"]]
    tris = tessellate_polygon(polys)
    flat = [p for c in polys for p in c]
    res.append(dict(codepoint=g["codepoint"], advance=g["advance"], contours=g["contours"],
                    verts=[[p.x, p.y] for p in flat], tris=[list(t) for t in tris]))
json.dump(res, open(os.path.join(d, "tris.json"), "w"))
print("TESSELLATED", [len(r["tris"]) for r in res])
