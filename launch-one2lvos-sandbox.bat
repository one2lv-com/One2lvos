@echo off
:: ============================================================================
:: Launch One2lvOS in Windows Sandbox
:: ============================================================================
:: Runs One2lvOS in isolated Windows Sandbox environment
:: Requires: Windows 10/11 Pro or Enterprise with Sandbox enabled
:: ============================================================================

title Launch One2lvOS in Sandbox

color 0B
cls

echo.
echo ========================================================================
echo    ONE2LVOS - Windows Sandbox Launcher
echo ========================================================================
echo.
echo    This will launch One2lvOS in an isolated Windows Sandbox
echo.
echo    Requirements:
echo    - Windows 10/11 Pro or Enterprise
echo    - Windows Sandbox feature enabled
echo.
echo ========================================================================
echo.

timeout /t 2 /nobreak >nul

:: Check if Windows Sandbox is available
echo [1/4] Checking Windows Sandbox...

where WindowsSandbox.exe >nul 2>&1
if %errorLevel% neq 0 (
    echo    ^> ERROR: Windows Sandbox not found
    echo.
    echo    Windows Sandbox is only available on:
    echo    - Windows 10 Pro, Enterprise, or Education
    echo    - Windows 11 Pro, Enterprise, or Education
    echo.
    echo    To enable Windows Sandbox:
    echo    1. Open "Turn Windows features on or off"
    echo    2. Check "Windows Sandbox"
    echo    3. Restart computer
    echo.
    echo    OR run this command as Administrator:
    echo    dism /online /Enable-Feature /FeatureName:Containers-DisposableClientVM -All
    echo.
    pause
    exit /b 1
)
echo    ^> Windows Sandbox available [OK]

:: Check if One2lvOS is installed
echo.
echo [2/4] Checking One2lvOS installation...

set INSTALL_DIR=%USERPROFILE%\One2lvOS
if exist "%INSTALL_DIR%" (
    echo    ^> Found at: %INSTALL_DIR% [OK]
) else (
    echo    ^> ERROR: One2lvOS not installed
    echo    ^> Please run install-one2lvos-windows-auto.bat first
    echo.
    pause
    exit /b 1
)

:: Create sandbox configuration
echo.
echo [3/4] Creating sandbox configuration...

set SANDBOX_CONFIG=%TEMP%\One2lvOS-Sandbox.wsb

(
echo ^<?xml version="1.0" encoding="UTF-8"?^>
echo ^<Configuration^>
echo   ^<VGpu^>Enable^</VGpu^>
echo   ^<Networking^>Enable^</Networking^>
echo   ^<MappedFolders^>
echo     ^<MappedFolder^>
echo       ^<HostFolder^>%INSTALL_DIR%^</HostFolder^>
echo       ^<SandboxFolder^>C:\One2lvOS^</SandboxFolder^>
echo       ^<ReadOnly^>false^</ReadOnly^>
echo     ^</MappedFolder^>
echo   ^</MappedFolders^>
echo   ^<LogonCommand^>
echo     ^<Command^>cmd /c "cd C:\One2lvOS && start-one2lvos.bat"^</Command^>
echo   ^</LogonCommand^>
echo   ^<MemoryInMB^>4096^</MemoryInMB^>
echo ^</Configuration^>
) > "%SANDBOX_CONFIG%"

echo    ^> Configuration created [OK]

:: Launch sandbox
echo.
echo [4/4] Launching Windows Sandbox...
echo    ^> One2lvOS will start automatically inside the sandbox
echo    ^> Sandbox will have access to: %INSTALL_DIR%
echo.

start "" WindowsSandbox.exe "%SANDBOX_CONFIG%"

if %errorLevel% neq 0 (
    echo    ^> ERROR: Failed to launch sandbox
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo    SANDBOX LAUNCHED!
echo ========================================================================
echo.
echo    One2lvOS is now running in an isolated Windows Sandbox
echo.
echo    Inside the sandbox:
echo       - Unified Gateway:  http://localhost:8888
echo       - AI Arcade:        http://localhost:8003
echo       - AI Lobby:         http://localhost:8006
echo.
echo    The sandbox is isolated from your main system
echo    All changes will be discarded when you close the sandbox
echo.
echo    To access from host: Use sandbox's IP address
echo    To stop: Close the sandbox window
echo.
echo ========================================================================
echo.

timeout /t 10

exit /b 0
