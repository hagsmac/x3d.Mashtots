#!/usr/bin/env python3
"""usage: x3d_mcp/.venv/bin/python validate_one.py FILE.x3d [...]  -- XSD + semantic validation through the x3d_mcp server (stdio)."""
import asyncio, json, re, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
REPO = "/Users/handshake/Projects/x3d/x3d_mcp"
TXT = lambda r: "".join(getattr(c, "text", "") for c in r.content)
async def main(files):
    params = StdioServerParameters(command=sys.executable, args=["-m", "src.server"], cwd=REPO)
    async with stdio_client(params, errlog=open("/dev/null", "w")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for fn in files:
                raw = open(fn, encoding="utf-8").read()
                v = json.loads(TXT(await s.call_tool("validate_x3d", {"content": raw, "encoding": "xml"})))
                t = TXT(await s.call_tool("validate_semantic", {"content": raw}))
                m = re.search(r"Found (\d+) error\(s\), (\d+) warning\(s\), (\d+) info", t)
                print(fn, "| XSD valid:", v.get("valid"), (v.get("errors") or [])[:3], "| semantic:", m.groups() if m else ("All Clear" if "All Clear" in t else t[:300]))
                if m and (int(m.group(1)) or int(m.group(2))): print(t[:1500])
asyncio.run(main(sys.argv[1:]))
