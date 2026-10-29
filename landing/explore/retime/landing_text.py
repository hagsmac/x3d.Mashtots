"""Text atlas for the Landing port: every label, caption and card line is a strip of pixels in one PNG (white, alpha only), so the scene needs no Text
node and no font in the browser (X_ITE has no Armenian font). Faces: Noto Serif Armenian and Lora (the deck's own, SIL OFL, in ./fonts), with fallbacks.
Strips are drawn at SC x resolution and placed 1 : 1 with the deck's 1920 x 1080 pixels by the label shader."""
from PIL import Image, ImageDraw, ImageFont

SC = 1.6                                      # render scale: 1.6 texels per deck pixel (big card glyphs are drawn at 1.0; the atlas is the scene's largest texture)
from fontTools.ttLib import TTFont
import os
HERE = os.path.dirname(os.path.abspath(__file__))
# the deck's own faces (Google Fonts, SIL OFL, downloaded to ./fonts): Noto Serif Armenian for the Armenian, Lora for the Latin.
# Georgia and Mshtakan stay as fallbacks for glyphs those two lack (Greek, arrows, math, a few transliteration letters).
FONTS = {"arm": (HERE + "/fonts/notoserifarmenian/NotoSerifArmenian[wdth,wght].ttf", 0, "noto"), "lat": (HERE + "/fonts/lora/Lora[wght].ttf", 0, "lora"),
         "geo": ("/System/Library/Fonts/Supplemental/Georgia.ttf", 0, None), "msh": ("/System/Library/Fonts/Supplemental/Mshtakan.ttc", 0, None),
         "sym": ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0, None), "sym2": ("/System/Library/Fonts/Apple Symbols.ttf", 0, None)}
_cache, _cmap = {}, {}
ARM_WGHT = 300                                   # the deck's .hy class; callers pass 200 (big glyph) or 400 (labels) where the deck does
def font(kind, size, wght=None):
    wght = wght or (ARM_WGHT if kind == "arm" else 400)
    key = (kind, size, wght)
    if key not in _cache:
        path, idx, var = FONTS[kind]; ft = ImageFont.truetype(path, int(round(size * SC)), index=idx)
        if var == "noto": ft.set_variation_by_axes([wght, 100])
        elif var == "lora": ft.set_variation_by_axes([min(700, max(400, wght))])
        _cache[key] = ft
    return _cache[key]
def has(kind, ch):
    if kind not in _cmap:
        path, idx, _ = FONTS[kind]
        tt = TTFont(path, fontNumber=idx, lazy=True); _cmap[kind] = set(tt.getBestCmap().keys())
    return ord(ch) in _cmap[kind]
def is_arm(ch): return 0x0530 <= ord(ch) <= 0x058F or ch in "։․"
SUBS = {"ₗ": ("l", -1), "ₖ": ("k", -1), "ᵀ": ("T", 1), "ˡ": ("l", 1), "⁽": ("(", 1), "⁺": ("+", 1), "⁾": (")", 1), "⁻": ("−", 1), "ᵝ": ("β", 1),
        "⁰": ("0", 1), "⁴": ("4", 1), "⁵": ("5", 1), "⁶": ("6", 1), "⁷": ("7", 1), "⁸": ("8", 1), "⁹": ("9", 1)}
def needs_fake(ch): return ch in SUBS and not any(has(k, ch) for k in ("lat", "geo", "sym", "sym2"))
def pick(ch, prefer):
    """the font for one character: Armenian script -> Noto Serif Armenian; else Lora if it covers the character, then Georgia, the symbol fonts, Mshtakan"""
    order = ["arm"] if is_arm(ch) else []
    order += [prefer, "lat", "geo", "sym", "sym2", "msh", "arm"]
    for k in order:
        if has(k, ch): return k
    return "lat"

