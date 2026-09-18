"""Android Controller package.

Exports AndroidController, ADBClient, UIParser, and relevant error classes.
"""

from .adb_client import (
    ADBClient,
    ADBError,
    ADBTimeoutError,
    CommandRunner,
    DeviceNotFoundError,
)
from .controller import AndroidController
from .ui_parser import (
    UIParser,
    calculate_center,
    compute_center,
    is_useful_element,
    parse_bounds,
    parse_ui_hierarchy,
)

__all__ = [
    "AndroidController",
    "ADBClient",
    "ADBError",
    "ADBTimeoutError",
    "CommandRunner",
    "DeviceNotFoundError",
    "UIParser",
    "calculate_center",
    "compute_center",
    "is_useful_element",
    "parse_bounds",
    "parse_ui_hierarchy",
]
