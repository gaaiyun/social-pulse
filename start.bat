@echo off
chcp 65001 >nul
echo ========================================
echo   社交媒体分析平台 - 启动器
echo ========================================
echo.

cd /d "%~dp0"

echo 检查依赖...
python -c "import streamlit, pandas, numpy, plotly, snownlp" 2>nul
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

echo.
echo 启动 Streamlit 应用...
echo 浏览器将自动打开 http://localhost:8501
echo 按 Ctrl+C 停止应用
echo.

streamlit run dashboard.py
