# Compiling EDSDK Helpers for Windows

This guide explains how to compile the Canon EDSDK helper executables for older camera support (pre-2016 cameras).

**Note:** Most users don't need this! WPD already supports cameras from 2016 onwards.

## When Do You Need EDSDK Helpers?

**You need EDSDK helpers if:**
- You have older Canon cameras from 2010-2015
- Examples: 600D, 650D, 700D, 1100D, 1200D, 60D, 70D, 100D, 5D Mark II/III, 6D, 7D

**You DON'T need EDSDK helpers if:**
- You have cameras from 2016 onwards (5D Mark IV, 90D, 6D Mark II, 80D, R5, R6, R7, R8, R10)
- WPD already supports these cameras natively

## Prerequisites

### Required Software

1. **Visual Studio 2022** (Community Edition is free)
   - Download: https://visualstudio.microsoft.com/downloads/
   - During installation, select "Desktop development with C++"

2. **Canon EDSDK** (Requires Canon Developer Registration)
   - Register at: https://developercommunity.usa.canon.com/canon
   - Download EDSDK versions:
     - EDSDK 3.6.1 (Jul 2017) - Recommended
     - EDSDK 3.5 (Sep 2016)
     - EDSDK 2.14 (Feb 2014)

### Alternative: MinGW (if you don't have Visual Studio)

1. **MinGW-w64**
   - Download: https://www.mingw-w64.org/
   - Or via package manager: `choco install mingw`

## Compilation Steps

### Method 1: Copy from Magpie Project (Easiest)

If you already have the Magpie project with source code:

```batch
# Navigate to Magpie helpers directory
cd C:\path\to\Magpie\helpers

# Compile SDK 3.6.1 helper
cd shutter-helper-sdk361
build.bat

# Compile SDK 3.5 helper
cd ..\shutter-helper-sdk35
build.bat

# Compile SDK 2.14 helper
cd ..\shutter-helper-32
build.bat
```

Then copy the resulting `.exe` files and DLLs to MagPy:

```batch
# Create target directories
mkdir helpers\edsdk\sdk361
mkdir helpers\edsdk\sdk35
mkdir helpers\edsdk\sdk214

# Copy SDK 3.6.1
copy Magpie\helpers\shutter-helper-sdk361\*.exe helpers\edsdk\sdk361\
copy Magpie\helpers\shutter-helper-sdk361\*.dll helpers\edsdk\sdk361\

# Copy SDK 3.5
copy Magpie\helpers\shutter-helper-sdk35\*.exe helpers\edsdk\sdk35\
copy Magpie\helpers\shutter-helper-sdk35\*.dll helpers\edsdk\sdk35\

# Copy SDK 2.14
copy Magpie\helpers\shutter-helper-32\*.exe helpers\edsdk\sdk214\
copy Magpie\helpers\shutter-helper-32\*.dll helpers\edsdk\sdk214\
```

### Method 2: Compile from Source (Full Control)

#### Step 1: Extract EDSDK

Extract each EDSDK version to a separate directory:

```
C:\EDSDK_3.6.1\
  ├── Header\
  │   ├── EDSDK.h
  │   ├── EDSDKErrors.h
  │   └── EDSDKTypes.h
  └── Library\
      ├── EDSDK.dll
      ├── EDSDK.lib
      ├── EdsImage.dll
      ├── Mlib.dll       (SDK 3.6.1 only)
      └── Ucs32P.dll     (SDK 3.6.1 only)
```

#### Step 2: Create Helper Directory Structure

```batch
mkdir helpers\edsdk\sdk361
mkdir helpers\edsdk\sdk35
mkdir helpers\edsdk\sdk214
```

#### Step 3: Copy Source Code

**For SDK 3.6.1:**

Create `helpers\edsdk\sdk361\main.c`:

```c
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <objbase.h>
#include "EDSDK.h"

// See Magpie project for full source code:
// /Users/tom.m/Documents/Magpie/helpers/shutter-helper-sdk361/main.c
```

**Note:** The full source code is available in the Magpie project. Copy `main.c` from:
- SDK 3.6.1: `Magpie/helpers/shutter-helper-sdk361/main.c`
- SDK 3.5: `Magpie/helpers/shutter-helper-sdk35/main.c`
- SDK 2.14: `Magpie/helpers/shutter-helper-32/main.c`

#### Step 4: Copy EDSDK Files

**For each SDK version:**

```batch
# Copy headers
copy C:\EDSDK_3.6.1\Header\*.h helpers\edsdk\sdk361\

# Copy libraries
copy C:\EDSDK_3.6.1\Library\*.dll helpers\edsdk\sdk361\
copy C:\EDSDK_3.6.1\Library\*.lib helpers\edsdk\sdk361\
```

#### Step 5: Create Build Script

Create `helpers\edsdk\sdk361\build.bat`:

```batch
@echo off
echo Building EDSDK 3.6.1 Helper...

REM Find Visual Studio
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "usebackq tokens=*" %%i in (`%VSWHERE% -latest -property installationPath`) do set VSINSTALL=%%i

REM Setup Visual Studio environment
call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat"

REM Compile
cl /Fe:shutter-helper-sdk361.exe /MT /O2 /GS- main.c ^
   /I. ^
   EDSDK.lib kernel32.lib ole32.lib

REM Check if successful
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

echo Build successful!
echo Output: shutter-helper-sdk361.exe
```

#### Step 6: Build

```batch
cd helpers\edsdk\sdk361
build.bat
```

