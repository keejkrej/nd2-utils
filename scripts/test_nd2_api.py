#!/usr/bin/env python3
"""
Test script to verify the nd2 API implementation is working correctly.
"""

import nd2
import numpy as np

def test_imread_api():
    """Test that imread works with the correct parameters."""
    print("Testing nd2.imread API...")
    
    # Verify the function exists and accepts the expected parameters
    import inspect
    sig = inspect.signature(nd2.imread)
    print(f"imread signature: {sig}")
    
    # Check for the parameters we need
    params = list(sig.parameters.keys())
    print(f"Parameters: {params}")
    
    assert 'file' in params, "file parameter missing"
    assert 'dask' in params, "dask parameter missing"
    assert 'xarray' in params, "xarray parameter missing"
    
    print("[OK] nd2.imread has the expected parameters")
    
    # Test default values
    dask_param = sig.parameters['dask']
    xarray_param = sig.parameters['xarray']
    print(f"dask default: {dask_param.default}")
    print(f"xarray default: {xarray_param.default}")
    
    print("[OK] All API tests passed!")

if __name__ == "__main__":
    test_imread_api()
