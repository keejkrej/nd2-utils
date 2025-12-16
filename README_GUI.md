# ND2 to OME-TIFF Converter GUI (Legacy Documentation)

> **Note**: This documentation refers to the legacy monolithic GUI implementation located in `archive/nd2_gui_tool.py`. The current implementation uses a modern modular structure in the `src/` directory.

## Legacy Implementation Overview

The original monolithic PySide6 GUI tool for reading large ND2 files using the `nd2` package and exporting them as OME-TIFF files has been refactored into:
- **Modular architecture** with clear separation of concerns
- **Reusable components** for better maintainability
- **Standard src/ layout** following Python packaging best practices

## Current Modern Implementation

See the main [README.md](README.md) for current installation and usage instructions.

### Key Improvements
- **Code separation**: Business logic separated from UI components
- **Reduced boilerplate**: Common patterns extracted into reusable utilities
- **Better testability**: Components can be tested independently
- **Professional structure**: Follows Python packaging standards

For the legacy documentation below, the actual implementation was in `archive/nd2_gui_tool.py`.

## Features

- **Lazy loading**: Uses the `nd2` package's lazy loading capabilities for large files
- **Dimension display**: Shows all dimensions (Position, Scene, Channel, Time, Z-stack) of the ND2 file
- **Selective export**: Allows users to export specific positions/scenes/views or the entire file
- **Non-blocking operations**: File loading and export happen in background threads
- **Modern interface**: Clean PySide6 GUI with progress indicators

## Installation

1. Install UV package manager
2.Clone the `nd2` repository as a sibling to this repository
3. Set up the environment and install dependencies:

```bash
# Set up UV environment with Python 3.13
uv --python 3.13 sync

# Or install manually
pip install nd2[tiff] PySide6 tifffile numpy
```

## Usage

1. Run the GUI application:
```bash
uv run python nd2_gui_tool.py
```

Or with explicit project path:

```bash
uv --project . run python nd2_gui_tool.py
```

2. Click "Browse" to select an ND2 file
3. Click "Load File" to read the file metadata and dimensions
4. Review the file information in the "File Info" tab
5. In the "Export OME-TIFF" tab, optionally select specific dimensions:
   - Check dimension checkboxes to enable selection
   - Use spinboxes to choose specific positions/scenes/channels/etc.
6. Click "Browse" to select the output OME-TIFF file location
7. Click "Export to OME-TIFF" to convert the file

## Requirements

- Python 3.9+
- nd2 package (from https://github.com/tlambert03/nd2)
- PySide6
- tifffile
- numpy

## Notes

- The tool supports both legacy and modern ND2 file formats
- For large files, the lazy loading feature ensures memory efficiency
- If no specific dimensions are selected, the entire file will be exported
- The export functionality preserves metadata and pixel spacing information
