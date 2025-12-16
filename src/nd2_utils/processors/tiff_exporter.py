"""
TIFF export module for ND2 to OME-TIFF conversion.
"""

import os
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

try:
    import tifffile
    TIFFFILE_AVAILABLE = True
except ImportError:
    logger.error("tifffile package not available")
    TIFFFILE_AVAILABLE = False


class TiffExporter(BaseWorkerThread):
    """Worker thread for exporting ND2 files to OME-TIFF format."""
    
    def __init__(self, nd2_path: str, output_path: str, 
                 position: Optional[tuple] = None,
                 channel: Optional[tuple] = None,
                 time: Optional[tuple] = None,
                 z: Optional[tuple] = None):
        super().__init__()
        self.nd2_path = nd2_path
        self.output_path = output_path
        self.position = position  # Can be None, (start, end), or (value, value)
        self.channel = channel    # Can be None, (start, end), or (value, value)
        self.time = time          # Can be None, (start, end), or (value, value)
        self.z = z              # Can be None, (start, end), or (value, value)
    
    def run(self):
        """Export ND2 file to OME-TIFF format."""
        try:
            self._check_cancelled()
            logger.info("Starting export process")
            
            if not ND2_AVAILABLE:
                raise ImportError("nd2 package is not available")
            if not TIFFFILE_AVAILABLE:
                raise ImportError("tifffile package is not available")
            
            self.progress.emit(10)
            
            self._check_cancelled()
            # Load ND2 file
            logger.debug("Calling nd2.imread with xarray=True, dask=True")
            my_array = nd2.imread(self.nd2_path, xarray=True, dask=True)
            logger.debug(f"Successfully loaded ND2 file with shape: {my_array.shape}")
            
            self.progress.emit(20)
            
            self._check_cancelled()
            # Extract metadata
            logger.debug("Extracting metadata from xarray attrs")
            attrs = my_array.attrs.get('metadata', {})
            nd2_attrs = attrs.get('attributes', {})
            
            # Convert attributes if needed
            if not isinstance(nd2_attrs, dict) and hasattr(nd2_attrs, '__dict__'):
                nd2_attrs_dict = vars(nd2_attrs)
            else:
                nd2_attrs_dict = nd2_attrs if isinstance(nd2_attrs, dict) else {}
            
            self.progress.emit(40)
            
            self._check_cancelled()
            # Extract data using slicer-based batched processing
            logger.debug("Extracting data with slicer-based batched processing")
            dimensions = DimensionParser.parse_dimensions(my_array)
            
            # Build slicer dictionary - unselected dimensions become full ranges
            slicers = DimensionParser.build_slicer_dict(
                position=self.position,
                channel=self.channel,
                time=self.time,
                z=self.z,
                dimensions=dimensions
            )
            
            # Extract data using tqdm progress - tqdm handles its own progress display
            data = DimensionParser.extract_data_with_progress(
                my_array, slicers, desc="Extracting data"
            )
            logger.debug(f"Extracted data with shape: {data.shape}")
            
            self._check_cancelled()
            # Ensure proper data type
            if not isinstance(data, np.ndarray):
                logger.warning(f"Data is still not numpy array (type: {type(data)}), converting")
                data = np.asarray(data)
            
            self.progress.emit(60)
            
            # Data should already be 5D from extraction
            # No need to pad - ensure_5d_structure should only verify structure
            
            self._check_cancelled()
            # Convert data type if needed - preserve uint16 if possible
            logger.debug(f"Input data dtype: {data.dtype}")
            
            if data.dtype not in [np.uint8, np.uint16, np.float32]:
                if data.dtype == np.float64:
                    # If we got float64, convert to uint16 (likely from dask computation)
                    logger.debug(f"Converting data type from {data.dtype} to uint16")
                    data_max = np.nanmax(data)
                    if data_max > 0:
                        data = (data / data_max * 65535).astype(np.uint16)
                    else:
                        data = np.zeros_like(data, dtype=np.uint16)
                elif data.dtype.kind != 'f':
                    # For integer types other than uint8/uint16
                    data = data.astype(np.uint16)
                else:
                    # For float32 - keep as is
                    pass
            logger.debug(f"Final data dtype: {data.dtype}")
            
            self.progress.emit(80)
            
            self._check_cancelled()
            # Write TIFF file
            self._write_tiff_file(data, nd2_attrs_dict)
            
            self.progress.emit(90)
            self.finished.emit(self.output_path)
            
            # Clean exit - thread will be cleaned up by event loop
            return
            
        except OperationCancelled:
            logger.debug("TIFF export cancelled")
            self.error.emit("Export cancelled")
        except Exception as e:
            logger.exception(f"Error during export: {e}")
            self.error.emit(f"Error exporting to OME-TIFF: {str(e)}")
    
    def _write_tiff_file(self, data: np.ndarray, nd2_attrs: Dict[str, Any]):
        """Write the data to a TIFF file."""
        logger.info(f"Writing TIFF file to: {self.output_path}")
        
        # Ensure data is contiguous
        data = np.ascontiguousarray(data)
        logger.debug(f"Final data shape: {data.shape}, dtype: {data.dtype}")
        
        # Handle data type conversion
        if data.dtype not in [np.uint8, np.uint16, np.float32]:
            logger.debug(f"Converting data type from {data.dtype} to uint16")
            if data.dtype.kind == 'f':
                data_max = np.nanmax(data)
                if data_max > 0:
                    data = (data / data_max * 65535).astype(np.uint16)
                else:
                    data = np.zeros_like(data, dtype=np.uint16)
            else:
                data = data.astype(np.uint16)
            logger.debug(f"Converted data to dtype: {data.dtype}")
        
        # Get pixel size for metadata
        pixel_size_x = 1.0
        pixel_size_y = 1.0
        if isinstance(nd2_attrs, dict) and 'pixelSizeUm' in nd2_attrs:
            if 'x' in nd2_attrs['pixelSizeUm']:
                pixel_size_x = nd2_attrs['pixelSizeUm']['x']
            if 'y' in nd2_attrs['pixelSizeUm']:
                pixel_size_y = nd2_attrs['pixelSizeUm']['y']
        
        # Get dimensions
        if len(data.shape) == 5:
            t, p, c, y, x = data.shape
        else:
            raise ValueError(f"Expected 5D data, got {data.shape}")
        
        logger.info(f"Exporting with dimensions T={t}, P={p}, C={c}, Y={y}, X={x}")
        
        # Create metadata
        metadata = {
            'description': f'Exported from ND2 file: {os.path.basename(self.nd2_path)}'
        }
        
        # Use the wrapper method which handles all dimension collapsing
        self._write_5d_tiff(data, metadata, pixel_size_x, pixel_size_y)
    
    @staticmethod
    def export_file(nd2_path: str, output_path: str,
                   position: Optional[tuple] = None,
                   channel: Optional[tuple] = None,
                   time: Optional[tuple] = None,
                   z: Optional[tuple] = None) -> str:
        """Export ND2 file to OME-TIFF synchronously (for CLI usage)."""
        logger.debug(f"Exporting ND2 file synchronously: {nd2_path}")
        
        # Load and process using ND2Processor
        info = ND2Processor.load_file(nd2_path)
        data = ND2Processor.extract_subset(info, position, channel, time, z)
        
        # Data should already be 5D from extraction
        # No padding needed
        
        # Convert data type if needed
        if data.dtype not in [np.uint8, np.uint16, np.float32, np.float64]:
            logger.debug(f"Converting data type from {data.dtype} to uint16")
            if data.dtype.kind == 'f':
                data_max = np.nanmax(data)
                if data_max > 0:
                    data = (data / data_max * 65535).astype(np.uint16)
                else:
                    data = np.zeros_like(data, dtype=np.uint16)
            else:
                data = data.astype(np.uint16)
        
        # Write file
        from tifffile import imwrite
        metadata = {
            'description': f'Exported from ND2 file: {os.path.basename(nd2_path)}'
        }
        
        data = np.ascontiguousarray(data)
        imwrite(output_path, data, metadata=metadata, imagej=True, bigtiff=True)
        
        logger.info(f"Successfully exported to: {output_path}")
        return output_path
    
    def _write_5d_tiff(self, data_5d, metadata, pixel_size_x, pixel_size_y):
        """Write 5D data (T, P, C, Y, X) to TIFF, handling dimension collapsing internally.
        
        Args:
            data_5d: 5D numpy array with shape (T, P, C, Y, X)
            metadata: Metadata dictionary
            pixel_size_x: Pixel size in X direction (µm)
            pixel_size_y: Pixel size in Y direction (µm)
        """
        from tifffile import imwrite, TiffWriter
        import numpy as np
        
        # Collapse singleton dimensions intelligently
        shape = data_5d.shape
        t, p, c, y, x = shape
        
        # Determine what dimensions to keep
        dims_to_keep = []
        axis_labels = ['T', 'P', 'C', 'Y', 'X']
        
        for size, label in zip(shape, axis_labels):
            if size > 1 or label in ['Y', 'X']:  # Always keep Y, X
                dims_to_keep.append(label)
        
        # Flatten P into C for ImageJ compatibility (TCYX format)
        # New shape: (T, P*C, Y, X)
        new_shape = (t, p * c, y, x)
        data_to_write = data_5d.reshape(new_shape)
        axes = 'TCYX'
        
        try:
            # Try OME-TIFF format first
            ome_metadata = {
                'axes': axes,
                'signatures': 'nd2-utils',
                'Description': metadata.get('description', 'ND2 export'),
                'PhysicalSizeX': pixel_size_x,
                'PhysicalSizeXUnit': 'µm',
                'PhysicalSizeY': pixel_size_y,
                'PhysicalSizeYUnit': 'µm'
            }
            
            # Only add channel metadata if we have channels
            if p * c > 0:
                # Generate channel names in P-C format
                channel_names = []
                for pos in range(p):
                    for chan in range(c):
                        channel_names.append(f'{pos}-{chan}')
                
                ome_metadata['Channel'] = {
                    'Name': channel_names
                }
            
            # Remove None values
            ome_metadata = {k: v for k, v in ome_metadata.items() if v is not None}
            
            imwrite(
                self.output_path,
                data_to_write,
                metadata=ome_metadata,
                photometric='minisblack',
                bigtiff=True
            )
            logger.info(f"Successfully wrote OME-TIFF file with {len(data_to_write.shape)}D shape: {data_to_write.shape}")
            
        except Exception as e:
            logger.warning(f"OME-TIFF write failed ({e}), trying ImageJ format fallback")
            
            # Fall back to ImageJ compatible format
            with TiffWriter(self.output_path, bigtiff=True, imagej=True) as tif:
                # For ImageJ, we need to decide what format works best
                if len(data_to_write.shape) >= 3:
                    # Keep the existing shape if it's 3D or more
                    imgj_metadata = {
                        'description': metadata.get('description', 'ND2 export'),
                        'axes': 'TYX' if len(data_to_write.shape) == 3 else 'TCYX'
                    }
                    return
                else:
                    # Flatten everything to 2D as last resort
                    flattened = data_to_write.reshape(-1, y, x)
                    imgj_metadata = {
                        'description': metadata.get('description', 'ND2 export'),
                        'axes': 'YX'
                    }
                    tif.write(flattened, metadata=imgj_metadata)
                    logger.info(f"Successfully flattened to ImageJ 2D TIFF with shape: {flattened.shape}")
