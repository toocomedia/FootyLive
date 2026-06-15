@echo off
echo =========================================
echo FootyLive GitHub Uploader
echo =========================================
echo.

if not exist .git (
    echo Initializing git repository...
    git init
)

echo Adding all files...
git add .

echo Committing files...
git commit -m "Update FootyLive"

echo Renaming branch to main...
git branch -M main

echo.
set /p REPO_URL="Please enter your new GitHub repository URL (e.g., https://github.com/Username/FootyLive.git): "

if "%REPO_URL%"=="" (
    echo Error: Repository URL cannot be empty.
    pause
    exit /b 1
)

echo.
echo Linking to %REPO_URL%...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Pushing code to GitHub...
git push -u origin main --force

echo.
echo =========================================
echo Done! If there were no errors above, your code is now on GitHub!
echo =========================================
pause
