@echo off
echo Starting Polymarket Sentinel...
echo --------------------------------------------------------------------------------
echo You can see logs here, and it will also be saved to polymarket.log.
echo To STOP this bot from running, simply close this window or press Ctrl+C.
echo --------------------------------------------------------------------------------
"%~dp0\.venv\Scripts\python.exe" "%~dp0\main.py"