class Atlas:
    def __init__(self, width=4096):
        self.W = width; self.items = []; self.rects = {}
    def add(self, key, text, size, track=0.0, upper=False, pad=0, tag=None, lat_size=None, bold=False, wght=400):
        """text strip. size = px at 1x. track = letter spacing in em. tag=(border_rgba, pad_x, pad_y) draws an outlined pill around it."""
        if key in self.rects: return self.rects[key][4:6]
        if upper: text = text.upper()
        lsz = lat_size or size
        runs, cur, kind = [], "", None
        prev = "lat"
        for ch in text:
            if needs_fake(ch): k = "fake"
            elif ch == " " or ch in "-–=()[]/,.:;0123456789·": k = "arm" if (prev == "arm" and ch not in "·") else ("lat" if ch == "·" else prev)
            else: k = pick(ch, "lat")
            if ch == "·": k = "lat"
            if k != kind and cur: runs.append((kind, cur)); cur = ""
            if k == "fake":                                        # one fake character per run
                if cur: runs.append((kind, cur)); cur = ""
                runs.append(("fake", ch)); kind = None; continue
            kind = k; cur += ch; prev = k if ch not in " -–=()[]/,.:;0123456789·" else prev
        if cur: runs.append((kind, cur))
        fa, fl = font("arm", size, wght), font("lat", lsz)
        asc = max(fa.getmetrics()[0], fl.getmetrics()[0]); desc = max(fa.getmetrics()[1], fl.getmetrics()[1])
        px = py = 0
        if tag: px, py = int(tag[1] * SC), int(tag[2] * SC)
        total = 0.0
        for kd, s in runs:
            if kd == "fake":
                bf = font("geo", lsz * 0.62) if has("geo", SUBS[s][0]) else font("lat", lsz * 0.62)
                total += bf.getlength(SUBS[s][0]) + track * size * SC; continue
            ft = font(kd, size if kd == "arm" else lsz, wght if kd == "arm" else None)
            for ch in s: total += ft.getlength(ch) + track * size * SC
        w = int(total) + int(2 * pad * SC) + 2 * px + 4; h = int(asc + desc) + int(2 * pad * SC) + 2 * py + 4
        im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
        x = float(pad * SC + px + 2); y = pad * SC + py + 2 + asc
        for kd, s in runs:
            if kd == "fake":
                base, sgn = SUBS[s]; ft = font("geo", lsz * 0.62) if has("geo", base) else font("lat", lsz * 0.62)
                d.text((x, y - sgn * 0.36 * lsz * SC), base, font=ft, fill=255, anchor="ls"); x += ft.getlength(base) + track * size * SC; continue
            ft = font(kd, size if kd == "arm" else lsz, wght if kd == "arm" else None)
            for ch in s:
                d.text((x, y), ch, font=ft, fill=255, anchor="ls"); x += ft.getlength(ch) + track * size * SC
        if tag:
            d.rounded_rectangle((1, 1, w - 2, h - 2), radius=int(4 * SC), outline=255, width=max(1, int(round(SC))))
        self.items.append((key, im)); self.rects[key] = [0, 0, 0, 0, w / SC, h / SC, asc / SC]
        return w / SC, h / SC
    def add_image(self, key, im):
        if key in self.rects: return
        self.items.append((key, im.convert("L"))); self.rects[key] = [0, 0, 0, 0, im.width / SC, im.height / SC, 0]
    def build(self, path):
        tot = sum(im.width * im.height for _, im in self.items)
        import os
        if os.environ.get('ATLAS_DEBUG'):
            big = sorted(self.items, key=lambda kv: -kv[1].width * kv[1].height)[:6]
            print('atlas items', len(self.items), 'texels %.1fM' % (tot / 1e6), [(k, im.size) for k, im in big])
            import re, collections
            cat = collections.Counter()
            for k, im in self.items: cat[re.sub(r'[0-9_.]+.*$', '', k)[:8]] += im.width * im.height
            print({k: round(v / 1e6, 2) for k, v in cat.most_common(14)})
        # shelf packing, tallest first
        order = sorted(self.items, key=lambda kv: -kv[1].height)
        x = y = shelf = 0; place = {}
        for key, im in order:
            if x + im.width + 2 > self.W: x, y, shelf = 0, y + shelf + 2, 0
            place[key] = (x, y); x += im.width + 2; shelf = max(shelf, im.height)
        H = y + shelf + 2                                   # NPOT is fine in WebGL2; no power-of-two padding
        atlas = Image.new("L", (self.W, H), 0)
        for key, im in self.items: atlas.paste(im, place[key])
        rgba = Image.new("RGBA", (self.W, H), (255, 255, 255, 0)); rgba.putalpha(atlas)
        rgba.save(path, optimize=True)
        for key, im in self.items:
            x0, y0 = place[key]; r = self.rects[key]
            r[0], r[1], r[2], r[3] = x0 / self.W, y0 / H, (x0 + im.width) / self.W, (y0 + im.height) / H      # top-origin v
        return self.W, H
    def uv(self, key): return self.rects[key][:4]
    def size(self, key): return self.rects[key][4:6]