Expected output:
```
Building EDSDK 3.6.1 Helper...
Microsoft (R) C/C++ Optimizing Compiler Version 19.xx.xxxxx for x64
...
Build successful!
Output: shutter-helper-sdk361.exe
```

#### Step 7: Test

```batch
# Test the helper
shutter-helper-sdk361.exe
```

Expected output (with camera connected):
```json
{"success":true,"model":"Canon EOS 600D","serial":"123456789","shutter":45123,"copyright":"-"}
```

#### Step 8: Repeat for Other SDK Versions

Repeat steps 3-7 for SDK 3.5 and SDK 2.14.

## Troubleshooting Compilation

### "cl.exe not found"

**Solution:**
Make sure Visual Studio is installed with "Desktop development with C++" workload.

Or use MinGW instead:
```batch
g++ -o shutter-helper-sdk361.exe main.c EDSDK.lib -lkernel32 -lole32
```

### "EDSDK.h: No such file or directory"

**Solution:**
Copy EDSDK headers to the helper directory:
```batch
copy C:\EDSDK_3.6.1\Header\*.h helpers\edsdk\sdk361\
```

### "Cannot find EDSDK.dll"

**Solution:**
The DLL must be in the same directory as the .exe:
```batch
copy C:\EDSDK_3.6.1\Library\*.dll helpers\edsdk\sdk361\
```

### "Unresolved external symbol"

**Solution:**
Make sure you're linking with EDSDK.lib:
```batch
cl ... main.c EDSDK.lib kernel32.lib ole32.lib
```

### Runtime Error: "The program can't start because EDSDK.dll is missing"

**Solution:**
Copy all DLLs to the .exe directory:

**For SDK 3.6.1:**
```batch
copy EDSDK.dll helpers\edsdk\sdk361\
copy EdsImage.dll helpers\edsdk\sdk361\
copy Mlib.dll helpers\edsdk\sdk361\
copy Ucs32P.dll helpers\edsdk\sdk361\
```

**For SDK 3.5:**
```batch
copy EDSDK.dll helpers\edsdk\sdk35\
copy EdsImage.dll helpers\edsdk\sdk35\
```

**For SDK 2.14:**
```batch
copy EDSDK.dll helpers\edsdk\sdk214\
copy EdsImage.dll helpers\edsdk\sdk214\
```

## Testing Your Helpers

### Test Individual Helper

```batch
cd helpers\edsdk\sdk361
shutter-helper-sdk361.exe
```

### Test via Python Backend

```bash
python edsdk_backend.py
```

### Test via Unified Reader

```bash
python canon_shutter_unified.py -v
```

## File Structure After Compilation

```
MagPy/
├── helpers/
│   └── edsdk/
│       ├── sdk361/
│       │   ├── shutter-helper-sdk361.exe
│       │   ├── EDSDK.dll
│       │   ├── EdsImage.dll
│       │   ├── Mlib.dll
│       │   ├── Ucs32P.dll
│       │   ├── EDSDK.h
│       │   ├── EDSDKErrors.h
│       │   ├── EDSDKTypes.h
│       │   ├── EDSDK.lib
│       │   ├── main.c
│       │   └── build.bat
│       ├── sdk35/
│       │   ├── shutter-helper-sdk35.exe
│       │   ├── EDSDK.dll
│       │   ├── EdsImage.dll
│       │   └── ...
│       └── sdk214/
│           ├── shutter-helper-sdk214.exe
│           ├── EDSDK.dll
│           ├── EdsImage.dll
│           └── ...
```

**Minimum required files for distribution:**
- `shutter-helper-sdkXXX.exe`
- `EDSDK.dll`
- `EdsImage.dll`
- `Mlib.dll` (SDK 3.6.1 only)
- `Ucs32P.dll` (SDK 3.6.1 only)

## Supported Cameras by SDK Version

### SDK 3.6.1 (Jul 2017)
✅ All cameras supported by SDK 3.5, plus:
✅ EOS 6D Mark II, EOS 200D, EOS 77D, EOS 800D

### SDK 3.5 (Sep 2016)
✅ All cameras supported by SDK 2.14, plus:
✅ EOS 5D Mark IV, EOS 80D, EOS 1300D

### SDK 2.14 (Feb 2014)
✅ EOS 70D, EOS 100D, EOS 700D, EOS 1200D
✅ EOS 60D, EOS 600D, EOS 650D, EOS 1100D
✅ EOS 5D Mark III, EOS 6D, EOS 7D
✅ EOS 5D Mark II, EOS 50D, EOS 40D
✅ EOS 550D, EOS 500D, EOS 450D

## Licensing Notes

- **EDSDK:** Requires Canon Developer registration (free)
- **EDSDK License:** Canon's EULA applies - typically free for non-commercial use
- **Your compiled helpers:** Subject to Canon's EDSDK EULA
- **Distribution:** Check Canon's EULA before distributing compiled helpers

## Alternative: Request Pre-Compiled Helpers

If you can't compile yourself, you can:

1. Check if Magpie project has pre-compiled helpers
2. Request them from the project maintainer
3. Use WPD for newer cameras instead (no compilation needed!)

## Next Steps

After successful compilation:

1. Test with `python edsdk_backend.py`
2. Test with `python canon_shutter_unified.py -v`
3. Verify correct shutter count with your camera
4. Optional: Bundle helpers for distribution

## Support

For compilation issues:

1. Check Visual Studio installation
2. Verify EDSDK files are copied correctly
3. Check build.bat for correct paths
4. Test helper manually before Python integration
5. Report issue with full error output
