#!/bin/sh
# One command: start the slide show's server (if it is not already running) and open it.
#   ./run.sh            the expanded measured cut with the control deck open
#   ./run.sh approved   the approved cut (mp3 score)        ./run.sh slide1   slide 1
#   ./run.sh score      the score lab                       ./run.sh stop     stop the server this script started
#   PORT=8411 ./run.sh  another port (default 8410)
cd "$(dirname "$0")" || exit 1
PORT="${PORT:-8410}"; BASE="http://127.0.0.1:$PORT"
command -v node >/dev/null 2>&1 || { echo "needs Node 18 or newer (https://nodejs.org)"; exit 1; }
case "${1:-show}" in
  show)     URL="$BASE/stage.html?deck=1" ;;
  approved) URL="$BASE/index.html?standalone=1" ;;
  slide1)   URL="$BASE/index.html?slide1&nav&standalone=1" ;;
  score)    URL="$BASE/score/index.html" ;;
  stop)     if [ -f .serve.pid ]; then kill "$(cat .serve.pid)" 2>/dev/null; rm -f .serve.pid; echo "server stopped"; else echo "no server started by this script"; fi; exit 0 ;;
  *)        echo "usage: ./run.sh [show|approved|slide1|score|stop]"; exit 1 ;;
esac
if ! curl -s -o /dev/null "$BASE/stage.html"; then
  nohup node serve.mjs "$PORT" > serve.log 2>&1 &
  echo $! > .serve.pid
  i=0; until curl -s -o /dev/null "$BASE/stage.html"; do i=$((i + 1)); [ $i -gt 40 ] && { echo "the server did not start: see serve.log"; exit 1; }; sleep 0.25; done
fi
echo "$URL"
case "$(uname)" in
  Darwin) if [ -d "/Applications/Google Chrome.app" ]; then open -a "Google Chrome" "$URL"; else open "$URL"; fi ;;
  *) (xdg-open "$URL" >/dev/null 2>&1 &) || echo "open $URL in a browser" ;;
esac
