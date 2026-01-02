"""
ND2 file processing module.
"""

import logging
from typing import Any, Dict, Optional, Callable

import nd2
import numpy as np

from ..utils.dimensions import DimensionParser
from ..utils.metadata import MetadataHandler
from ..utils.threading import BaseWorkerThread, OperationCancelled
from ..core.signals import SignalsInterface, DefaultSignals

logger = logging.getLogger(__name__)


# Module-level functions for ND2 file operations

def load_file(file_path: str) -> Dict[str, Any]:
    """Load ND2 file synchronously."""
    return ND2ProcessorLogic.load(file_path)


def extract_subset(
    info: Dict[str, Any],
    position: Optional[int] = None,
    channel: Optional[int] = None,
    time: Optional[int] = None,
    z: Optional[int] = None,
) -> np.ndarray:
    """Extract a subset of data from ND2 file info."""
    logger.debug("Extracting subset of data")

    dimensions = info["dimensions"]
    xarray = info["xarray"]

    # Validate dimension selections
    slicers = DimensionParser.validate_dimension_selection(
        dimensions, position, channel, time, z
    )

    # Extract the subset from the xarray
    if slicers:
        logger.debug(f"Applying slices: {slicers}")
        data_array = xarray.isel(slicers, drop=False)
        data = data_array.compute()
        logger.debug(f"Converted subset to numpy with shape: {data.shape}")
    else:
        logger.debug("Exporting entire file")
        data = xarray.compute()
        logger.debug(f"Converted to numpy with shape: {data.shape}")

    return data


def build_ome_metadata(
    nd2_attrs: Dict[str, Any], source_filename: str
) -> Dict[str, Any]:
    """Build OME-TIFF metadata from ND2 attributes."""
    metadata = {"Description": f"Exported from ND2 file: {source_filename}"}

    # Extract pixel sizes
    if isinstance(nd2_attrs, dict) and "pixelSizeUm" in nd2_attrs:
        pixel_size = nd2_attrs["pixelSizeUm"]
        if hasattr(pixel_size, "x") and pixel_size.x:
            metadata["PhysicalSizeX"] = pixel_size.x
            metadata["PhysicalSizeXUnit"] = "µm"
        if hasattr(pixel_size, "y") and pixel_size.y:
            metadata["PhysicalSizeY"] = pixel_size.y
            metadata["PhysicalSizeYUnit"] = "µm"
        if hasattr(pixel_size, "z") and pixel_size.z:
            metadata["PhysicalSizeZ"] = pixel_size.z
            metadata["PhysicalSizeZUnit"] = "µm"

    # Extract channel names
    if isinstance(nd2_attrs, dict) and "channelNames" in nd2_attrs:
        channel_names = nd2_attrs["channelNames"]
        if channel_names:
            metadata["Channel"] = {"Name": list(channel_names)}

    # Extract time loop info
    if isinstance(nd2_attrs, dict) and "loops" in nd2_attrs:
        loops = nd2_attrs["loops"]
        for loop in loops if hasattr(loops, "__iter__") else []:
            if hasattr(loop, "type") and loop.type == "TimeLoop":
                if hasattr(loop, "parameters") and hasattr(loop.parameters, "periodMs"):
                    period_ms = loop.parameters.periodMs
                    if period_ms:
                        metadata["TimeIncrement"] = period_ms
                        metadata["TimeIncrementUnit"] = "ms"
                break

    logger.debug(f"Built OME metadata with keys: {list(metadata.keys())}")
    return metadata

def write_tiff(output_path: str, data_5d: np.ndarray, metadata: Dict[str, Any]):
    """Write 5D data to 4D TIFF."""
    from tifffile import imwrite
    
    t, p, c, y, x = data_5d.shape
    new_shape = (t, p * c, y, x)
    data_to_write = data_5d.reshape(new_shape)
    
    tiff_metadata = metadata.copy()
    tiff_metadata["axes"] = "TCYX"
    
    imwrite(output_path, data_to_write, bigtiff=True, metadata=tiff_metadata, ome=True)

class ND2ProcessorLogic:
    @staticmethod
    def load(
        file_path: str, 
        signals: Optional[SignalsInterface] = None,
        check_cancelled: Optional[Callable[[], None]] = None
    ) -> Dict[str, Any]:
        if signals is None:
            signals = DefaultSignals()
            
        def _check():
            if check_cancelled:
                check_cancelled()
                
        try:
            _check()
            logger.debug(f"Starting to load file: {file_path}")

            _check()
            my_array = nd2.imread(file_path, xarray=True, dask=True)
            logger.debug(f"imread returned xarray with shape: {my_array.shape}")

            _check()
            attrs = my_array.attrs.get("metadata", {})

            _check()
            info = MetadataHandler.build_info_dict(file_path, my_array, attrs)

            _check()
            dimensions = DimensionParser.parse_dimensions(my_array)
            info["dimensions"] = dimensions

            logger.debug("Emitting finished signal with info")
            signals.finished.emit(info)
            return info

        except OperationCancelled:
            logger.debug("ND2 processing cancelled")
            signals.error.emit("Operation cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error loading ND2 file: {e}")
            signals.error.emit(f"Error loading ND2 file: {str(e)}")
            raise

class ND2Processor(BaseWorkerThread):
    """Worker thread for loading and processing ND2 files."""

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        """Load ND2 file and extract metadata."""
        try:
            ND2ProcessorLogic.load(
                file_path=self.file_path,
                signals=self,
                check_cancelled=self._check_cancelled
            )
        except OperationCancelled:
            pass
        except Exception:
            pass
