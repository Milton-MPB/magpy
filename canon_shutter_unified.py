#!/usr/bin/env python3
"""
Unified Canon Shutter Count Reader
Intelligently selects the best method for each camera type.

Method Priority (Windows):
1. WPD Property 0xD167 - Digic 8/X cameras (R5, R6, R7, R8, R10, 1D X III, R3)
2. WPD Monitor Mode 0x905F - Digic 6+ cameras (5D IV, 90D, 6D II, 80D)
3. EDSDK - Older cameras pre-Digic 6 (600D, 1100D, 5D II/III, 6D, 7D, etc.)
4. PyUSB FAPI - Fallback (requires WinUSB driver)

Method Priority (macOS/Linux):
1. PyUSB FAPI - Native USB access (no driver changes needed)
"""
import sys
from pathlib import Path


class ShutterCountResult:
    """Unified result format"""
    def __init__(self, mechanical=0, electronic=0, total=0, source="", success=False, error=None, model=None, serial=None):
        self.mechanical = mechanical
        self.electronic = electronic
        self.total = total
        self.source = source
        self.success = success
        self.error = error
        self.model = model
        self.serial = serial

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'success': self.success,
            'mechanical': self.mechanical,
            'electronic': self.electronic,
            'total': self.total,
            'source': self.source,
            'error': self.error,
            'model': self.model,
            'serial': self.serial
        }

    def __repr__(self):
        if self.success:
            return f"ShutterCount(total={self.total}, source='{self.source}')"
        else:
            return f"ShutterCount(success=False, error='{self.error}')"


class CanonShutterReader:
    """
    Unified Canon shutter count reader.
    Automatically selects best method for platform and camera.
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.platform = sys.platform
        self.is_windows = self.platform == 'win32'

    def log(self, message):
        """Print verbose log message"""
        if self.verbose:
            print(f"[CanonShutterReader] {message}")

    def read_shutter_count(self):
        """
        Read shutter count using best available method.

        Returns:
            ShutterCountResult with success status and data
        """
        if self.is_windows:
            return self._read_windows()
        else:
            return self._read_unix()

    def _read_windows(self):
        """
        Windows-specific reading with intelligent cascade.
        Tries native methods first (WPD, EDSDK), falls back to PyUSB.
        """
        errors = []

        # Method 1: Try WPD (native Windows, no driver changes)
        self.log("Trying WPD Property 0xD167 (Digic 8/X cameras)...")
        try:
            from wpd_backend import read_shutter_count_wpd

            result = read_shutter_count_wpd()

            if result.success:
                self.log(f"✓ Success via {result.source}")
                return result
            else:
                errors.append(f"WPD: {result.error}")
                self.log(f"✗ WPD failed: {result.error}")

        except ImportError as e:
            error_msg = f"WPD not available: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")
        except Exception as e:
            error_msg = f"WPD error: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")

        # Method 2: Try EDSDK (native Windows, no driver changes)
        self.log("Trying EDSDK helpers (pre-Digic 6 cameras)...")
        try:
            from edsdk_backend import read_shutter_count_edsdk

            result = read_shutter_count_edsdk()

            if result.success and result.total > 0:
                self.log(f"✓ Success via {result.source}")
                return result
            else:
                errors.append(f"EDSDK: {result.error}")
                self.log(f"✗ EDSDK failed: {result.error}")

        except ImportError as e:
            error_msg = f"EDSDK not available: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")
        except Exception as e:
            error_msg = f"EDSDK error: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")

        # Method 3: Fallback to PyUSB (requires WinUSB driver)
        self.log("Trying PyUSB FAPI (requires WinUSB driver via Zadig)...")
        try:
            # Import existing PyUSB implementation
            sys.path.insert(0, str(Path(__file__).parent))
            from read_shutter_count import read_shutter_count as read_pyusb

            result_dict = read_pyusb()

            if result_dict:
                result = ShutterCountResult(
                    mechanical=result_dict.get('mechanical', 0),
                    electronic=result_dict.get('electronic', 0),
                    total=result_dict.get('total', 0),
                    source="PyUSB FAPI (WinUSB driver)",
                    success=True
                )
                self.log(f"✓ Success via {result.source}")
                return result
            else:
                error_msg = "PyUSB failed to read shutter count"
                errors.append(f"PyUSB: {error_msg}")
                self.log(f"✗ {error_msg}")

        except ImportError as e:
            error_msg = f"PyUSB not available: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")
        except Exception as e:
            error_msg = f"PyUSB error: {e}"
            errors.append(error_msg)
            self.log(f"✗ {error_msg}")

        # All methods failed
        return ShutterCountResult(
            success=False,
            error=f"All methods failed. Errors: {'; '.join(errors)}"
        )

    def _read_unix(self):
        """
        macOS/Linux reading using PyUSB.
        Native USB access works without driver changes on Unix systems.
        """
        self.log("Using PyUSB FAPI (native macOS/Linux support)...")

        try:
            # Import existing PyUSB implementation
            sys.path.insert(0, str(Path(__file__).parent))
            from read_shutter_count import read_shutter_count as read_pyusb

            result_dict = read_pyusb()

            if result_dict:
                result = ShutterCountResult(
                    mechanical=result_dict.get('mechanical', 0),
                    electronic=result_dict.get('electronic', 0),
                    total=result_dict.get('total', 0),
                    source="PyUSB FAPI",
                    success=True
                )
                self.log(f"✓ Success via {result.source}")
                return result
            else:
                return ShutterCountResult(
                    success=False,
                    error="PyUSB failed to read shutter count"
                )

        except ImportError as e:
            return ShutterCountResult(
                success=False,
                error=f"PyUSB not available: {e}. Install with: pip install pyusb"
            )
        except Exception as e:
            return ShutterCountResult(
                success=False,
                error=f"Error: {e}"
            )


def read_shutter_count_unified(verbose=False):
    """
    Convenience function to read shutter count.

    Args:
        verbose: Enable verbose logging

    Returns:
        ShutterCountResult
    """
    reader = CanonShutterReader(verbose=verbose)
    return reader.read_shutter_count()


if __name__ == '__main__':
    """Test unified reader"""
    import argparse

    parser = argparse.ArgumentParser(description='Canon Shutter Count Reader (Unified)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    print("Canon Camera Shutter Count Reader (Unified)")
    print("="*60)

    result = read_shutter_count_unified(verbose=args.verbose)

    if result.success:
        print(f"\n{'='*60}")
        print("SHUTTER COUNT")
        print(f"{'='*60}")
        if result.model:
            print(f"Camera Model: {result.model}")
        if result.serial:
            print(f"Serial Number: {result.serial}")
        print(f"Mechanical actuations: {result.mechanical:,}")
        print(f"Electronic actuations: {result.electronic:,}")
        print(f"TOTAL ACTUATIONS:      {result.total:,}")
        print(f"Method used: {result.source}")
        print(f"{'='*60}\n")
        print("✓ Success!")
        sys.exit(0)
    else:
        print(f"\n✗ Failed to read shutter count")
        print(f"Error: {result.error}")
        print("\nTroubleshooting:")
        if sys.platform == 'win32':
            print("  - Windows users: WPD and EDSDK should work without driver changes")
            print("  - If using PyUSB fallback, you need WinUSB driver via Zadig")
            print("  - Make sure camera is connected, powered on, and not in use")
        else:
            print("  - Make sure camera is connected and powered on")
            print("  - Try running with sudo if permission denied")
            print("  - Install PyUSB: pip install pyusb")
        sys.exit(1)
