#!/usr/bin/env python3
"""Write participation/annotate.html from annotate.template.html with a small demo batch inside (12 sentences + 4 words from a batch file).

usage: python3 -I make_form.py BATCH.json   (the notebook writes annotation/batch_b001.json; the demo here came from the local dry run: UD text, CC BY-SA)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(sys.argv[1], encoding="utf-8"))
ds = [x for x in b["items"] if x["task"] == "dialect_spelling" and "-q" not in x["id"]][:12]
mo = [x for x in b["items"] if x["task"] == "morph"][:4]
demo = dict(batch="demo", created=b["created"], items=[dict(x, id=f"demo-{k:02d}") for k, x in enumerate(ds + mo)],
            text_licences="UD Armenian treebanks, CC BY-SA 4.0", note="demo only: answers to the demo are not used")
html = open(os.path.join(HERE, "annotate.template.html"), encoding="utf-8").read().replace("/*DEMO*/null", json.dumps(demo, ensure_ascii=False))
open(os.path.join(HERE, "annotate.html"), "w", encoding="utf-8").write(html)
print("wrote annotate.html with", len(demo["items"]), "demo items")
