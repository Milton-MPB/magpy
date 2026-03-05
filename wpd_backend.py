#!/usr/bin/env python3
"""
Windows Portable Devices (WPD) Backend for Canon Shutter Count
Uses native Windows COM API to read shutter count without driver changes.

Supports:
- Digic 8/X cameras (R5, R6, R7, R8, R10, 1D X III, R3) via Property 0xD167
- Digic 6+ cameras (5D IV, 90D, 6D II, 80D) via Monitor Mode 0x905F
"""
import struct
import sys

# WPD is Windows-only
if sys.platform != 'win32':
    raise ImportError("WPD backend requires Windows")

try:
    import comtypes
    from comtypes import GUID, POINTER, CoCreateInstance, COMMETHOD
    from comtypes.client import CreateObject
    from ctypes import c_void_p, c_ulong, c_wchar_p, byref, create_unicode_buffer
    from ctypes.wintypes import DWORD, LPWSTR
    import ctypes
except ImportError as e:
    raise ImportError(f"WPD backend requires comtypes: {e}")


# COM GUIDs for Windows Portable Devices
CLSID_PortableDeviceManager = GUID("{0AF10CEC-2ECD-4B92-9581-34F6AE0637F3}")
CLSID_PortableDevice = GUID("{728A21C5-3D9E-48D7-9810-864848F0F404}")
CLSID_PortableDeviceValues = GUID("{0C15D503-D017-47CE-9016-7B3F978721CC}")
CLSID_PortableDevicePropVariantCollection = GUID("{08A99E2F-6D6D-4B80-AF5A-BAF2BCBE4CB9}")

# Property keys for WPD
class PROPERTYKEY(ctypes.Structure):
    _fields_ = [
        ('fmtid', GUID),
        ('pid', DWORD)
    ]

# WPD MTP Extension property keys
WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 11
)
WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 12
)
WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 13
)

WPD_PROPERTY_COMMON_COMMAND_CATEGORY = PROPERTYKEY(
    GUID("{F0422A9C-5DC8-4440-B5BD-5DF28835658A}"), 1001
)
WPD_PROPERTY_COMMON_COMMAND_ID = PROPERTYKEY(
    GUID("{F0422A9C-5DC8-4440-B5BD-5DF28835658A}"), 1002
)

WPD_PROPERTY_MTP_EXT_OPERATION_CODE = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1001
)
WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1002
)
WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1006
)
WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1011
)
WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_READ = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1012
)
WPD_PROPERTY_MTP_EXT_TRANSFER_DATA = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1013
)
WPD_PROPERTY_MTP_EXT_RESPONSE_CODE = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1005
)
WPD_PROPERTY_MTP_EXT_RESPONSE_PARAMS = PROPERTYKEY(
    GUID("{4D545058-1A2E-4106-A357-771E0819FC56}"), 1006
)

WPD_CLIENT_NAME = PROPERTYKEY(
    GUID("{204D9F0C-2292-4080-9F42-40664E70F859}"), 2
)
WPD_CLIENT_MAJOR_VERSION = PROPERTYKEY(
    GUID("{204D9F0C-2292-4080-9F42-40664E70F859}"), 3
)


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


