# ND2 Utils

Utility tools for working with ND2 files and exporting to OME-TIFF format.

## Features

- Load and visualize ND2 microscopy files
- Export ND2 files to OME-TIFF format
- Dimension-based subset extraction
- GUI and programmatic interfaces

## Installation

```bash
pip install nd2-utils
```

Or install from source:

```bash
git clone <repository-url>
cd nd2-utils
pip install -e .
```

## Usage

### GUI Application

```bash
nd2-gui
```

After installation in development mode:

```bash
uv pip install -e .
nd2-gui
```

### Programmatic Usage

```python
from nd2_utils.processors import ND2Processor, TiffExporter

# Load ND2 file
processor = ND2Processor()
info = processor.load_file("path/to/file.nd2")

# Export to TIFF
exporter = TiffExporter()
exporter.export_file("input.nd2", "output.ome.tif")
```

## Project Structure

```
nd2-utils/
├── src/nd2_utils/          # Main package
│   ├── processors/         # Core processing logic
│   ├── gui/               # GUI components
│   ├── utils/             # Utilities
│   └── config.py          # Configuration
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── archive/               # Legacy files
├── main.py               # GUI entry point
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## Development

Install in development mode:

```bash
pip install -e .
```

Run tests:

```bash
python -m pytest tests/
```

## Dependencies

- nd2[tiff] - ND2 file reading
- PySide6 - GUI framework  
- tifffile - TIFF writing
- numpy - Numerical operations
- xarray - Array handling
- dask - Parallel processing

## License

[Add your license here]
