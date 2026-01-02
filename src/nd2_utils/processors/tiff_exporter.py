"""
TIFF export module for ND2 to TIFF conversion.
"""

import logging
import os
from typing import Any, Dict, Optional

import nd2
import numpy as np

from ..utils.dimensions import DimensionParser
from ..utils.threading import BaseWorkerThread, OperationCancelled
from . import nd2_processor
from .export_logic import TiffExportLogic

logger = logging.getLogger(__name__)


# Module-level functions for TIFF export operations remain for backward compatibility

def export_to_tiff(
    nd2_path: str,
    output_path: str,
    position: Optional[tuple] = None,
    channel: Optional[tuple] = None,
    time: Optional[tuple] = None,
    z: Optional[tuple] = None,
) -> str:
    """Export ND2 file to TIFF format."""
    return TiffExportLogic.export(
        nd2_path=nd2_path,
        output_path=output_path,
        position=position,
        channel=channel,
        time=time,
        z=z
    )


def write_tiff(output_path: str, data_5d: np.ndarray, metadata: Dict[str, Any]):
    """Write 5D data (T, P, C, Y, X) to 4D TIFF with flattened P×C dimensions."""
    from tifffile import imwrite

    shape = data_5d.shape
    t, p, c, y, x = shape

    # Flatten P×C dimensions for ImageJ compatibility (TCYX format)
    new_shape = (t, p * c, y, x)
    data_to_write = data_5d.reshape(new_shape)

    # Add axes to metadata
    tiff_metadata = metadata.copy()
    tiff_metadata["axes"] = "TCYX"

    # Write BigTIFF file
    imwrite(output_path, data_to_write, bigtiff=True, metadata=tiff_metadata, ome=True)

    logger.info(
        f"Successfully wrote TIFF file with shape: {data_to_write.shape} (T={t}, C={p * c}, Y={y}, X={x})"
    )


class TiffExporter(BaseWorkerThread):
    """Worker thread for exporting ND2 files to TIFF format."""

    def __init__(
        self,
        nd2_path: str,
        output_path: str,
        position: Optional[tuple] = None,
        channel: Optional[tuple] = None,
        time: Optional[tuple] = None,
        z: Optional[tuple] = None,
    ):
        super().__init__()
        self.nd2_path = nd2_path
        self.output_path = output_path
        self.position = position
        self.channel = channel
        self.time = time
        self.z = z

    def run(self):
        """Export ND2 file to TIFF format."""
        try:
            TiffExportLogic.export(
                nd2_path=self.nd2_path,
                output_path=self.output_path,
                position=self.position,
                channel=self.channel,
                time=self.time,
                z=self.z,
                signals=self,
                check_cancelled=self._check_cancelled
            )
        except OperationCancelled:
            pass
        except Exception:
            # Error signal emitted by TiffExportLogic
            pass
