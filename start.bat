@echo off
chcp 65001 > nul
setlocal

echo [Stock Tracking App] 起動中...
echo.

cd /d %~dp0
call .venv\Scripts\activate

echo Flaskサーバーを起動しています (ポート 5000)...
echo アプリケーションを終了するには Ctrl+C を押してください...
echo.

python app.py
