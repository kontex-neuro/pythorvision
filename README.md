# PyThorVision

**PyThorVision** is a Python client for communicating with a ThorVision server, designed to manage camera streams and recordings. It provides a simple, high-level API for listing cameras, selecting stream capabilities, and recording video streams into segmented `.mkv` files using GStreamer.

The client is designed for robustness, with automatic resource cleanup on exit and support for use as a context manager.

## Requirements

- **Platform**: The client is cross-platform and has been tested on both Windows and Unix-like systems (Linux, macOS).
- **Python**: Python 3.6 or higher is required.
- **Dependencies**:
    - `requests`: For making HTTP requests to the ThorVision server.
    - `GStreamer`: Must be installed on the client machine and `gst-launch-1.0` must be in the system's PATH.

## Installation

To install PyThorVision, you can use `pip`:

```bash
pip install <project_root>/pythorvision
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

You should see output detailing the camera capabilities, the selected stream, and recording status. After 60 seconds, the script will finish, and the recording will be stopped. The recorded `.mkv` file will be saved in the `recordings` directory.

## API Documentation



### Listing Cameras and Capabilities

**`list_cameras(self) -> List[Dict[str, Any]]`**

-   Retrieves a list of all cameras available on the server.
-   Returns a list of dictionaries, where each dictionary contains details about a camera.

**`format_camera_capabilities(self, cameras: Optional[List[Dict[str, Any]]] = None) -> Dict[int, List[str]]`**

-   Fetches and prints a human-readable, formatted list of capabilities for each camera, grouped by media type, format, and resolution.
-   It filters for and displays only `image/jpeg` and `video/x-raw` capabilities.
-   Returns a dictionary mapping each `camera_id` to a list of its formatted capability strings, which can be passed to the streaming methods.

### Streaming and Recording

**`start_stream_with_recording(self, camera_id: int, capability: str, **kwargs) -> Dict[str, Any]`**

-   Starts a stream on the server and launches a local GStreamer process to record it into segmented `.mkv` files.
-   `camera_id` (int): The ID of the camera to use.
-   `capability` (str): A formatted capability string from `format_camera_capabilities`. This method is primarily designed for `image/jpeg` capabilities.
-   **Keyword Arguments:**
    -   `output_dir` (str, optional): Directory to save recording files. Defaults to `./recordings`.
    -   `max_size_time` (int, optional): The maximum duration of each video segment in seconds. Defaults to `3600` (1 hour).
    -   `max_size_bytes` (int, optional): The maximum size of each video segment in bytes. Defaults to `2000000000` (2GB).
    -   `gstreamer_log` (str, optional): Controls GStreamer's logging. Can be `'console'`, `'file'`, or `'none'`. Defaults to `'file'`.

### Managing Active Streams

**`stop_stream(self, camera_id: int) -> Dict[str, Any]`**

-   Stops the GStreamer recording process and sends a request to the server to stop the stream for the specified `camera_id`.

**`list_active_streams(self) -> Dict[int, Dict[str, Any]]`**

-   Returns a dictionary of all streams currently being managed by the client instance, showing their port, recording status, and output path.

### Resource Management

**`cleanup(self)`**

-   Stops all active streams and recordings and releases all associated resources. This method is called automatically on program exit or when the `with` statement context is exited. Manual invocation is generally not required if using the context manager.