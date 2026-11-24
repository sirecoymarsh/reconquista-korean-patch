@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ChronicleProto.ps1"
if errorlevel 1 pause
