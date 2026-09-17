"""
Android Controller package.

Provides automated control, inspection, and action execution on Android devices via ADB and UIAutomator.
"""

try:
    from .adb_client import ADBClient, ADBError, ADBTimeoutError, DeviceNotFoundError
    from .controller import AndroidController
    from .ui_parser import UIParser, compute_center, parse_bounds
except (ImportError, ValueError):
    from adb_client import ADBClient, ADBError, ADBTimeoutError, DeviceNotFoundError
    from controller import AndroidController
    from ui_parser import UIParser, compute_center, parse_bounds


__all__ = [
    "ADBClient",
    "ADBError",
    "ADBTimeoutError",
    "DeviceNotFoundError",
    "UIParser",
    "parse_bounds",
    "compute_center",
    "AndroidController",
]
