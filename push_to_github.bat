@echo off
REM ============================================================
REM CyberSentinel AI — GitHub Setup Script
REM Run this from INSIDE C:\Users\Salman\cybersentinel-ai
REM (double-click it, or run "push_to_github.bat" in cmd)
REM ============================================================

echo.
echo === Step 1: Checking Git is installed ===
git --version
if errorlevel 1 (
    echo.
    echo Git is not installed or not on PATH.
    echo Download it from https://git-scm.com/download/win , install with
    echo default options, then run this script again.
    pause
    exit /b 1
)

echo.
echo === Step 2: Creating .gitignore ===
(
echo __pycache__/
echo *.pyc
echo mlruns/
echo mlflow.db
echo *.log
echo .venv/
echo venv/
echo .DS_Store
) > .gitignore
echo .gitignore created.

echo.
echo === Step 3: Initializing git repository ===
if not exist ".git" (
    git init
) else (
    echo Git repo already initialized, skipping.
)

echo.
echo === Step 4: Staging all files ===
git add .

echo.
echo === Step 5: Committing ===
git commit -m "Initial commit: CyberSentinel AI - 4-module threat detection platform"

echo.
echo === Step 6: Connect to GitHub ===
echo Before continuing, go to https://github.com/new and create a new,
echo EMPTY repository (no README, no .gitignore, no license added there).
echo Then copy its URL — it looks like:
echo   https://github.com/YOUR_USERNAME/cybersentinel-ai.git
echo.
set /p REPO_URL="Paste your GitHub repository URL here and press Enter: "

git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%
git branch -M main

echo.
echo === Step 7: Pushing to GitHub ===
echo A browser window may open asking you to sign in and authorize —
echo do that if prompted, then come back here.
echo.
git push -u origin main

echo.
echo ============================================================
echo Done. Go to your repository page on github.com to verify
echo everything uploaded correctly.
echo ============================================================
pause
