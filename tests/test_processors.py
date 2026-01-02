"""
Tests for the processor modules.
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Add src package to path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nd2_utils.processors.nd2_processor import load_file
from nd2_utils.utils.metadata import MetadataHandler
from nd2_utils.utils.dimensions import DimensionParser


class TestMetadataHandler(unittest.TestCase):
    """Test the metadata handler utility."""

    def test_convert_attrs_to_dict_dataclass(self):
        """Test converting dataclass attributes to dict."""

        class MockDataclass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = "value2"

        mock_attrs = MockDataclass()
        result = MetadataHandler.convert_attrs_to_dict(mock_attrs)

        expected = {"attr1": "value1", "attr2": "value2"}
        self.assertEqual(result, expected)

    def test_convert_attrs_to_dict_namedtuple(self):
        """Test converting namedtuple attributes to dict."""
        from collections import namedtuple

        MockNamedTuple = namedtuple("MockNamedTuple", ["attr1", "attr2"])
        mock_attrs = MockNamedTuple("value1", "value2")

        result = MetadataHandler.convert_attrs_to_dict(mock_attrs)

        expected = {"attr1": "value1", "attr2": "value2"}
        self.assertEqual(result, expected)

    def test_convert_attrs_to_dict_dict(self):
        """Test converting dict attributes to dict."""
        mock_attrs = {"attr1": "value1", "attr2": "value2"}

        result = MetadataHandler.convert_attrs_to_dict(mock_attrs)

        expected = {"attr1": "value1", "attr2": "value2"}
        self.assertEqual(result, expected)

    def test_extract_pixel_size(self):
        """Test extracting pixel size information."""

        class MockPixelSize:
            def __init__(self):
                self.x = 0.1
                self.y = 0.2
                self.z = 0.5

        class MockAttrs:
            def __init__(self):
                self.pixelSizeUm = MockPixelSize()

        mock_attrs = MockAttrs()
        result = MetadataHandler.extract_pixel_size(mock_attrs)

        expected = {"x": 0.1, "y": 0.2, "z": 0.5}
        self.assertEqual(result, expected)

    def test_extract_channel_names(self):
        """Test extracting channel names."""

        class MockAttrs:
            def __init__(self):
                self.channelNames = ["DAPI", "GFP", "RFP"]

        mock_attrs = MockAttrs()
        result = MetadataHandler.extract_channel_names(mock_attrs, 3)

        expected = ["DAPI", "GFP", "RFP"]
        self.assertEqual(result, expected)

    def test_extract_channel_names_default(self):
        """Test extracting channel names with default fallback."""

        class MockAttrs:
            pass

        mock_attrs = MockAttrs()
        result = MetadataHandler.extract_channel_names(mock_attrs, 2)

        expected = ["Channel 0", "Channel 1"]
        self.assertEqual(result, expected)


class TestDimensionParser(unittest.TestCase):
    """Test the dimension parser utility."""

    def test_parse_dimensions(self):
        """Test parsing dimensions from xarray mock."""
        mock_xarray = Mock()
        mock_xarray.dims = ["T", "C", "Y", "X"]
        mock_xarray.sizes = {"T": 10, "C": 3, "Y": 512, "X": 512}

        result = DimensionParser.parse_dimensions(mock_xarray)

        expected = {
            "T": {"size": 10, "labels": []},
            "C": {"size": 3, "labels": []},
            "Y": {"size": 512, "labels": []},
            "X": {"size": 512, "labels": []},
        }
        self.assertEqual(result, expected)

    def test_validate_dimension_selection(self):
        """Test validating dimension selections."""
        dimensions = {
            "T": {"size": 10},
            "C": {"size": 3},
            "P": {"size": 2},
            "Z": {"size": 5},
        }

        # Valid selections
        result = DimensionParser.validate_dimension_selection(
            dimensions, position=1, channel=2, time=5, z=3
        )
        expected = {"P": 1, "C": 2, "T": 5, "Z": 3}
        self.assertEqual(result, expected)

        # Invalid selections (out of range)
        result = DimensionParser.validate_dimension_selection(
            dimensions, position=5, channel=10, time=15, z=20
        )
        expected = {}  # All invalid, should be empty
        self.assertEqual(result, expected)

    def test_ensure_5d_structure(self):
        """Test ensuring 5D structure for data."""
        # Already 5D
        data_5d = np.ones((2, 3, 4, 512, 512))
        result = DimensionParser.ensure_5d_structure(data_5d)
        self.assertEqual(result.shape, (2, 3, 4, 512, 512))

        # Less than 5D
        data_3d = np.ones((4, 512, 512))
        result = DimensionParser.ensure_5d_structure(data_3d)
        self.assertEqual(result.shape, (4, 1, 1, 512, 512))

    def test_get_dimension_limits(self):
        """Test getting dimension limits."""
        dimensions = {"T": {"size": 10}, "C": {"size": 3}, "P": {"size": 2}}

        result = DimensionParser.get_dimension_limits(dimensions)
        expected = {"T": 9, "C": 2, "P": 1}
        self.assertEqual(result, expected)


class TestND2Processor(unittest.TestCase):
    """Test the ND2 processor."""

    @patch("nd2_utils.processors.nd2_processor.nd2")
    def test_load_file_success(self, mock_nd2):
        """Test successful file loading."""
        # Setup mocks
        mock_xarray = Mock()
        mock_xarray.shape = (10, 3, 512, 512)
        mock_xarray.size = 10 * 3 * 512 * 512
        mock_xarray.dtype = "uint16"
        mock_xarray.dims = ["T", "C", "Y", "X"]
        mock_xarray.attrs = {"metadata": {"attributes": {}}}

        mock_nd2.imread.return_value = mock_xarray

        # Test loading
        result = load_file("/test/file.nd2")

        # Verify result structure
        self.assertIn("path", result)
        self.assertIn("shape", result)
        self.assertIn("dimensions", result)
        self.assertEqual(result["path"], "/test/file.nd2")

        # Verify nd2.imread was called correctly
        mock_nd2.imread.assert_called_once_with(
            "/test/file.nd2", xarray=True, dask=True
        )


class TestTiffExporter(unittest.TestCase):
    """Test the TIFF exporter."""

    @patch("nd2_utils.processors.tiff_exporter.tifffile")
    @patch("nd2_utils.processors.tiff_exporter.nd2")
    @patch("nd2_utils.processors.nd2_processor.load_file")
    def test_export_file_success(self, mock_load_file, mock_nd2, mock_tifffile):
        """Test successful file export."""
        from nd2_utils.processors.tiff_exporter import export_to_tiff

        # Setup mocks
        mock_info = {
            "path": "/test/input.nd2",
            "dimensions": {"T": {"size": 10}, "P": {"size": 1}, "C": {"size": 3}},
            "xarray": MagicMock(),
            "attributes": {},
        }
        mock_load_file.return_value = mock_info

        with patch("nd2_utils.processors.nd2_processor.extract_subset") as mock_extract:
            mock_extract.return_value = np.ones((10, 1, 3, 512, 512), dtype=np.uint16)

            with patch("nd2_utils.processors.tiff_exporter.write_tiff") as mock_write:
                # Test export
                result = export_to_tiff("/test/input.nd2", "/test/output.ome.tif")

                # Verify result
                self.assertEqual(result, "/test/output.ome.tif")

                # Verify write_tiff was called
                mock_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
