#!/usr/bin/env python3
"""Helpers for the Mashtots PoC notebook (and its local dry run with MP_LOCAL=1).

Pattern taken from ../jepa-bridge: every check that imports torch runs in a fresh process (pip may change packages under a live session);
heavy work runs as scripts in subprocesses whose output streams into the cell; every step is safe to run twice.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402

LOCAL = C.LOCAL
PIP = ["tokenizers>=0.21", "tiktoken>=0.8", "pyarrow>=15", "huggingface_hub>=0.30", "regex", "scipy", "matplotlib"]
CODE_FILES = ["mp_common.py", "mp_data.py", "mp_tok.py", "mp_model.py", "mp_train.py", "mp_eval.py", "mp_analyze.py", "mp_export.py", "nb_helpers.py"]


def sh(cmd, cwd=None, env=None, check=True, quiet=False):
    p = subprocess.Popen(cmd if isinstance(cmd, list) else ["bash", "-c", cmd], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1)
    for line in p.stdout:
        if not quiet:
            print(line, end="")
    rc = p.wait()
    if check and rc:
        raise RuntimeError(f"command failed ({rc}): {cmd if isinstance(cmd, str) else ' '.join(map(str, cmd))}")
    return rc


def ok(flag, msg, hint=""):
    print(("✅ " if flag else "❌ ") + msg + ("" if flag or not hint else f"\n   -> {hint}"))
    return bool(flag)


def _probe(code, timeout=900):
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _last(text, n=300):
    lines = [x for x in (text or "").strip().splitlines() if x.strip()]
    return lines[-1][:n] if lines else ""


def install():
    if LOCAL:
        print("local dry run: no pip")
        return
    sh([sys.executable, "-m", "pip", "install", "-q", *PIP])          # torch is Colab's own build: never reinstalled here


def env_report():
    print("python", platform.python_version(), "|", platform.platform())
    print("cpus", os.cpu_count(), "| disk free GB", round(shutil.disk_usage("/").free / 1e9, 1))
    rc, out, err = _probe(
        "import importlib.metadata as md\n"
        "for m in ('torch','tokenizers','tiktoken','pyarrow','huggingface_hub','numpy','scipy'):\n"
        "    try: print(m, md.version(m))\n"
        "    except Exception as e: print(m, 'missing')\n"
        "import torch\n"
        "if torch.cuda.is_available():\n"
        "    p = torch.cuda.get_device_properties(0); print('GPU', p.name, '%.0f GiB' % (p.total_memory/2**30), 'sm_%d%d' % (p.major, p.minor), 'cuda', torch.version.cuda)\n"
        "else: print('GPU: none visible to torch')\n")
    print(out, end="")
    if rc:
        print(_last(err))


def doctor(src, root, drive_out=None, need_gb=1.0):
    """Every dependency in one pass, each in a fresh process. ALL GOOD or a list of what to send to Claude."""
    src, root = pathlib.Path(src), pathlib.Path(root)
    res = []
    if LOCAL:
        res.append(ok(True, "local dry run: GPU checks skipped (CPU, tiny model)"))
    else:
        rc, out, err = _probe("import torch; assert torch.cuda.is_available(); a=torch.randn(4096,4096,device='cuda',dtype=torch.bfloat16); "
                              "import time; torch.cuda.synchronize(); t=time.time(); [a@a for _ in range(50)]; torch.cuda.synchronize(); "
                              "print('%s, bf16 matmul %.0f TFLOP/s' % (torch.cuda.get_device_name(0), 50*2*4096**3/(time.time()-t)/1e12))")
        res.append(ok(rc == 0, "GPU + bf16: " + (out.strip() or _last(err)), "Runtime > Change runtime type > G4, then run from cell 1"))
    code = (f"import sys; sys.path.insert(0, {str(src)!r}); import torch, mp_model as M\n"
            "dev = 'cuda' if torch.cuda.is_available() else 'cpu'\n"
            "cfg = M.Config(vocab=512, d=128, L=2, H=4, seq=256); m = M.GPT(cfg).to(dev)\n"
            "x = torch.randint(0, 512, (4, 256), device=dev)\n"
            "f = torch.compile(m) if dev == 'cuda' else m\n"
            "opt = torch.optim.AdamW(m.parameters(), 1e-3); l0 = None\n"
            "for i in range(30):\n"
            "    with torch.autocast(device_type=dev.split(':')[0], dtype=torch.bfloat16, enabled=dev=='cuda'):\n"
            "        loss = f(x, x)['loss']\n"
            "    loss.backward(); opt.step(); opt.zero_grad(); l0 = l0 or float(loss)\n"
            "a = m(x[:1, :64], need_attn=True)['attn'][0]; s = a.sum(-1)\n"
            "assert torch.allclose(s, torch.ones_like(s), atol=1e-3)\n"
            "print('loss %.2f -> %.2f in 30 steps, compile %s, attention rows sum to 1' % (l0, float(loss), dev == 'cuda'))\n")
    rc, out, err = _probe(code)
    res.append(ok(rc == 0 and "->" in out, "model: forward, backward, SDPA, torch.compile, explicit attention: " + (out.strip() or _last(err)),
                  "copy the message to Claude"))
    code = (f"import sys; sys.path.insert(0, {str(src)!r}); import mp_tok as T, mp_common as C\n"
            "docs = ['Ճանաչել զիմաստութիւն եւ զխրատ, իմանալ զբանս հանճարոյ. ' * 3, 'Հայաստանի Հանրապետությունը գտնվում է Հարավային Կովկասում։ 2026 թ.', "
            "'Western: Կ՚ուզեմ որ գաս, ըսաւ ան։ ☃ Ü ﬓ']\n"
            "mo = T.Morph(T.HAND_SUFFIXES)\n"
            "bad = 0\n"
            "for arm in ['bpe', 'mashtots', 'bpe_morph', 'mashtots_nomorph']:\n"
            "    tok = T.build_tokenizer(arm, 400, lambda: iter(docs * 20), mo)\n"
            "    import tempfile, os; p = os.path.join(tempfile.mkdtemp(), arm + '.json'); tok.save(p)\n"
            "    e = T.Encoder(arm, p, mo); bad += e.roundtrip(docs + list(C.PROBES.values()))\n"
            "print('round-trip failures', bad)\n"
            "assert bad == 0\n")
    rc, out, err = _probe(code)
    res.append(ok(rc == 0, "tokenizers: 4 arms train and round-trip exactly (Armenian, Western, Grabar, digits, rare characters): " + (out.strip() or _last(err)),
                  "copy the message to Claude"))
    if LOCAL:
        res.append(ok(True, "network: skipped in the local dry run"))
    else:
        rc, out, err = _probe("import urllib.request, json\n"
                              "d = json.load(urllib.request.urlopen('https://huggingface.co/api/datasets/COPA-AI/armweb', timeout=30)); print('HF ok', d['id'])\n"
                              "urllib.request.urlopen('https://raw.githubusercontent.com/UniversalDependencies/UD_Armenian-ArmTDP/r2.18/README.md', timeout=30); print('GitHub ok')\n"
                              "import tiktoken; tiktoken.get_encoding('o200k_base'); print('tiktoken ok')\n")
        res.append(ok(rc == 0, "network: Hugging Face, GitHub, tiktoken: " + " / ".join(out.split("\n")).strip(" /"), _last(err)))
    free = shutil.disk_usage(str(root if root.exists() else "/")).free / 1e9
    res.append(ok(free > need_gb, f"disk: {free:.0f} GB free, about {need_gb:.0f} GB needed for this profile"))
    if drive_out:
        try:
            pathlib.Path(drive_out).mkdir(parents=True, exist_ok=True)
            t = pathlib.Path(drive_out) / ".write_test"
            t.write_text("ok")
            t.unlink()
            res.append(ok(True, f"Drive writable: {drive_out}"))
        except Exception as exc:
            res.append(ok(False, f"Drive not writable: {exc}", "run the Drive cell again and allow access"))
    print("\nALL GOOD" if all(res) else "\nNOT ALL GOOD: copy the ❌ lines to Claude before going on")
    return all(res)


# ------------------------------------------------------------------------------------------------ the grid and its cost
def profile_cfg(profile):
    return dict(C.LOCAL_PROFILE) if LOCAL else dict(C.PROFILES[profile])


def grid(profile, arms_override="", sizes_override="", grabar=True):
    """The runs of a profile, smallest first; within a size bpe, mashtots, bytes (so a budget cut drops bytes at the top size first)."""
    P = profile_cfg(profile)
    arms = [a for a in ("bpe", "mashtots", "bytes") if a in (arms_override.split(",") if arms_override else P["arms"])]
    sizes = sizes_override.split(",") if sizes_override else P["sizes"]
    specs = []
    for s in sizes:
        T = C.train_tokens(s, P)
        for a in arms:
            specs.append(dict(arm=a, size=s, grabar=False, tokens=T, id=C.run_id(a, s)))
        if grabar and s in P["grabar_sizes"] and "bpe" in arms:
            specs.append(dict(arm="bpe", size=s, grabar=True, tokens=T, id=C.run_id("bpe", s, True)))
    return specs


def bench(src, data, specs, compile_=True, steps=20):
    out = {}
    for key in sorted({(s["arm"], s["size"]) for s in specs}, key=lambda k: (C.non_embedding_params(k[1]), k[0])):
        arm, size = key
        d = pathlib.Path(data) / "bench" / f"{arm}-{size}"
        if not (d / "bench.json").exists():
            sh([sys.executable, str(pathlib.Path(src) / "mp_train.py"), "--root", str(data), "--arm", arm, "--size", size, "--out", str(d),
                "--bench-steps", str(steps if not LOCAL else 3), "--device", "cpu" if LOCAL else "cuda"] + (["--compile"] if compile_ and not LOCAL else []))
        out[key] = json.loads((d / "bench.json").read_text())
    return out


def project(specs, bench_res, units_per_hour=0.0, overhead_min=3.0):
    rows, total_h = [], 0.0
    print(f"{'run':<16}{'tokens':>10}{'tok/s':>10}{'hours':>8}")
    for s in specs:
        b = bench_res.get((s["arm"], s["size"]))
        h = (s["tokens"] / b["tok_per_s"] / 3600 if b else float("nan")) + overhead_min / 60
        total_h += h
        rows.append(dict(s, hours=h))
        print(f"{s['id']:<16}{s['tokens'] / 1e6:>9.0f}M{(b['tok_per_s'] / 1e3 if b else 0):>9.0f}k{h:>8.2f}")
    print(f"{'total':<16}{'':>20}{total_h:>8.2f} h" + (f"  = {total_h * units_per_hour:.0f} compute units at {units_per_hour} units/h" if units_per_hour else
                                                      "  (enter UNITS_PER_HOUR in cell 2 for the cost in units)"))
    print("Estimate: measured throughput x planned tokens, plus about 3 minutes of scoring per run. Data and tokenizer cells are extra.")
    return rows, total_h


def train_grid(src, data, specs, runs_dir, drive_runs=None, max_hours=0.0, compile_=True):
    stop_at = time.time() + max_hours * 3600 if max_hours else 0
    done, left = [], []
    for s in specs:
        out = pathlib.Path(runs_dir) / s["id"]
        if (out / "done.json").exists() or (drive_runs and (pathlib.Path(drive_runs) / s["id"] / "done.json").exists()):
            if not (out / "done.json").exists() and drive_runs:
                shutil.copytree(pathlib.Path(drive_runs) / s["id"], out, dirs_exist_ok=True)
            done.append(s["id"])
            continue
        if stop_at and time.time() > stop_at - 300:
            left.append(s["id"])
            continue
        cmd = [sys.executable, str(pathlib.Path(src) / "mp_train.py"), "--root", str(data), "--arm", s["arm"], "--size", s["size"], "--out", str(out),
               "--tokens", str(s["tokens"]), "--device", "cpu" if LOCAL else "cuda"]
        cmd += ["--grabar"] if s["grabar"] else []
        cmd += ["--compile"] if compile_ and not LOCAL else []
        cmd += ["--mirror", str(pathlib.Path(drive_runs) / s["id"])] if drive_runs else []
        cmd += ["--stop-at", str(stop_at)] if stop_at else []
        rc = sh(cmd, check=False)
        if rc == 4:
            print(f"MAX_HOURS reached during {s['id']}: its checkpoint is saved; run this cell again (or raise MAX_HOURS) to continue")
            left += [x["id"] for x in specs[specs.index(s):]]
            break
        if rc:
            raise RuntimeError(f"run {s['id']} failed (exit {rc}); copy the lines above to Claude")
        done.append(s["id"])
    print(f"\nfinished: {len(done)} of {len(specs)} runs" + (f"; not started or unfinished: {', '.join(left)}" if left else ""))
    return done, left


# ------------------------------------------------------------------------------------------------ freeze, checkpoints
def freeze(src, data, profile, extra):
    src, data = pathlib.Path(src), pathlib.Path(data)
    shutil.copy(src / "PREREG.md", data / "PREREG.md")
    h = {n: C.sha256_file(src / n) for n in ["PREREG.md"] + CODE_FILES}
    rec = dict(frozen=C.stamp(), profile=profile, version=C.VERSION, sha256=h, **extra)
    if (data / "PREREG.sha256").exists():
        old = json.loads((data / "PREREG.sha256").read_text())
        if old["sha256"] != h:
            print("⚠️  the code or PREREG.md changed since the first freeze of this data folder; both records are kept (DEVIATIONS.md)")
            (data / f"PREREG.sha256.{int(time.time())}").write_text(json.dumps(old, indent=1))
        else:
            print("FROZEN (unchanged since", old["frozen"] + ")")
            return old
    (data / "PREREG.sha256").write_text(json.dumps(rec, indent=1))
    print("FROZEN", rec["frozen"])
    for n, v in h.items():
        print(f"  {v[:12]}  {n}")
    return rec


def checkpoint(src_dir, drive_out, names):
    if not drive_out:
        return
    src_dir, dst = pathlib.Path(src_dir), pathlib.Path(drive_out)
    dst.mkdir(parents=True, exist_ok=True)
    for n in names:
        p = src_dir / n
        if p.is_dir():
            shutil.copytree(p, dst / n, dirs_exist_ok=True)
        elif p.exists():
            shutil.copy(p, dst / n)
    print("saved to Drive:", ", ".join(n for n in names if (src_dir / n).exists()))


def show(paths):
    try:
        from IPython.display import Image, display
        for p in paths:
            if pathlib.Path(p).exists():
                print(pathlib.Path(p).name)
                display(Image(filename=str(p)))
    except Exception as exc:
        print("(inline display unavailable)", exc)
