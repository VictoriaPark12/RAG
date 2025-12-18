# GPU QLoRA 모드로 백엔드 시작 스크립트
# torch313 환경의 Python을 직접 호출 (conda activate 우회)
# 이미 8000 포트를 쓰는 백엔드가 있으면 자동으로 종료(중복 실행 방지)
$existing = netstat -ano | Select-String ":8000\\s+.*LISTENING\\s+(\\d+)"
if ($existing) {
  $pid = ($existing.Matches[0].Groups[1].Value)
  if ($pid) {
    Write-Host "[BOOT] killing existing server on :8000 PID=$pid"
    try { taskkill /F /PID $pid | Out-Null } catch {}
    Start-Sleep -Seconds 1
  }
}

$env:USE_QLORA = "1"
$env:QLORA_BASE_MODEL_PATH = "C:\Users\hi\Documents\devic\langchain\app\model\midm"
$env:PYTHONUNBUFFERED = "1"
Set-Location app
& "C:\Users\hi\anaconda3\envs\torch313\python.exe" main.py

