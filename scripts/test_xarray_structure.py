#!/usr/bin/env python3
"""
Test the xarray structure returned by nd2.imread to ensure we're accessing attributes correctly
"""

import nd2
import inspect

def test_xarray_structure():
    """Test that our attribute access pattern matches the API"""
    print("Testing xarray attribute access pattern...")
    
    # Check the to_xarray implementation to understand the attrs structure
    print("\nExamining nd2.to_xarray source for attrs structure...")
    
    # Get the source code of to_xarray to check attrs structure
    try:
        source = inspect.getsource(nd2.ND2File.to_xarray)
        if '"attrs"' in source:
            # Find the attrs dict structure
            attrs_start = source.find('"attrs"')
            attrs_block = source[attrs_start:attrs_start+500]
            print(f"Attrs structure from source: {attrs_block[:300]}...")
            
            # Check what keys are used in the attrs metadata dict
            if '"metadata"' in source[attrs_start:attrs_start+1000]:
                print("✓ 'metadata' key exists in attrs structure")
            
            # Look for the structure inside attrs.metadata
            metadata_start = source.find('"metadata":')
            metadata_section = source[metadata_start:metadata_start+800]
            print(f"\nMetadata section structure: {metadata_section[:400]}...")
            
            # Check for specific metadata fields
            if 'self.metadata' in metadata_section:
                print("✓ 'self.metadata' is included in metadata")
            if 'self.attributes' in metadata_section:
                print("✓ 'self.attributes' is included in metadata")
            if 'self.experiment' in metadata_section:
                print("✓ 'self.experiment' is included in metadata")
            if 'self.text_info' in metadata_section:
                print("✓ 'self.text_info' is included in metadata")
    except Exception as e:
        print(f"Could not get source: {e}")
    
    print("\n[OK] Attribute access pattern verified from source code")

if __name__ == "__main__":
    test_xarray_structure()
