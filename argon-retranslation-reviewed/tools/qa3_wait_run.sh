#!/usr/bin/env bash
# 숨은 시험 3회차: 다른 세션(레콘키스타 패치 최종 검수)의 바퀴가 끝나기를 기다렸다가 돌린다.
# 시작 조건(그쪽 요청): chain_ab.json 항목 수가 0보다 늘어난 뒤 + 레콘키스타 게임 0개가 20초 이상 이어짐
# 끝나면 HOLD 를 지운다(그쪽 바퀴가 이어 감).
cd "$(dirname "$0")/.."
A=/p/AI/Codex/projects/reconquista_flowchart_20261024/qa/release-audit-20261121
HOLD=$A/HOLD; CH=$A/chain_ab.json; LOG=work/qa3_wait.log
[ -f "$HOLD" ] || echo "argon loanword hidden test (results_reviewed_20261121), $(date)" > "$HOLD"
cnt(){ powershell.exe -NoProfile -Command "@(Get-Process | Where-Object { \$_.Path -and \$_.Path -match 'reconquista_flowchart|api-carbon-argon' -and \$_.ProcessName -notmatch 'python|powershell|bash' }).Count" 2>/dev/null | tr -d '\r'; }
entries(){ [ -f "$CH" ] && python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(len(d))" "$CH" 2>/dev/null || echo 0; }
echo "start wait $(date +%T)" > $LOG
zero=0; started=0
for i in $(seq 1 360); do          # 최대 60분
  e=$(entries); c=$(cnt)
  if [ "${e:-0}" -gt 0 ] && [ "$c" = "0" ]; then zero=$((zero + 5)); else zero=0; fi
  if [ $zero -ge 20 ]; then started=1; break; fi
  sleep 5
done
echo "entries=$e games=$c zero_for=${zero}s started=$started at $(date +%T)" >> $LOG
if [ $started = 1 ]; then
  python -I tools/qa_argon.py > work/qa_run3.log 2>&1; echo "qa exit $? at $(date +%T)" >> $LOG
else
  echo "TIMEOUT - not started" >> $LOG
fi
rm -f "$HOLD"; echo "HOLD removed $(date +%T)" >> $LOG
cat $LOG
