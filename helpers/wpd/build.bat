@echo off
echo Building WPD FAPI Helper...
echo.

REM Try Visual Studio first
where cl >nul 2>nul
if %ERRORLEVEL% EQU 0 goto :build_vs

REM Setup Visual Studio environment
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist %VSWHERE% (
    echo ERROR: Visual Studio not found
    echo Please install Visual Studio 2022 with C++ Desktop Development
    exit /b 1
)

for /f "usebackq tokens=*" %%i in (`%VSWHERE% -latest -property installationPath`) do set VSINSTALL=%%i
if not exist "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" (
    echo ERROR: Visual Studio C++ tools not found
    exit /b 1
)

echo Setting up Visual Studio environment...
call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

:build_vs
echo Compiling with Visual Studio...
cl /Fe:wpd-fapi-helper.exe /MT /O2 /EHsc wpd-fapi-helper.cpp ^
   kernel32.lib ole32.lib oleaut32.lib PortableDeviceGUIDs.lib

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed!
    exit /b 1
)

echo.
echo Build successful!
echo Output: wpd-fapi-helper.exe
echo.
echo Test it with:
echo   wpd-fapi-helper.exe
