#!/bin/sh
# usage: ./mkstill.sh REAL_SEC [camx camy camz]   (ACT=1 ./mkstill.sh ACT_SEC ...  takes the deck's act time instead)  -> still_SEC.x3d
t=$1; shift
flag=--freeze; [ -n "$ACT" ] && flag=--act
if [ $# -ge 3 ]; then python3 make_landing.py $flag $t --cam $1 $2 $3 --out still_$t.x3d >/dev/null; else python3 make_landing.py $flag $t --out still_$t.x3d >/dev/null; fi
