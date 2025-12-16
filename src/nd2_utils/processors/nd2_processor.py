"""
ND2 file processing module.
"""

import logging
from typing import Dict, Any, Optional
import numpy as np

from ..utils.metadata import MetadataHandler
from ..utils.dimensions import DimensionParser
from ..utils.threading import BaseWorkerThread, OperationCancelled

logger = logging.getLogger(__name__)

try:
    import nd2
    assert hasattr(nd2, 'imread'), "nd2.imread function not found"
    ND2_AVAILABLE = True
except ImportError:
    logger.error("nd2 package not available")
    ND2_AVAILABLE = False


class ND2Processor(BaseWorkerThread):
    """Worker thread for loading and processing ND2 files."""
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Load ND2 file and extract metadata."""
        try:
            self._check_cancelled()
            logger.debug(f"Starting to load file: {self.file_path}")
            
            if not ND2_AVAILABLE:
                raise ImportError("nd2 package is not available")
            
            self._check_cancelled()
            # Use imread with xarray=True, dask=True
            logger.debug("Calling nd2.imread with xarray=True, dask=True")
            my_array = nd2.imread(self.file_path, xarray=True, dask=True)
            logger.debug(f"imread returned xarray with shape: {my_array.shape}")
            
            self._check_cancelled()
            # Extract metadata from xarray attributes
            logger.debug("Extracting metadata from xarray attrs")
            attrs = my_array.attrs.get('metadata', {})
            
            self._check_cancelled()
            # Build comprehensive info dict
            info = MetadataHandler.build_info_dict(self.file_path, my_array, attrs)
            
            # Parse dimension information
            self._check_cancelled()
            dimensions = DimensionParser.parse_dimensions(my_array)
            info['dimensions'] = dimensions
            
            logger.debug(f"Emitting finished signal with info")
            self.finished.emit(info)
            
        except OperationCancelled:
            logger.debug("ND2 processing cancelled")
            self.error.emit("Operation cancelled")
        except Exception as e:
            logger.exception(f"Error loading ND2 file: {e}")
            self.error.emit(f"Error loading ND2 file: {str(e)}")
    
    @staticmethod
    def load_file(file_path: str) -> Dict[str, Any]:
        """Load ND2 file synchronously (for CLI usage)."""
        logger.debug(f"Loading ND2 file synchronously: {file_path}")
        
        if not ND2_AVAILABLE:
            raise ImportError("nd2 package is not available")
        
        # Use imread with xarray=True, dask=True
        my_array = nd2.imread(file_path, xarray=True, dask=True)
        
        # Extract metadata
        attrs = my_array.attrs.get('metadata', {})
        
        # Build info dict
        info = MetadataHandler.build_info_dict(file_path, my_array, attrs)
        info['dimensions'] = DimensionParser.parse_dimensions(my_array)
        
        return info
    
    @staticmethod
    def extract_subset(info: Dict[str, Any], 
                      position: Optional[int] = None,
                      channel: Optional[int] = None,
                      time: Optional[int] = None,
                      z: Optional[int] = None) -> np.ndarray:
        """Extract a subset of data from ND2 file info."""
        logger.debug("Extracting subset of data")
        
        dimensions = info['dimensions']
        xarray = info['xarray']
        
        # Validate dimension selections
        slicers = DimensionParser.validate_dimension_selection(
            dimensions, position, channel, time, z
        )
        
        # Extract the subset from the xarray
        if slicers:
            logger.debug(f"Applying slices: {slicers}")
            data_array = xarray.isel(slicers, drop=False)  # drop=False maintains dimensions
            # Convert to numpy
            data = data_array.compute()
            logger.debug(f"Converted subset to numpy with shape: {data.shape}")
        else:
            # No subset selection, export entire file
            logger.debug("Exporting entire file")
            data = xarray.compute()
            logger.debug(f"Converted to numpy with shape: {data.shape}")
        
        return data
