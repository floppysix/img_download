@echo off
REM 在 video_download conda 环境中运行 Python 脚本
REM 使用方法: run_video_download.bat example.py

chcp 65001 >nul
call activate video_download
python %*
deactivate
