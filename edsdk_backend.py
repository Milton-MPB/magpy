#!/usr/bin/env python3
"""
Canon EDSDK Backend for Shutter Count Reading
Wraps EDSDK helper executables via subprocess calls.

Supports older Canon cameras (pre-Digic 6, ~2015 and earlier):
- 40D, 50D, 60D, 70D, 100D
- 450D-700D, 1100D-1300D
- 5D Mark II/III, 6D, 7D
"""
import os
import sys
import json
import subprocess
from pathlib import Path


class ShutterCountResult:
    """Result from shutter count reading"""
    def __init__(self, mechanical=0, electronic=0, total=0, source="", success=False, error=None, model=None, serial=None):
        self.mechanical = mechanical
        self.electronic = electronic
        self.total = total
        self.source = source
        self.success = success
        self.error = error
        self.model = model
        self.serial = serial

    def __repr__(self):
        if self.success:
            return f"ShutterCount(total={self.total}, source='{self.source}', model='{self.model}')"
        else:
            return f"ShutterCount(success=False, error='{self.error}')"


def find_edsdk_helpers():
    """
    Find EDSDK helper executables.
    Returns dict of {sdk_version: exe_path}
    """
    helpers = {}

    # Get script directory
    script_dir = Path(__file__).parent

    # Look for helpers in helpers/edsdk/ directory
    helpers_dir = script_dir / 'helpers' / 'edsdk'

    if not helpers_dir.exists():
        return helpers

    # SDK versions to look for (in priority order)
    sdk_versions = [
        ('sdk361', 'shutter-helper-sdk361.exe'),
        ('sdk35', 'shutter-helper-sdk35.exe'),
        ('sdk214', 'shutter-helper-sdk214.exe'),
        ('sdk32', 'shutter-helper-32.exe'),  # Alternative name for 2.14
    ]

    for sdk_name, exe_name in sdk_versions:
        exe_path = helpers_dir / exe_name

        if exe_path.exists() and os.access(exe_path, os.X_OK):
            helpers[sdk_name] = exe_path

    return helpers


def run_edsdk_helper(exe_path, timeout=10):
    """
    Run EDSDK helper executable and parse JSON output.

    Args:
        exe_path: Path to helper executable
        timeout: Timeout in seconds

    Returns:
        ShutterCountResult
    """
    try:
        # Run helper with timeout
        result = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=exe_path.parent  # Run in helper directory so it finds DLLs
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

        # Extract shutter count
        shutter = data.get('shutter', 0)
        model = data.get('model', 'Unknown')
        serial = data.get('serial', '-')

        # EDSDK returns total count, doesn't separate mechanical/electronic
        return ShutterCountResult(
            mechanical=shutter,
            electronic=0,
            total=shutter,
            source=f"EDSDK {exe_path.stem}",
            success=True,
            model=model,
            serial=serial
        )

    except subprocess.TimeoutExpired:
        return ShutterCountResult(
            success=False,
            error=f"Helper timed out after {timeout}s"
        )
    except Exception as e:
        return ShutterCountResult(
            success=False,
            error=f"Failed to run helper: {e}"
        )


def read_shutter_count_edsdk():
    """
    Read shutter count using EDSDK helpers.
    Tries multiple SDK versions in cascade:
    1. SDK 3.6.1 (newest, Jul 2017)
    2. SDK 3.5 (Sep 2016)
    3. SDK 2.14 (Feb 2014)

    Returns ShutterCountResult.
    """
    if sys.platform != 'win32':
        return ShutterCountResult(
            success=False,
            error="EDSDK backend requires Windows"
        )

    # Find available helpers
    helpers = find_edsdk_helpers()

    if not helpers:
        return ShutterCountResult(
            success=False,
            error="No EDSDK helpers found. Please compile helpers from helpers/edsdk/ directory."
        )

    # Try helpers in priority order
    priority_order = ['sdk361', 'sdk35', 'sdk214', 'sdk32']

    last_error = None

    for sdk_name in priority_order:
        if sdk_name not in helpers:
            continue

        exe_path = helpers[sdk_name]
        result = run_edsdk_helper(exe_path)

        # Return first successful result with non-zero count
        if result.success and result.total > 0:
            return result

        last_error = result.error

    # All helpers failed or returned 0
    if last_error:
        return ShutterCountResult(
            success=False,
            error=f"All EDSDK helpers failed. Last error: {last_error}"
        )
    else:
        return ShutterCountResult(
            success=False,
            error="EDSDK helpers returned 0 (camera may be too new for EDSDK)"
        )


if __name__ == '__main__':
    """Test EDSDK backend"""
    # List available helpers
    helpers = find_edsdk_helpers()

    if helpers:
        print(f"Found EDSDK helpers: {list(helpers.keys())}")
    else:
        print("No EDSDK helpers found in helpers/edsdk/")
        print("\nTo use EDSDK backend:")
        print("1. Copy helper source from Magpie project")
        print("2. Compile on Windows")
        print("3. Place executables in helpers/edsdk/")
        sys.exit(1)

    # Try reading shutter count
    result = read_shutter_count_edsdk()

    if result.success:
        print(f"\n{'='*60}")
        print("SHUTTER COUNT (via EDSDK)")
        print(f"{'='*60}")
        print(f"Camera Model: {result.model}")
        print(f"Serial Number: {result.serial}")
        print(f"Total actuations: {result.total:,}")
        print(f"Method: {result.source}")
        print(f"{'='*60}\n")
    else:
        print(f"ERROR: {result.error}")
        sys.exit(1)