class WPDCanonCamera:
    """
    Windows Portable Devices interface for Canon cameras.
    Uses native Windows COM API to communicate via PTP/MTP.
    """

    def __init__(self):
        self.device = None
        self.device_id = None
        comtypes.CoInitialize()

    def __del__(self):
        self.close()
        try:
            comtypes.CoUninitialize()
        except:
            pass

    def find_canon_camera(self):
        """Find Canon camera via WPD enumeration"""
        try:
            # Try using win32com as fallback if comtypes fails
            try:
                from comtypes.gen import PortableDeviceApi as PDA
            except ImportError:
                # Try to generate the type library
                import comtypes.client
                try:
                    # Generate PortableDeviceApi type library
                    comtypes.client.GetModule(('{1F001332-1A57-4934-BE31-AFFC99F4EE0A}', 1, 0))
                    # Try importing again after generation
                    import importlib
                    import comtypes.gen
                    importlib.reload(comtypes.gen)
                    from comtypes.gen import PortableDeviceApi as PDA
                except Exception as e:
                    # If comtypes fails, try win32com as fallback
                    try:
                        import win32com.client
                        return self._find_camera_win32com()
                    except ImportError:
                        raise ImportError(f"Failed to use WPD (comtypes failed and pywin32 not available): {e}")

            # Create device manager
            manager = CoCreateInstance(
                CLSID_PortableDeviceManager,
                interface=PDA.IPortableDeviceManager
            )

            # Get device count
            count = DWORD()
            manager.GetDevices(None, byref(count))

            if count.value == 0:
                return None

            # Get device IDs
            device_ids = (LPWSTR * count.value)()
            manager.GetDevices(device_ids, byref(count))

            # Find Canon device
            for i in range(count.value):
                device_id = device_ids[i]

                # Check manufacturer
                manufacturer = create_unicode_buffer(256)
                manufacturer_len = DWORD(256)

                try:
                    manager.GetDeviceManufacturer(device_id, manufacturer, byref(manufacturer_len))
                    if 'CANON' in manufacturer.value.upper():
                        self.device_id = device_id
                        return device_id
                except:
                    continue

            return None

        except Exception as e:
            print(f"Error finding Canon camera: {e}")
            return None

    def _find_camera_win32com(self):
        """Fallback method using win32com instead of comtypes"""
        try:
            import win32com.client

            # Use WMI to enumerate portable devices
            wmi = win32com.client.GetObject("winmgmts:")
            devices = wmi.InstancesOf("Win32_PnPEntity")

            for device in devices:
                try:
                    if device.Name and 'canon' in device.Name.lower():
                        # Found a Canon device
                        # Note: win32com doesn't give us the same level of WPD access
                        # This is just for detection
                        print(f"Found Canon device via WMI: {device.Name}")
                        # We can't actually use this for WPD commands, so return None
                        # This will force fallback to other methods
                        return None
                except:
                    continue

            return None
        except Exception as e:
            print(f"Win32com detection also failed: {e}")
            return None

    def open(self):
        """Open connection to Canon camera"""
        try:
            if not self.device_id:
                if not self.find_canon_camera():
                    return False

            from comtypes.gen import PortableDeviceApi as PDA

            # Create device instance
            self.device = CoCreateInstance(
                CLSID_PortableDevice,
                interface=PDA.IPortableDevice
            )

            # Create client info
            client_info = CoCreateInstance(
                CLSID_PortableDeviceValues,
                interface=PDA.IPortableDeviceValues
            )

            # Set client name
            from comtypes import BSTR
            client_info.SetStringValue(
                byref(WPD_CLIENT_NAME),
                BSTR("MagPy Canon Shutter Reader")
            )
            client_info.SetUnsignedIntegerValue(
                byref(WPD_CLIENT_MAJOR_VERSION),
                1
            )

            # Open device
            self.device.Open(self.device_id, client_info)
            return True

        except Exception as e:
            print(f"Error opening Canon camera: {e}")
            return False

    def close(self):
        """Close connection"""
        if self.device:
            try:
                self.device.Close()
            except:
                pass
            self.device = None

    def send_mtp_command_no_data(self, opcode, params=None):
        """
        Send MTP command without data phase.
        Used for handshake commands like 0x9116, 0x9114.
        """
        try:
            from comtypes.gen import PortableDeviceApi as PDA

            params = params or []

            # Create command parameters
            command_params = CoCreateInstance(
                CLSID_PortableDeviceValues,
                interface=PDA.IPortableDeviceValues
            )

            # Set command category and ID
            command_params.SetGuidValue(
                byref(WPD_PROPERTY_COMMON_COMMAND_CATEGORY),
                byref(WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE.fmtid)
            )
            command_params.SetUnsignedIntegerValue(
                byref(WPD_PROPERTY_COMMON_COMMAND_ID),
                WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE.pid
            )

            # Set operation code
            command_params.SetUnsignedIntegerValue(
                byref(WPD_PROPERTY_MTP_EXT_OPERATION_CODE),
                opcode
            )

            # Set parameters if any
            if params:
                param_collection = CoCreateInstance(
                    CLSID_PortableDevicePropVariantCollection,
                    interface=PDA.IPortableDevicePropVariantCollection
                )

                for param in params:
                    pv = comtypes.automation.VARIANT()
                    pv.value = param
                    param_collection.Add(byref(pv))

                command_params.SetIPortableDevicePropVariantCollectionValue(
                    byref(WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS),
                    param_collection
                )

            # Send command
            results = POINTER(PDA.IPortableDeviceValues)()
            self.device.SendCommand(0, command_params, byref(results))

            # Get response code
            response_code = DWORD()
            results.GetUnsignedIntegerValue(
                byref(WPD_PROPERTY_MTP_EXT_RESPONSE_CODE),
                byref(response_code)
            )

            return response_code.value == 0x2001  # OK

        except Exception as e:
            print(f"Error sending MTP command 0x{opcode:04X}: {e}")
            return False

    def send_mtp_command_with_data_read(self, opcode, params=None, expected_size=1024):
        """
        Send MTP command with data to read from device.
        Used for Property 0xD167 and Monitor Mode 0x905F.
        Returns bytes data from camera.
        """
        try:
            from comtypes.gen import PortableDeviceApi as PDA

            params = params or []

            # Create command parameters
            command_params = CoCreateInstance(
                CLSID_PortableDeviceValues,
                interface=PDA.IPortableDeviceValues
            )

            # Set command for data read
            command_params.SetGuidValue(
                byref(WPD_PROPERTY_COMMON_COMMAND_CATEGORY),
                byref(WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.fmtid)
            )
            command_params.SetUnsignedIntegerValue(
                byref(WPD_PROPERTY_COMMON_COMMAND_ID),
                WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.pid
            )

            # Set operation code
            command_params.SetUnsignedIntegerValue(
                byref(WPD_PROPERTY_MTP_EXT_OPERATION_CODE),
                opcode
            )

            # Set parameters
            if params:
                param_collection = CoCreateInstance(
                    CLSID_PortableDevicePropVariantCollection,
                    interface=PDA.IPortableDevicePropVariantCollection
                )

                for param in params:
                    pv = comtypes.automation.VARIANT()
                    pv.value = param
                    param_collection.Add(byref(pv))

                command_params.SetIPortableDevicePropVariantCollectionValue(
                    byref(WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS),
                    param_collection
                )

            # Send initial command
            results = POINTER(PDA.IPortableDeviceValues)()
            self.device.SendCommand(0, command_params, byref(results))

            # Get transfer context
            transfer_context = create_unicode_buffer(256)
            results.GetStringValue(
                byref(WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT),
                transfer_context
            )

            # Get total data size
            total_size = DWORD()
            try:
                results.GetUnsignedIntegerValue(
                    byref(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE),
                    byref(total_size)
                )
            except:
                total_size = DWORD(expected_size)

            # Read data
            read_params = CoCreateInstance(
                CLSID_PortableDeviceValues,
                interface=PDA.IPortableDeviceValues
            )

            # Set context
            read_params.SetStringValue(
                byref(WPD_PROPERTY_MTP_EXT_TRANSFER_CONTEXT),
                transfer_context.value
            )
            read_params.SetUnsignedIntegerValue(
                byref(WPD_PROPERTY_MTP_EXT_TRANSFER_NUM_BYTES_TO_READ),
                total_size.value
            )

            # Read data results
            read_results = POINTER(PDA.IPortableDeviceValues)()
            self.device.SendCommand(0, read_params, byref(read_results))

            # Extract data bytes
            data_array = POINTER(ctypes.c_ubyte)()
            data_size = DWORD()

            read_results.GetBufferValue(
                byref(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA),
                byref(data_array),
                byref(data_size)
            )

            # Convert to bytes
            return bytes(data_array[:data_size.value])

        except Exception as e:
            print(f"Error reading data from MTP command 0x{opcode:04X}: {e}")
            return None

    def read_property_0xd167(self):
        """
        Read shutter count via Property 0xD167 (Digic 8/X cameras).
        Works on: R5, R6, R6 II/III, R7, R8, R10, 1D X III, R3

        Returns ShutterCountResult with mechanical and electronic counts.
        """
        try:
            # GetDevicePropValue (0x1015) for property 0xD167
            data = self.send_mtp_command_with_data_read(0x1015, [0xD167], expected_size=16)

            if not data or len(data) < 16:
                return ShutterCountResult(success=False, error="Property 0xD167 not available")

            # Parse response (16 bytes)
            # Bytes 0-3: Header/type
            # Bytes 4-7: Flags
            # Bytes 8-11: Mechanical shutter count
            # Bytes 12-15: Electronic shutter count
            mechanical = struct.unpack('<I', data[8:12])[0]
            electronic = struct.unpack('<I', data[12:16])[0]
            total = mechanical + electronic

            return ShutterCountResult(
                mechanical=mechanical,
                electronic=electronic,
                total=total,
                source="WPD Property 0xD167",
                success=True
            )

        except Exception as e:
            return ShutterCountResult(success=False, error=f"Property 0xD167 failed: {e}")

    def read_monitor_mode_0x905f(self):
        """
        Read shutter count via Monitor Mode 0x905F (Digic 6+ cameras).
        Works on: 5D Mark IV, 90D, 6D Mark II, 80D

        Requires handshake sequence:
        1. Enable Canon Extended Features (0x9116)
        2. Set Remote Mode (0x9114)
        3. Monitor Mode (0x905F)
        4. Disable Remote Mode (0x9114)

        Returns ShutterCountResult.
        """
        try:
            # Step 1: Enable Canon Extended Features
            if not self.send_mtp_command_no_data(0x9116, [1]):
                return ShutterCountResult(success=False, error="Failed to enable Canon features (0x9116)")

            # Step 2: Set Remote Mode
            if not self.send_mtp_command_no_data(0x9114, [1]):
                return ShutterCountResult(success=False, error="Failed to set remote mode (0x9114)")

            # Step 3: Monitor Mode query
            data = self.send_mtp_command_with_data_read(0x905F, [0x0D], expected_size=512)

            # Step 4: Disable Remote Mode (cleanup)
            self.send_mtp_command_no_data(0x9114, [0])

            if not data:
                return ShutterCountResult(success=False, error="Monitor Mode 0x905F returned no data")

            # Parse response - scan for valid shutter count
            # The response format varies, but shutter count is typically a 32-bit value
            # in a reasonable range (10 - 10,000,000)
            for i in range(0, min(len(data) - 4, 200), 4):
                try:
                    value = struct.unpack('<I', data[i:i+4])[0]
                    if 10 < value < 10000000:
                        return ShutterCountResult(
                            mechanical=value,
                            electronic=0,  # Monitor mode doesn't separate them
                            total=value,
                            source="WPD Monitor Mode 0x905F",
                            success=True
                        )
                except:
                    continue

            return ShutterCountResult(success=False, error="Could not parse shutter count from Monitor Mode response")

        except Exception as e:
            # Make sure to disable remote mode on error
            try:
                self.send_mtp_command_no_data(0x9114, [0])
            except:
                pass
            return ShutterCountResult(success=False, error=f"Monitor Mode failed: {e}")


