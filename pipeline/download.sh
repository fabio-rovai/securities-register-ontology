#!/bin/bash
# Resumable downloader for the three bulk inputs. GLEIF drops large transfers
# (no Range support on some endpoints) so every file loops with curl -C - until
# the size stops growing and the archive tests clean.
set -u
cd "$(dirname "$0")/../data"
UA="Kampakis and Co Ltd research fabio@thetesseractacademy.com"

fetch () { # url outfile
  local url="$1" out="$2" tries=0
  while [ $tries -lt 30 ]; do
    curl -sS -C - -L -H "User-Agent: $UA" "$url" -o "$out" && break
    tries=$((tries+1)); sleep 5
  done
  if [[ "$out" == *.zip ]]; then unzip -tq "$out" >/dev/null 2>&1 && echo "OK $out $(stat -f%z "$out")" || echo "BAD $out"; else echo "DONE $out $(stat -f%z "$out")"; fi
}

fetch "https://isinmapping.gleif.org/api/v2/isin-lei/d6a9b6d7-f625-44c7-ad14-acdb1245e7bb/download" isin-lei.zip &
fetch "https://goldencopy.gleif.org/storage/golden-copy-files/2026/08/17/1264880/20260817-0800-gleif-goldencopy-lei2-golden-copy.csv.zip" lei2.csv.zip &
fetch "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip" submissions.zip &
wait
echo "ALL DOWNLOADS FINISHED"
ls -la
