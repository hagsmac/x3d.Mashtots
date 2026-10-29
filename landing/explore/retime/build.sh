#!/bin/sh
# Builds the re-timed Landing into ./build (never the Landing folder):  PRESET=graph-expanded ./build.sh   (presets: see presets.json)
# Needs ../data-graph/out/graph.json (python3 ../data-graph/grabar_graph.py). About a minute.
set -e
cd "$(dirname "$0")"
python3 patch.py
python3 check_timeline.py > /dev/null
[ -e fonts ] || ln -s ../../fonts fonts
mkdir -p build/scratch build/glyphs
cp ../../scratch/landing.json build/scratch/landing.json
[ -e build/assets_src ] || ln -s ../../../assets_src build/assets_src
PRESET=${PRESET:-graph-expanded}
cd build && PRESET=$PRESET python3 ../make_landing_retimed.py --out "mashtots-landing-$PRESET.x3d"
cp sections.json "sections-$PRESET.json"