def read_shutter_count_wpd():
    """
    Read shutter count from Canon camera using WPD.
    Tries multiple methods in order:
    1. Property 0xD167 (Digic 8/X)
    2. Monitor Mode 0x905F (Digic 6+)

    Returns ShutterCountResult.
    """
    if sys.platform != 'win32':
        return ShutterCountResult(success=False, error="WPD backend requires Windows")

    camera = WPDCanonCamera()

    try:
        if not camera.open():
            return ShutterCountResult(success=False, error="No Canon camera found via WPD")

        # Method 1: Try Property 0xD167 (newest cameras)
        result = camera.read_property_0xd167()
        if result.success:
            return result

        # Method 2: Try Monitor Mode 0x905F (older Digic 6+ cameras)
        result = camera.read_monitor_mode_0x905f()
        if result.success:
            return result

        return ShutterCountResult(success=False, error="Camera doesn't support WPD methods (may be too old for WPD, try EDSDK)")

    finally:
        camera.close()


if __name__ == '__main__':
    """Test WPD backend"""
    result = read_shutter_count_wpd()

    if result.success:
        print(f"\n{'='*60}")
        print("SHUTTER COUNT (via WPD)")
        print(f"{'='*60}")
        print(f"Mechanical actuations: {result.mechanical:,}")
        print(f"Electronic actuations: {result.electronic:,}")
        print(f"TOTAL ACTUATIONS:      {result.total:,}")
        print(f"Method: {result.source}")
        print(f"{'='*60}\n")
    else:
        print(f"ERROR: {result.error}")
        sys.exit(1)
