#!/usr/bin/env python3
"""
WPD FAPI Backend - Windows-native MonReadAndGetData via WPD pass-through

Uses wpd-fapi-helper.exe to read shutter count using the same protocol
as PyUSB, but through Windows Portable Devices API instead of raw USB.

Advantages:
- No WinUSB driver needed (uses native Windows MTP driver)
- Camera stays visible in Windows Explorer
- Same MonReadAndGetData protocol as PyUSB (proven to work)
"""
import sys
import json
import subprocess
from pathlib import Path


class ShutterCountResult:
    """Result from shutter count reading"""
    def __init__(self, mechanical=0, electronic=0, total=0, source="", success=False, error=None):
        self.mechanical = mechanical
        self.electronic = electronic
        self.total = total
        self.source = source
        self.success = success
        self.error = error

    def __repr__(self):
        if self.success:
            return f"ShutterCount(mechanical={self.mechanical}, electronic={self.electronic}, total={self.total}, source='{self.source}')"
        else:
            return f"ShutterCount(success=False, error='{self.error}')"


def find_wpd_fapi_helper():
    """Find the WPD FAPI helper executable"""
    script_dir = Path(__file__).parent
    helpers_dir = script_dir / 'helpers' / 'wpd'

    helper_path = helpers_dir / 'wpd-fapi-helper.exe'

    if helper_path.exists():
        return helper_path

    return None


def read_shutter_count_wpd_fapi():
    """
    Read shutter count using WPD FAPI helper.

    This uses the SAME MonReadAndGetData protocol as PyUSB,
    but sends it through WPD pass-through instead of raw USB.

    Returns ShutterCountResult.
    """
    if sys.platform != 'win32':
        return ShutterCountResult(
            success=False,
            error="WPD FAPI backend requires Windows"
        )

    # Find helper executable
    helper_path = find_wpd_fapi_helper()

    if not helper_path:
        return ShutterCountResult(
            success=False,
            error="WPD FAPI helper not found. Please compile helpers/wpd/wpd-fapi-helper.cpp"
        )

    try:
        # Run helper
        result = subprocess.run(
            [str(helper_path)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=helper_path.parent
        )

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Try to find JSON in output
            lines = result.stdout.strip().split('\n')
            data = None
            for line in lines:
                if line.strip().startswith('{'):
                    try:
                        data = json.loads(line)
                        break
                    except:
                        continue

            if not data:
                return ShutterCountResult(
                    success=False,
                    error=f"Failed to parse helper output: {result.stdout[:200]}"
                )

        # Check if successful
        if not data.get('success', False):
            return ShutterCountResult(
                success=False,
                error=data.get('error', 'Unknown error')
            )

        # Extract shutter counts
        mechanical = data.get('mechanical', 0)
        electronic = data.get('electronic', 0)
        total = data.get('total', mechanical + electronic)
        source = data.get('source', 'WPD FAPI')

        return ShutterCountResult(
            mechanical=mechanical,
            electronic=electronic,
            total=total,
            source=source,
            success=True
        )

    except subprocess.TimeoutExpired:
        return ShutterCountResult(
            success=False,
            error="Helper timed out after 10s"
        )
    except Exception as e:
        return ShutterCountResult(
            success=False,
            error=f"Failed to run helper: {e}"
        )


if __name__ == '__main__':
    """Test WPD FAPI backend"""
    # Check if helper exists
    helper_path = find_wpd_fapi_helper()

    if not helper_path:
        print("WPD FAPI helper not found!")
        print("\nTo use WPD FAPI backend:")
        print("1. Navigate to helpers/wpd/")
        print("2. Run build.bat to compile wpd-fapi-helper.exe")
        print("3. Run this script again")
        sys.exit(1)

    print(f"Found helper: {helper_path}\n")

    # Try reading shutter count
    result = read_shutter_count_wpd_fapi()

    if result.success:
        print(f"{'='*60}")
        print("SHUTTER COUNT (via WPD FAPI)")
        print(f"{'='*60}")
        print(f"Mechanical actuations: {result.mechanical:,}")
        print(f"Electronic actuations: {result.electronic:,}")
        print(f"TOTAL ACTUATIONS:      {result.total:,}")
        print(f"Method: {result.source}")
        print(f"{'='*60}\n")
        print("✓ Success!")
    else:
        print(f"ERROR: {result.error}")
        sys.exit(1)
