@echo off
:: ============================================================================
:: Build One2lvOS.exe - Standalone Launcher
:: ============================================================================
:: Creates a Windows executable for One2lvOS using PyInstaller
:: ============================================================================

title Building One2lvOS.exe

color 0B
cls

echo.
echo ========================================================================
echo    ONE2LVOS - Executable Builder
echo ========================================================================
echo.
echo    This will create a standalone One2lvOS.exe launcher
echo.
echo ========================================================================
echo.

timeout /t 2 /nobreak >nul

set BUILD_DIR=%CD%
set INSTALL_DIR=%USERPROFILE%\One2lvOS

:: Check if in One2lvOS directory
if exist "one2lvos_launcher.py" (
    echo [1/5] Found launcher script [OK]
) else (
    echo [1/5] Looking for One2lvOS installation...
    if exist "%INSTALL_DIR%\one2lvos_launcher.py" (
        cd /d "%INSTALL_DIR%"
        echo    ^> Found at: %INSTALL_DIR%
    ) else (
        echo    ^> ERROR: one2lvos_launcher.py not found
        echo    ^> Please run the installer first
        pause
        exit /b 1
    )
)

:: Check Python
echo.
echo [2/5] Checking Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo    ^> ERROR: Python not found
    pause
    exit /b 1
)
echo    ^> Python found [OK]

:: Install PyInstaller
echo.
echo [3/5] Installing PyInstaller...
python -m pip install pyinstaller --quiet --upgrade
if %errorLevel% neq 0 (
    echo    ^> ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)
echo    ^> PyInstaller installed [OK]

:: Clean previous builds
echo.
echo [4/5] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "One2lvOS.spec" del /q One2lvOS.spec
echo    ^> Cleaned [OK]

:: Build executable
echo.
echo [5/5] Building One2lvOS.exe...
echo    ^> This may take 2-3 minutes...
echo.

python -m PyInstaller ^
    --onefile ^
    --console ^
    --name "One2lvOS" ^
    --add-data "one2lvos_launcher.py;." ^
    --hidden-import=subprocess ^
    --hidden-import=socket ^
    --hidden-import=webbrowser ^
    --hidden-import=threading ^
    --hidden-import=signal ^
    one2lvos_launcher.py

if %errorLevel% neq 0 (
    echo.
    echo    ^> ERROR: Build failed
    pause
    exit /b 1
)

:: Verify build
if exist "dist\One2lvOS.exe" (
    echo.
    echo ========================================================================
    echo    BUILD SUCCESSFUL!
    echo ========================================================================
    echo.
    echo    Executable created: dist\One2lvOS.exe
    echo    Size:
    dir "dist\One2lvOS.exe" | findstr One2lvOS.exe
    echo.

    :: Copy to desktop
    echo    Copying to Desktop...
    copy "dist\One2lvOS.exe" "%USERPROFILE%\Desktop\One2lvOS.exe" >nul 2>&1
    if exist "%USERPROFILE%\Desktop\One2lvOS.exe" (
        echo    ^> Desktop shortcut created [OK]
    )

    :: Copy to installation directory
    if exist "%INSTALL_DIR%" (
        echo    Copying to installation directory...
        copy "dist\One2lvOS.exe" "%INSTALL_DIR%\One2lvOS.exe" >nul 2>&1
        if exist "%INSTALL_DIR%\One2lvOS.exe" (
            echo    ^> Copied to %INSTALL_DIR% [OK]
        )
    )

    echo.
    echo ========================================================================
    echo    USAGE
    echo ========================================================================
    echo.
    echo    Double-click One2lvOS.exe to launch the system
    echo.
    echo    Locations:
    echo       - Desktop: %USERPROFILE%\Desktop\One2lvOS.exe
    echo       - Build:   %CD%\dist\One2lvOS.exe

    if exist "%INSTALL_DIR%\One2lvOS.exe" (
        echo       - Install: %INSTALL_DIR%\One2lvOS.exe
    )

    echo.
    echo ========================================================================
) else (
    echo.
    echo    ^> ERROR: dist\One2lvOS.exe not found
    echo    ^> Build may have failed
    pause
    exit /b 1
)

echo.
pause

exit /b 0
