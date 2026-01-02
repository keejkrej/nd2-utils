"""
ND2 file processing module.
"""

import logging
from typing import Dict, Any, Optional
import numpy as np
import nd2

from ..utils.metadata import MetadataHandler
from ..utils.dimensions import DimensionParser
from ..utils.threading import BaseWorkerThread, OperationCancelled

logger = logging.getLogger(__name__)


# Module-level functions for ND2 file operations


def load_file(file_path: str) -> Dict[str, Any]:
    """Load ND2 file synchronously.

    Args:
        file_path: Path to the ND2 file

    Returns:
        Dictionary containing xarray, metadata, attributes, and dimensions
    """
    logger.debug(f"Loading ND2 file: {file_path}")

    # Use imread with xarray=True, dask=True
    my_array = nd2.imread(file_path, xarray=True, dask=True)

    # Extract metadata
    attrs = my_array.attrs.get("metadata", {})

    # Build info dict
    info = MetadataHandler.build_info_dict(file_path, my_array, attrs)
    info["dimensions"] = DimensionParser.parse_dimensions(my_array)

    return info


def extract_subset(
    info: Dict[str, Any],
    position: Optional[int] = None,
    channel: Optional[int] = None,
    time: Optional[int] = None,
    z: Optional[int] = None,
) -> np.ndarray:
    """Extract a subset of data from ND2 file info.

    Args:
        info: ND2 file info dictionary from load_file()
        position: Position index to extract (None for all)
        channel: Channel index to extract (None for all)
        time: Time index to extract (None for all)
        z: Z-slice index to extract (None for all)

    Returns:
        Numpy array with extracted data
    """
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


def build_ome_metadata(
    nd2_attrs: Dict[str, Any], source_filename: str
) -> Dict[str, Any]:
    """Build OME-TIFF metadata from ND2 attributes.

    Args:
        nd2_attrs: ND2 file attributes dictionary
        source_filename: Name of the source ND2 file

    Returns:
        Dictionary with OME-TIFF compatible metadata
    """
    metadata = {"Description": f"Exported from ND2 file: {source_filename}"}

    # Extract pixel sizes if available
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

    # Extract channel names if available
    if isinstance(nd2_attrs, dict) and "channelNames" in nd2_attrs:
        channel_names = nd2_attrs["channelNames"]
        if channel_names:
            metadata["Channel"] = {"Name": list(channel_names)}

    # Extract time loop information if available
    if isinstance(nd2_attrs, dict) and "loops" in nd2_attrs:
        loops = nd2_attrs["loops"]
        # Find TimeLoop
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

            self._check_cancelled()
            # Use imread with xarray=True, dask=True
            logger.debug("Calling nd2.imread with xarray=True, dask=True")
            my_array = nd2.imread(self.file_path, xarray=True, dask=True)
            logger.debug(f"imread returned xarray with shape: {my_array.shape}")

            self._check_cancelled()
            # Extract metadata from xarray attributes
            logger.debug("Extracting metadata from xarray attrs")
            attrs = my_array.attrs.get("metadata", {})

            self._check_cancelled()
            # Build comprehensive info dict
            info = MetadataHandler.build_info_dict(self.file_path, my_array, attrs)

            # Parse dimension information
            self._check_cancelled()
            dimensions = DimensionParser.parse_dimensions(my_array)
            info["dimensions"] = dimensions

            logger.debug("Emitting finished signal with info")
            self.finished.emit(info)

        except OperationCancelled:
            logger.debug("ND2 processing cancelled")
            self.error.emit("Operation cancelled")
        except Exception as e:
            logger.exception(f"Error loading ND2 file: {e}")
            self.error.emit(f"Error loading ND2 file: {str(e)}")
