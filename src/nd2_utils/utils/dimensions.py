"""
Dimension parsing and handling utilities for ND2 files.
"""

import itertools
import logging
from typing import Any, Dict, Optional, Callable, Iterable

import numpy as np
from tqdm import tqdm

logger = logging.getLogger(__name__)


class DimensionParser:
    """Handles dimension parsing and validation for ND2 files."""

    # Standard ND2 dimension order
    STANDARD_AXES = ["T", "P", "C", "Y", "X"]

    @staticmethod
    def parse_dimensions(xarray) -> Dict[str, Dict[str, Any]]:
        """Parse dimension information from xarray."""
        logger.debug("Parsing dimensions from xarray")
        logger.debug(f"xarray dims: {list(xarray.dims)}")

        dimension_info = {}
        for axis in xarray.dims:
            dimension_info[axis] = {
                "size": xarray.sizes.get(axis, 1),
                "labels": [],  # Can't get labels from xarray alone
            }
            logger.debug(f"Axis {axis}: size={dimension_info[axis]['size']}")

        return dimension_info

    @staticmethod
    def validate_dimension_selection(
        dimensions: Dict[str, Dict[str, Any]],
        position: Optional[int] = None,
        channel: Optional[int] = None,
        time: Optional[int] = None,
        z: Optional[int] = None,
    ) -> Dict[str, int]:
        """Validate and return valid dimension selections."""
        logger.debug("Validating dimension selection")

        slicers = {}

        if position is not None and "P" in dimensions:
            max_pos = dimensions["P"]["size"] - 1
            if 0 <= position <= max_pos:
                slicers["P"] = position
                logger.debug(f"Valid position slice: {position}")
            else:
                logger.warning(f"Invalid position {position}, max is {max_pos}")

        if channel is not None and "C" in dimensions:
            max_chan = dimensions["C"]["size"] - 1
            if 0 <= channel <= max_chan:
                slicers["C"] = channel
                logger.debug(f"Valid channel slice: {channel}")
            else:
                logger.warning(f"Invalid channel {channel}, max is {max_chan}")

        if time is not None and "T" in dimensions:
            max_time = dimensions["T"]["size"] - 1
            if 0 <= time <= max_time:
                slicers["T"] = time
                logger.debug(f"Valid time slice: {time}")
            else:
                logger.warning(f"Invalid time {time}, max is {max_time}")

        if z is not None and "Z" in dimensions:
            max_z = dimensions["Z"]["size"] - 1
            if 0 <= z <= max_z:
                slicers["Z"] = z
                logger.debug(f"Valid z slice: {z}")
            else:
                logger.warning(f"Invalid z {z}, max is {max_z}")

        return slicers

    @staticmethod
    def extract_data_with_progress(
        xarray, slicers, desc="Processing data", progress_wrapper: Optional[Callable[[Iterable], Iterable]] = None
    ) -> np.ndarray:
        """Extract data in batches using isel wrapper with progress bar.

        Handles multiple batch dimensions by creating all combinations and looping through them.

        Args:
            xarray: The xarray DataArray to extract from
            slicers: Dictionary with dimension names as keys and list/tuple as values
                    e.g., {'P': 0, 'C': [0], 'T': [0, 100]} for single position,
                          single channel, all time points from index 0 to 99
            desc: Description for progress bar
            progress_wrapper: Optional function to wrap the iterator for progress tracking (e.g., rich.progress.track)

        Returns:
            numpy.ndarray with the extracted data
        """
        logger.debug(f"Batched extraction with slicers: {slicers}")

        # Convert slicers to single values or ranges
        dim_indices = {}
        batch_dims = []
        fixed_dims = {}

        for dim, value in slicers.items():
            if dim not in xarray.dims:
                continue

            if isinstance(value, (list, tuple)) and len(value) == 2:
                # Range format: [start, end] -> range of indices (exclusive end)
                start, end = value
                # Handle the case where start == end (single value)
                if start == end:
                    fixed_dims[dim] = start
                else:
                    # For ranges, end is inclusive, so add 1 for Python range
                    indices = list(range(start, end + 1))
                    dim_indices[dim] = indices
                    if len(indices) > 1:
                        batch_dims.append(dim)
            elif isinstance(value, (list, tuple)) and len(value) > 2:
                # Explicit list of indices
                dim_indices[dim] = list(value)
                batch_dims.append(dim)
            elif value is None:
                # Single value but None - skip
                continue
            else:
                # Single value
                fixed_dims[dim] = value

        # Check if we need batch processing
        if not batch_dims:
            logger.debug(f"Single extraction with: {fixed_dims}")
            result = xarray.isel(fixed_dims, drop=False).compute()
            # Preserve original dtype from dask/xarray to prevent float64 promotion
            if hasattr(result, "dtype") and result.dtype != xarray.dtype:
                result = result.astype(xarray.dtype)
            return result

        logger.debug(f"Batch dimensions: {batch_dims}")
        logger.debug(f"Fixed dimensions: {fixed_dims}")

        # Generate all combinations of batch dimension indices
        batch_combinations = list(
            itertools.product(*[dim_indices[dim] for dim in batch_dims])
        )

        total_combinations = len(batch_combinations)
        logger.debug(
            f"Generated {total_combinations} combinations for {len(batch_dims)} batch dimensions"
        )

        # Pre-allocate array directly in xarray.dims order (no transpose needed!)
        logger.debug("Pre-allocating result array in xarray.dims order")

        # Build final shape in xarray.dims order
        final_shape = []
        for dim in xarray.dims:
            if dim in batch_dims:
                final_shape.append(len(dim_indices[dim]))
            elif dim in fixed_dims:
                final_shape.append(1)
            else:
                # Non-batch, non-fixed dimension keeps its full size
                final_shape.append(xarray.sizes[dim])

        result_array = np.zeros(final_shape, dtype=xarray.dtype)
        logger.debug(
            f"Pre-allocated array with shape: {result_array.shape}, dtype: {result_array.dtype}"
        )

        # Create mapping from original indices to result array indices
        index_maps = {
            dim: {
                orig_idx: result_idx
                for result_idx, orig_idx in enumerate(dim_indices[dim])
            }
            for dim in batch_dims
        }

        # Create mapping from dimension name to its position in xarray.dims
        dim_positions = {dim: i for i, dim in enumerate(xarray.dims)}

        # Use provided progress wrapper or fallback to tqdm
        if progress_wrapper:
            iterator = progress_wrapper(batch_combinations)
        else:
            iterator = tqdm(
                batch_combinations,
                desc=f"{desc} ({','.join(batch_dims)})",
            )

        for combination in iterator:
            # Build slicers for this combination
            current_slicers = fixed_dims.copy()
            for i, dim in enumerate(batch_dims):
                current_slicers[dim] = combination[i]

            # Extract the chunk
            chunk = xarray.isel(current_slicers, drop=False).compute()

            # Preserve original dtype from dask/xarray to prevent float64 promotion
            if hasattr(chunk, "dtype") and chunk.dtype != xarray.dtype:
                chunk = chunk.astype(xarray.dtype)

            # Build array indices in xarray.dims order
            array_indices = [slice(None)] * len(xarray.dims)
            for i, dim in enumerate(batch_dims):
                # Map this batch dimension to its position in xarray.dims
                pos = dim_positions[dim]
                # Get the result array index for this original index
                array_indices[pos] = index_maps[dim][combination[i]]

            # For fixed dimensions, use index 0
            for dim in fixed_dims:
                pos = dim_positions[dim]
                array_indices[pos] = 0

            result_array[tuple(array_indices)] = chunk

        # No transpose needed - array is already in correct order!
        logger.debug(f"Final result shape: {result_array.shape}")
        return result_array

    @staticmethod
    def build_slicer_dict(
        position=None, channel=None, time=None, z=None, dimensions=None
    ):
        """Build slicer dictionary from individual dimension selections."""
        slicers = {}

        if dimensions is None:
            if position is not None:
                slicers["P"] = position
            if channel is not None:
                slicers["C"] = channel
            if time is not None:
                slicers["T"] = time
            if z is not None:
                slicers["Z"] = z
            return slicers

        # Handle each dimension
        if "P" in dimensions:
            if position is None:
                slicers["P"] = (0, dimensions["P"]["size"] - 1)
            else:
                slicers["P"] = position

        if "C" in dimensions:
            if channel is None:
                slicers["C"] = (0, dimensions["C"]["size"] - 1)
            else:
                slicers["C"] = channel

        if "T" in dimensions:
            if time is None:
                slicers["T"] = (0, dimensions["T"]["size"] - 1)
            else:
                slicers["T"] = time

        if "Z" in dimensions:
            if z is None:
                slicers["Z"] = (0, dimensions["Z"]["size"] - 1)
            else:
                slicers["Z"] = z

        logger.debug(f"Built slicer dict: {slicers}")
        return slicers

    @staticmethod
    def ensure_5d_structure(data) -> tuple:
        """Ensure data has the expected 5D structure (T, P, C, Y, X)."""
        logger.debug(f"Ensuring 5D structure for data with shape: {data.shape}")

        if len(data.shape) == 5:
            shape_order = list(data.shape)
        elif len(data.shape) == 3:
            t, y, x = data.shape
            shape_order = [t, 1, 1, y, x]
        elif len(data.shape) == 4:
            dims = list(data.shape)
            if dims[1] in [1, 2, 3, 4]:
                t, c, y, x = dims
                shape_order = [t, 1, c, y, x]
            else:
                t, p, y, x = dims
                shape_order = [t, p, 1, y, x]
        else:
            while len(data.shape) < 5:
                data = np.expand_dims(data, axis=0)
            return data

        if len(data.shape) != len(shape_order):
            logger.debug(f"Reshaping from {data.shape} to {shape_order}")
            data = data.reshape(shape_order)

        logger.debug(f"Final data shape: {data.shape}")
        return data

    @staticmethod
    def get_dimension_limits(dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """Get the maximum valid index for each available dimension."""
        limits = {}
        for axis, dim_info in dimensions.items():
            limits[axis] = dim_info["size"] - 1
            logger.debug(f"Dimension {axis} limit: {limits[axis]}")
        return limits

    @staticmethod
    def get_dimension_info_text(dimensions: Dict[str, Dict[str, Any]]) -> str:
        """Format dimension information for display."""
        lines = []
        lines.append("=== Dimension Details ===")
        for axis, dim_info in dimensions.items():
            lines.append(f"Axis {axis}:")
            lines.append(f"  Size: {dim_info['size']}")
            if dim_info["labels"]:
                labels_text = dim_info["labels"][:5]
                labels_text += "..." if len(dim_info["labels"]) > 5 else ""
                lines.append(f"  Labels: {labels_text}")
            lines.append("")
        return "\n".join(lines)
