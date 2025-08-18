# PyThorVision

**PyThorVision** is a Python client for communicating with a ThorVision server, designed to manage camera streams and recordings. It provides a simple, high-level API for listing cameras, selecting stream capabilities, and recording video streams into segmented `.mkv` files using GStreamer.

The client is designed for robustness, with automatic resource cleanup on exit and support for use as a context manager.

## Requirements

- **Python**: Python 3.6 or higher is required.
- **Dependencies**:
    - `requests`: For making HTTP requests to the ThorVision server.
    - `GStreamer`: Must be installed on the client machine and `gst-launch-1.0` must be in the system's PATH.
      - To download GStreamer please go to https://gstreamer.freedesktop.org/download/#windows

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
   python examples/run_2_cams.py
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