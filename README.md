
### Streaming and Recording

**`start_stream_with_recording(self, camera_id: int, capability: str, **kwargs) -> Dict[str, Any]`**
- Starts a stream on the server and launches a local GStreamer process to record it into segmented `.mkv` files.
- `camera_id` (int): The ID of the camera to use.
- `capability` (str): A formatted capability string from `format_camera_capabilities`. This method is primarily designed for `image/jpeg` capabilities.
- `output_dir` (str, optional): Directory to save recording files. Defaults to `./recordings`.
- `max_size_time` (int, optional): The maximum duration of each video segment in seconds. Defaults to `3600` (1 hour).
- `max_size_bytes` (int, optional): The maximum size of each video segment in bytes. Defaults to `2000000000` (2GB).
- `gstreamer_log` (str, optional): Controls GStreamer's logging. Can be `'console'`, `'file'`, or `'none'`. Defaults to `'file'`.

### Managing Active Streams

**`stop_stream(self, camera_id: int) -> Dict[str, Any]`**
- Stops the GStreamer recording process and sends a request to the server to stop the stream for the specified `camera_id`.

**`list_active_streams(self) -> Dict[int, Dict[str, Any]]`**
- Returns a dictionary of all streams currently being managed by the client instance, showing their port, recording status, and output path.

### Resource Management

**`cleanup(self)`**
- Stops all active streams and recordings and releases all associated resources. This method is called automatically on program exit or when the `with` statement context is exited. Manual invocation is generally not required if using the context manager.