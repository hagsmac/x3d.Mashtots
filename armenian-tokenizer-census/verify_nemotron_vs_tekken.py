"""Check that Nemotron Nano 9B v2 and Mistral Nemo (Tekken) tokenizers are the same BPE. Usage: python3 -I verify_nemotron_vs_tekken.py DATA_DIR"""
import json, sys
from tokenizers import Tokenizer
D = sys.argv[1]
A, B = Tokenizer.from_file(f"{D}/tok-nemotron-nano-9b-v2/tokenizer.json"), Tokenizer.from_file(f"{D}/tok-mistral-nemo/tokenizer.json")
va, vb = A.get_vocab(), B.get_vocab()
print("tokens only in nemotron:", sorted(set(va) - set(vb))); print("tokens only in mistral:", sorted(set(vb) - set(va)))
print("shared tokens with different ids:", sum(va[t] != vb[t] for t in set(va) & set(vb)))
ja, jb = (json.load(open(f"{D}/tok-{n}/tokenizer.json"))["model"]["merges"] for n in ("nemotron-nano-9b-v2", "mistral-nemo"))
norm = lambda m: [" ".join(x) if isinstance(x, list) else x for x in m]   # one file stores merges as pairs, the other as strings
print("merges identical (same order):", norm(ja) == norm(jb), len(ja))
