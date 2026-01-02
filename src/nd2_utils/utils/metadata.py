"""
Metadata handling utilities for ND2 files.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MetadataHandler:
    """Handles extraction and processing of ND2 metadata."""
    
    @staticmethod
    def convert_attrs_to_dict(attrs_obj: Any) -> Dict[str, Any]:
        """Convert ND2 attributes object to dictionary."""
        logger.debug(f"Converting attrs object of type: {type(attrs_obj)}")
        
        if hasattr(attrs_obj, '__dict__'):
            # Dataclass or object with attributes
            attributes_dict = vars(attrs_obj)
            logger.debug(f"Converted using vars(), got {len(attributes_dict)} items")
        elif hasattr(attrs_obj, '_asdict'):
            # NamedTuple
            attributes_dict = attrs_obj._asdict()
            logger.debug(f"Converted using _asdict(), got {len(attributes_dict)} items")
        else:
            # Try direct conversion or fallback
            try:
                attributes_dict = dict(attrs_obj) if attrs_obj else {}
                logger.debug(f"Converted using dict(), got {len(attributes_dict)} items")
            except (TypeError, ValueError):
                attributes_dict = {'raw_object': str(attrs_obj)}
                logger.warning("Could not convert attrs to dict, using string representation")
        
        return attributes_dict
    
    @staticmethod
    def extract_pixel_size(attrs_obj: Any) -> Dict[str, Any]:
        """Extract pixel size information from ND2 attributes."""
        logger.debug("Extracting pixel size")
        
        if not hasattr(attrs_obj, 'pixelSizeUm'):
            logger.debug("No pixel size information found")
            return {}
        
        pixel_size_obj = attrs_obj.pixelSizeUm
        logger.debug(f"pixelSizeUm type: {type(pixel_size_obj)}")
        
        if hasattr(pixel_size_obj, '__dict__'):
            pixel_size_dict = vars(pixel_size_obj)
        elif hasattr(pixel_size_obj, '_asdict'):
            pixel_size_dict = pixel_size_obj._asdict()
        else:
            # Try to get attributes directly
            try:
                pixel_size_dict = {
                    'x': getattr(pixel_size_obj, 'x', None),
                    'y': getattr(pixel_size_obj, 'y', None),
                    'z': getattr(pixel_size_obj, 'z', None),
                }
            except AttributeError:
                pixel_size_dict = {'raw_object': str(pixel_size_obj)}
        
        # Filter out None values
        result = {k: v for k, v in pixel_size_dict.items() if v is not None}
        logger.debug(f"Found pixel_size: {result}")
        return result
    
    @staticmethod
    def extract_channel_names(attrs_obj: Any, channel_count: int) -> list:
        """Extract channel names from ND2 attributes."""
        logger.debug("Extracting channel names")
        
        if hasattr(attrs_obj, 'channelNames') and attrs_obj.channelNames:
            channels = list(attrs_obj.channelNames[:channel_count])
            logger.debug(f"Found channel names: {channels}")
            return channels
        
        channels = [f"Channel {i}" for i in range(channel_count)]
        logger.debug(f"Created default channel names: {channels}")
        return channels
    
    @staticmethod
    def build_info_dict(file_path: str, xarray, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive information dictionary from ND2 data."""
        logger.debug("Building information dictionary")
        
        # Get attributes object
        nd2_attrs = attrs.get('attributes', {})
        
        # Convert attributes to dict
        attributes_dict = MetadataHandler.convert_attrs_to_dict(nd2_attrs)
        
        # Extract pixel size
        pixel_size = MetadataHandler.extract_pixel_size(nd2_attrs)
        
        # Build base info
        info = {
            'path': file_path,
            'shape': xarray.shape,
            'size': xarray.size,
            'dtype': str(xarray.dtype),
            'axes': list(xarray.dims),
            'metadata': attrs.get('metadata', {}),
            'is_legacy': False,  # Can't easily determine from xarray alone
            'frame_count': 0,     # Can't easily determine from xarray alone
            'attributes': attributes_dict,
            'xarray': xarray,      # Store the actual xarray for later use
            'pixel_size': pixel_size,
        }
        
        logger.debug(f"Built info dictionary with keys: {list(info.keys())}")
        return info
