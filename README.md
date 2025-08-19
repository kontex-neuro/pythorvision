# PyThorVision

**PyThorVision** is a Python client for communicating with a XDAQ server, designed to manage camera streams and recordings.

## Features

PythorVision features **High-level API** with simple interface for managing camera streams and recordings.
- **Camera Discovery**: List available cameras and their capabilities.
- **Flexible Stream Selection**: Select stream capabilities (media type, format, resolution, framerate).
- **GStreamer-based Recording**: Record video streams into split `.mkv` files using GStreamer.

## Requirements

- **Python**: Python 3.6 or higher is required.
- **Dependencies**:
    - **GStreamer**: Must be installed on the client machine, and `gst-launch-1.0` must be available in the system's PATH.
        - You can download GStreamer from [gstreamer.freedesktop.org/download](https://gstreamer.freedesktop.org/download).

        - **Windows**:
            1. Download and run the runtime installer.
            2. Add the `bin` directory of your GStreamer installation (e.g., `C:\gstreamer\1.0\msvc_x86_64\bin`) to your system's `Path` environment variable.

        - **macOS**:
            - The recommended way to install is using [Homebrew](https://brew.sh/):
              ```bash
              brew install gstreamer
              ```
            - Alternatively, you can download and run the runtime installer from the GStreamer website. If you use the installer, you may need to manually add GStreamer to your PATH:
              ```bash
              export PATH=/Library/Frameworks/GStreamer.framework/Versions/Current/bin:$PATH
              ```

## Installation

To install PyThorVision, you can use `pip` in project root directory:

```bash
pip install .
```

This will install the package and its required Python dependencies.

## Tutorial

This tutorial demonstrates how to use `XdaqClient` to connect to the server, start and record streams from cameras, and then clean up the resources.

### Run the Example Script

Run the example script from your terminal:

   ```bash
   python ./examples/run_two_cams.py
   ```

This example script demonstrates how to:
- Connect to the XDAQ server
- List available cameras and their capabilities
- Start recording streams from up to 2 cameras
- Record for a short period
- Properly clean up resources

You should see output detailing the camera capabilities, the selected streams, and recording status. The recorded `.mkv` video files will be saved in the `recordings/` directory.

## API Documentation

For complete API documentation, visit: [https://kontex-neuro.github.io/PyThorVision/](https://kontex-neuro.github.io/PyThorVision/)