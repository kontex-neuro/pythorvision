# PyThorVision

**PyThorVision** is a Python client for communicating with a ThorVision server, designed to manage camera streams and recordings. It provides a simple, high-level API for listing cameras, selecting stream capabilities, and recording video streams into segmented `.mkv` files using GStreamer.

The client is designed for robustness, with automatic resource cleanup on exit and support for use as a context manager.

## Requirements

- **Python**: Python 3.6 or higher is required.
- **Dependencies**:
    - `requests`: For making HTTP requests to the ThorVision server.
    - `GStreamer`: Must be installed on the client machine and `gst-launch-1.0` must be in the system's PATH.

## Installation

To install PyThorVision, you can use `pip` in project root directory:

```bash
pip install .
```

This will install the package and its required Python dependencies.

## Tutorial

This tutorial demonstrates how to use `ThorVisionClient` to connect to the server, start and record a stream from a camera, and then clean up the resources.

### Run the Test Script

1.  Make sure the ThorVision server is running and accessible at `192.168.177.100`. You can ping it using `ping 192.168.177.100`.
2.  Run test script test.py from your terminal:

    ```bash
    python test.py
    ```

You should see output detailing the camera capabilities, the selected stream, and recording status. After 10 seconds, the script will finish, and the recording will be stopped. The recorded `.mkv` video file will be saved in the directory you specify.

## API Documentation

### `XdaqClient`

The main client for interacting with the ThorVision server.

#### `__init__(self, host: str = "192.168.177.100", port: int = 8000)`

- Initializes the client and establishes a connection to the server.

### Listing Cameras and Capabilities

#### `list_cameras(self) -> List[Camera]`

- Retrieves a list of all `Camera` objects available on the server.
- Each `Camera` object contains its `id`, `name`, and a list of `Capability` objects.

### Streaming and Recording

#### `start_stream_with_recording(self, camera: Camera, capability: Capability, **kwargs) -> Dict[str, Any]`

- Starts a stream on the server and launches a local GStreamer process to record it.
- `camera` (Camera): The `Camera` object to use.
- `capability` (Capability): The `Capability` object specifying the stream parameters.
- **Keyword Arguments:**
    - `output_dir` (str): Directory to save recording files.
    - `split_max_files` (int, optional): Max number of files before recycling. Defaults to `0` (no limit).
    - `split_max_time_sec` (int, optional): The maximum duration of each video segment in seconds. Defaults to `0` (no limit).
    - `split_max_size_mb` (int, optional): The maximum size of each video segment in megabytes. Defaults to `0` (no limit).
    - `gstreamer_debug` (bool, optional): If `True`, enables GStreamer debug logging to a file. Defaults to `False`.

### Managing Active Streams

#### `stop_stream(self, camera_id: int) -> Dict[str, Any]`

- Stops the GStreamer recording process and the stream on the server for the specified `camera_id`.

### Resource Management

#### `cleanup(self)`

- Stops all active streams and recordings and releases all associated resources. It's called automatically on script exit.