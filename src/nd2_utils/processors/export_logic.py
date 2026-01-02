import logging
import os
from typing import Any, Dict, Optional, Callable, Iterable
import nd2
import numpy as np

from ..utils.dimensions import DimensionParser
from ..core.signals import SignalsInterface, DefaultSignals
from ..core.worker import OperationCancelled
from . import nd2_processor

logger = logging.getLogger(__name__)

class TiffExportLogic:
    @staticmethod
    def export(
        nd2_path: str,
        output_path: str,
        position: Optional[tuple] = None,
        channel: Optional[tuple] = None,
        time: Optional[tuple] = None,
        z: Optional[tuple] = None,
        signals: Optional[SignalsInterface] = None,
        check_cancelled: Optional[Callable[[], None]] = None,
        progress_wrapper: Optional[Callable[[Iterable], Iterable]] = None
    ) -> str:
        if signals is None:
            signals = DefaultSignals()
            
        def _check():
            if check_cancelled:
                check_cancelled()

        try:
            _check()
            logger.info("Starting export process")
            signals.progress.emit(10)

            _check()
            # Load ND2 file
            logger.debug("Calling nd2.imread with xarray=True, dask=True")
            my_array = nd2.imread(nd2_path, xarray=True, dask=True)
            logger.debug(f"Successfully loaded ND2 file with shape: {my_array.shape}")

            signals.progress.emit(20)

            _check()
            # Extract metadata
            logger.debug("Extracting metadata from xarray attrs")
            attrs = my_array.attrs.get("metadata", {})
            nd2_attrs = attrs.get("attributes", {})

            # Convert attributes if needed
            if not isinstance(nd2_attrs, dict) and hasattr(nd2_attrs, "__dict__"):
                nd2_attrs_dict = vars(nd2_attrs)
            else:
                nd2_attrs_dict = nd2_attrs if isinstance(nd2_attrs, dict) else {}

            signals.progress.emit(40)

            _check()
            # Extract data using slicer-based batched processing
            logger.debug("Extracting data with slicer-based batched processing")
            dimensions = DimensionParser.parse_dimensions(my_array)

            # Build slicer dictionary - unselected dimensions become full ranges
            slicers = DimensionParser.build_slicer_dict(
                position=position,
                channel=channel,
                time=time,
                z=z,
                dimensions=dimensions,
            )

            # Extract data
            data = DimensionParser.extract_data_with_progress(
                my_array, slicers, desc="Extracting data", progress_wrapper=progress_wrapper
            )
            logger.debug(f"Extracted data with shape: {data.shape}")

            _check()
            # Ensure proper data type
            if not isinstance(data, np.ndarray):
                logger.warning(f"Data is still not numpy array (type: {type(data)}), converting")
                data = np.asarray(data)

            signals.progress.emit(60)

            _check()
            # Convert data type if needed - preserve uint16 if possible
            logger.debug(f"Input data dtype: {data.dtype}")

            if data.dtype not in [np.uint8, np.uint16, np.float32]:
                if data.dtype == np.float64:
                    logger.debug(f"Converting data type from {data.dtype} to uint16")
                    data_max = np.nanmax(data)
                    if data_max > 0:
                        data = (data / data_max * 65535).astype(np.uint16)
                    else:
                        data = np.zeros_like(data, dtype=np.uint16)
                elif data.dtype.kind != "f":
                    data = data.astype(np.uint16)
                else:
                    pass
            logger.debug(f"Final data dtype: {data.dtype}")

            signals.progress.emit(80)

            _check()
            # Write TIFF file
            TiffExportLogic._write_tiff_file(output_path, nd2_path, data, nd2_attrs_dict)

            signals.progress.emit(90)
            signals.finished.emit(output_path)
            return output_path

        except OperationCancelled:
            logger.debug("TIFF export cancelled")
            signals.error.emit("Export cancelled")
            raise
        except Exception as e:
            logger.exception(f"Error during export: {e}")
            signals.error.emit(f"Error exporting to TIFF: {str(e)}")
            raise

    @staticmethod
    def _write_tiff_file(output_path: str, nd2_path: str, data: np.ndarray, nd2_attrs: Dict[str, Any]):
        """Write the data to a TIFF file."""
        logger.info(f"Writing TIFF file to: {output_path}")

        # Ensure data is contiguous
        data = np.ascontiguousarray(data)
        logger.debug(f"Final data shape: {data.shape}, dtype: {data.dtype}")

        # Handle data type conversion
        if data.dtype not in [np.uint8, np.uint16, np.float32]:
            logger.debug(f"Converting data type from {data.dtype} to uint16")
            if data.dtype.kind == "f":
                data_max = np.nanmax(data)
                if data_max > 0:
                    data = (data / data_max * 65535).astype(np.uint16)
                else:
                    data = np.zeros_like(data, dtype=np.uint16)
            else:
                data = data.astype(np.uint16)
            logger.debug(f"Converted data to dtype: {data.dtype}")

        # Get dimensions
        if len(data.shape) == 5:
            t, p, c, y, x = data.shape
        else:
            raise ValueError(f"Expected 5D data, got {data.shape}")

        logger.info(f"Exporting with dimensions T={t}, P={p}, C={c}, Y={y}, X={x}")

        # Build OME metadata from ND2 attributes
        metadata = nd2_processor.build_ome_metadata(
            nd2_attrs, os.path.basename(nd2_path)
        )

        # Write TIFF file with metadata
        nd2_processor.write_tiff(output_path, data, metadata)
