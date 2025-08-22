# pythorvision

`pythorvision` is a python package as client API for communicating with **XDAQ** video streaming subsystem -- **ThorVision**, designed to manage camera streams and recordings.

## Features

**pythorvision** features **High-level API** with simple interface for managing camera streams and recordings.
- **Camera Discovery**: List available cameras and their capabilities.
- **Flexible Stream Selection**: Select stream capabilities:
  - media type (MJPEG)
  - format
  - resolution
  - framerate
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

To install **pythorvision**, you can use `pip` in project root directory:

```bash
pip install .
```

This will install the package and its required Python dependencies.

## Tutorial

This tutorial demonstrates how to use `ThorVisionClient` to connect to the server, start and record streams from cameras, and then clean up the resources.

### Run the Example Scripts

#### Record Video from Two Cameras

Run the following script to record from the first two available cameras for 10 seconds:

```bash
python ./examples/run_two_cams.py
```

The recorded `.mkv` video files will be saved in the `recordings/` directory.

#### Extract Metadata from a Video File

If you have a pre-recorded video, you can extract its frame metadata using this script:

```bash
python ./examples/extract_video_metadata.py "path/to/your/video.mkv"
```

#### Record and Immediately Extract Metadata

This script provides a complete end-to-end example of recording a short video and then immediately parsing it to display its metadata.

```bash
python ./examples/record_and_extract.py
```

## API Documentation

For complete API documentation, visit: [https://kontex-neuro.github.io/pythorvision/](https://kontex-neuro.github.io/pythorvision/)