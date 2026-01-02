#!/usr/bin/env python3
"""
Check what attributes are available in the xarray returned by nd2.imread
"""

import nd2


def check_xarray_attrs():
    """Check the xarray attributes structure"""
    print("Checking xarray attributes from nd2.imread...")

    # Create a test to see the structure (without an actual ND2 file)
    print("Import nd2 module and checking documentation...")

    # Let's look at the documentation or source to understand attrs
    import inspect

    print("\nimread function signature:")
    sig = inspect.signature(nd2.imread)
    print(sig)

    # Check if there are any clues in the nd2 module
    print("\nnd2 module contents related to xarray:")
    for name in dir(nd2):
        if (
            "xarray" in name.lower()
            or "attrs" in name.lower()
            or "metadata" in name.lower()
        ):
            print(f"  {name}: {type(getattr(nd2, name))}")


if __name__ == "__main__":
    check_xarray_attrs()
