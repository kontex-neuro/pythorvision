# pythorvision/client.py
import requests
import subprocess
import os
import signal
import time
import sys
import atexit
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

class ThorVisionClient:
    """Client for communicating with the ThorVision server."""
    
    def __init__(self, host: str = "192.168.177.100", port: int = 8000):
        """
        Initialize the ThorVision client.
        
        Args:
            host: Server hostname or IP address
            port: Server port
        """
        self._host = host
        self.base_url = f"http://{host}:{port}"
        self.active_streams = {}  # Track active streams: {port: camera_id}
        self.camera_to_port = {}  # Track which port is used by each camera: {camera_id: port}
        self.gstreamer_processes = {}  # Track GStreamer processes: {camera_id: process}
        self.gstreamer_log_files = {} # Track GStreamer log file handles
        self.output_paths = {}  # Track output file paths: {camera_id: path}
        self._cleanup_done = False  # Flag to prevent multiple cleanups
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
        # Register signal handlers for graceful termination
        if os.name == 'nt':  # Windows
            # Windows supports SIGINT (Ctrl+C) and SIGTERM
            # By not handling SIGINT, we allow Python's default KeyboardInterrupt
            # to be raised, which is handled correctly by atexit and __exit__.
            signal.signal(signal.SIGTERM, self._signal_handler)
        else:  # Unix/Linux/Mac
            # Unix supports more signals
            # We do the same for Unix-like systems regarding SIGINT.
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals by cleaning up resources."""
        print(f"Signal {sig} received, cleaning up resources...")
        self.cleanup()
        # Don't exit here, let the main program decide what to do after cleanup
    
    def __enter__(self):
        """Support for context manager (with statement)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context manager."""
        self.cleanup()
        return False  # Don't suppress exceptions
    
    def list_cameras(self) -> List[Dict[str, Any]]:
        """
        Get a list of available cameras.
        
        Returns:
            List of camera information dictionaries
        """
        response = requests.get(f"{self.base_url}/cameras")
        response.raise_for_status()
        return response.json()
    
    def format_camera_capabilities(self, cameras: Optional[List[Dict[str, Any]]] = None) -> Dict[int, List[str]]:
        """
        Format and print camera capabilities, and return formatted capability strings.
        Only displays 'image/jpeg' and 'video/x-raw' media types.
        
        Args:
            cameras: List of camera information dictionaries. If None, fetches cameras.
            
        Returns:
            Dictionary mapping camera IDs to lists of formatted capability strings
        """
        if cameras is None:
            cameras = self.list_cameras()
        
        camera_capabilities = {}
        
        for camera in cameras:
            camera_id = camera.get("id")
            camera_name = camera.get("name")
            
            print(f"Camera {camera_id}: {camera_name}")
            print("-" * 40)
            
            # Group capabilities by media_type, format, width, height
            grouped_caps = defaultdict(list)
            formatted_caps = []
            
            for cap in camera.get("caps", []):
                media_type = cap.get("media_type")
                
                # Only process image/jpeg and video/x-raw media types
                if media_type not in ["image/jpeg", "video/x-raw"]:
                    continue
                
                format_val = cap.get("format", "")
                width = cap.get("width")
                height = cap.get("height")
                framerate = cap.get("framerate")
                
                # Create formatted capability string for stream API
                cap_str = f"{media_type},width={width},height={height},framerate={framerate}"
                if format_val:
                    cap_str = f"{media_type},format={format_val},width={width},height={height},framerate={framerate}"
                
                formatted_caps.append(cap_str)
                
                key = (media_type, format_val, width, height)
                grouped_caps[key].append(framerate)
            
            # Print grouped capabilities
            for (media_type, format_val, width, height), framerates in grouped_caps.items():
                if format_val:
                    print(f"{media_type}, format={format_val}, resolution={width}x{height}")
                else:
                    print(f"{media_type}, resolution={width}x{height}")
                
                # Print each framerate on a new line
                for fr in sorted(framerates, key=lambda x: int(x.split('/')[0])):
                    if format_val:
                        print(f"    {media_type},format={format_val},width={width},height={height},framerate={fr}")
                    else:
                        print(f"    {media_type},width={width},height={height},framerate={fr}")
            
            print()  # Empty line between cameras
            
            # Store formatted capabilities for this camera
            camera_capabilities[camera_id] = formatted_caps
            
        return camera_capabilities
    
    def start_stream_with_recording(self, camera_id: int, capability: str, 
                                   output_dir: str = "./recordings",
                                   max_size_time: int = 3600,
                                   max_size_bytes: int = 2000000000,
                                   gstreamer_log: str = 'file') -> Dict[str, Any]:
        """
        Start a JPEG stream for a camera with automatic port allocation and launch a GStreamer pipeline to record it.
        
        Args:
            camera_id: ID of the camera to stream
            capability: Formatted capability string (e.g., "image/jpeg,width=1280,height=720,framerate=30/1")
            output_dir: Directory to save recordings
            max_size_time: Maximum recording segment duration in seconds (default: 1 hour)
            max_size_bytes: Maximum recording segment size in bytes (default: 2GB)
            gstreamer_log: Logging for GStreamer. 'console' (default), 'file', or 'none'.
            
        Returns:
            Dictionary with stream and recording information
        """
        if "image/jpeg" not in capability:
            print(f"Warning: Capability {capability} is not JPEG format")
        
        # Check if camera is already streaming
        if camera_id in self.camera_to_port:
            existing_port = self.camera_to_port[camera_id]
            print(f"Camera {camera_id} is already streaming on port {existing_port}")
            return {"message": f"Camera {camera_id} already streaming on port {existing_port}"}
        
        # Get camera name for file naming
        cameras = self.list_cameras()
        camera_name = f"camera{camera_id}"
        for camera in cameras:
            if camera.get("id") == camera_id:
                camera_name = camera.get("name", f"camera{camera_id}")
                # Replace spaces and special characters with underscores
                camera_name = ''.join(c if c.isalnum() else '_' for c in camera_name)
                break
        
        # Auto-allocate port
        port = self.get_available_port()
        
        # Start the stream
        payload = {
            "id": camera_id,
            "port": port,
            "capability": capability
        }
        
        response = requests.post(f"{self.base_url}/jpeg", json=payload)
        response.raise_for_status()
        
        # Track this stream
        self.active_streams[port] = camera_id
        self.camera_to_port[camera_id] = port
        
        print(f"Started JPEG stream for camera {camera_id} on port {port}")
        print(f"Stream capability: {capability}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output file path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{camera_id}_{camera_name}_{timestamp}"
        output_filename = f"{base_filename}-%02d.mkv"
        output_path = os.path.join(output_dir, output_filename)
        self.output_paths[camera_id] = output_path
        
        # Convert Windows path to proper format for GStreamer
        # Use forward slashes instead of backslashes
        if os.name == 'nt':
            gst_output_path = output_path.replace('\\', '/')
        else:
            gst_output_path = output_path
        
        # Build GStreamer pipeline as a single command string
        # Add a `timeout` property to srtclientsrc to prevent premature disconnection.
        pipeline_cmd = f'gst-launch-1.0 -e srtclientsrc uri=srt://{self._host}:{port} latency=500 ! queue ! jpegparse ! splitmuxsink max-size-time={max_size_time * 1000000000} max-size-bytes={max_size_bytes} muxer-factory=matroskamux location={gst_output_path} '
        
        print(f"Running GStreamer command: {pipeline_cmd}")

        # Setup logging for subprocess
        log_file_path = None
        if gstreamer_log == 'none':
            stdout_dest = stderr_dest = subprocess.DEVNULL
        elif gstreamer_log == 'file':
            log_filename = f"{base_filename}.log"
            log_file_path = os.path.join(output_dir, log_filename)
            print(f"GStreamer logs will be saved to: {log_file_path}")
            log_file = open(log_file_path, 'w', buffering=1)
            self.gstreamer_log_files[camera_id] = log_file
            stdout_dest = stderr_dest = log_file
        elif gstreamer_log == 'console':
            stdout_dest = subprocess.PIPE
            stderr_dest = None  # Inherits from parent
        else:
            raise ValueError(f"Invalid gstreamer_log option: '{gstreamer_log}'. Use 'console', 'file', or 'none'.")
        
        # Launch GStreamer pipeline
        try:
            # Create a copy of the current environment and add GST_DEBUG
            env = os.environ.copy()
            env['GST_DEBUG'] = '3'

            # Use shell=True to handle the command as a single string
            process = subprocess.Popen(
                pipeline_cmd,
                stdout=stdout_dest,
                stderr=stderr_dest,
                text=True,
                bufsize=1,
                shell=True,  # Use shell mode for better handling of complex commands
                env=env
            )
            self.gstreamer_processes[camera_id] = process
            
            # Give GStreamer a moment to start
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                if gstreamer_log == 'console':
                    process.communicate()
                    error_msg = "Failed to start GStreamer. See console output for details."
                elif gstreamer_log == 'file':
                    error_msg = f"Failed to start GStreamer. Check log file at {log_file_path}."
                else: # 'none'
                    error_msg = "Failed to start GStreamer. Logging is disabled."

                self.stop_stream(camera_id)
                return {"error": error_msg}
            
            print(f"Started recording for camera {camera_id} to {output_path}")
            
            return {
                "camera_id": camera_id,
                "port": port,
                "capability": capability,
                "recording": True,
                "output_path": output_path
            }
            
        except Exception as e:
            print(f"Failed to start GStreamer: {e}")
            self.stop_stream(camera_id)
            return {"error": f"Failed to start GStreamer: {e}"}
    
    def stop_stream(self, camera_id: int) -> Dict[str, Any]:
        """
        Stop a stream and its associated GStreamer recording process.
        
        Args:
            camera_id: ID of the camera to stop streaming
            
        Returns:
            Server response
        """
        # Stop GStreamer process first if it exists
        process = self.gstreamer_processes.pop(camera_id, None)
        output_path = self.output_paths.pop(camera_id, None)
        log_file = self.gstreamer_log_files.pop(camera_id, None)
        
        if process:
            try:
                # Check if process is still running
                if process.poll() is None:
                    # Process is still running, try to terminate it gracefully
                    print(f"Terminating GStreamer process for camera {camera_id}...")
                    
                    if os.name == 'nt':  # Windows
                        print("Windows detected, attempting to kill GStreamer process tree...")
                        try:
                            # Use taskkill to terminate the entire process tree by PID.
                            # This is more reliable for processes started with shell=True.
                            subprocess.run(
                                ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                check=True, capture_output=True, text=True
                            )
                        except (FileNotFoundError, subprocess.CalledProcessError) as e:
                            print(f"taskkill failed: {e}. Falling back to process.kill().")
                            if process.poll() is None:
                                process.kill()
                    else:  # Unix/Linux/Mac
                        process.send_signal(signal.SIGINT)
                    
                    # Wait for process to terminate
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        print(f"Process didn't terminate gracefully, forcing kill...")
                        process.kill()
                        process.wait(timeout=2)  # Wait for the kill to complete
                    
                    # Capture any remaining output from stdout
                    process.communicate()

                else:
                    # Process already terminated
                    process.communicate()
                    
                print(f"Stopped recording for camera {camera_id}")
            except Exception as e:
                print(f"Error stopping GStreamer process: {e}")
            finally:
                if log_file:
                    log_file.close()

        elif log_file:
            # Defensive closing in case process is gone but file handle remains
            log_file.close()
        
        # Check if this camera is in our tracking before trying to stop it on the server
        if camera_id not in self.camera_to_port:
            print(f"No active stream found for camera {camera_id}")
            return {
                "message": "No active stream found",
                "camera_id": camera_id,
                "output_path": output_path
            }
        
        # Stop the stream
        port = self.camera_to_port.pop(camera_id, None)
        if port is not None:
            self.active_streams.pop(port, None)
        
        payload = {
            "id": camera_id
        }
        
        try:
            response = requests.post(f"{self.base_url}/stop", json=payload)
            response.raise_for_status()
            print(f"Stopped stream for camera {camera_id} on port {port}")
            return {
                "message": "Stream and recording stopped",
                "camera_id": camera_id,
                "output_path": output_path
            }
        except requests.exceptions.HTTPError as e:
            print(f"Server error details: {response.text}")
            print(f"Failed to stop stream on server, but local resources have been cleaned up")
            # Even if the server call fails, we've already cleaned up our local resources
            return {
                "message": "Stream recording stopped, but server reported an error",
                "camera_id": camera_id,
                "output_path": output_path,
                "error": str(e)
            }
    
    def get_available_port(self, start: int = 9001, end: int = 9099) -> int:
        """
        Get an available port for streaming that isn't currently in use.
        
        Args:
            start: Start of port range
            end: End of port range
            
        Returns:
            Available port number
            
        Raises:
            RuntimeError: If no ports are available
        """
        for port in range(start, end + 1):
            if port not in self.active_streams:
                return port
        
        raise RuntimeError(f"No available ports in range {start}-{end}")
    
    def list_active_streams(self) -> Dict[int, Dict[str, Any]]:
        """
        List all active streams and recordings.
        
        Returns:
            Dictionary mapping camera IDs to stream information
        """
        result = {}
        for camera_id, port in self.camera_to_port.items():
            result[camera_id] = {
                "port": port,
                "recording": camera_id in self.gstreamer_processes,
                "output_path": self.output_paths.get(camera_id, None)
            }
        return result

    def cleanup(self):
        """
        Clean up all resources and stop all active streams and recordings.
        Call this method when you're done using the client.
        """
        # Prevent multiple cleanups
        if self._cleanup_done:
            return
        
        self._cleanup_done = True
        
        # Make a copy of keys since we'll be modifying the dictionary during iteration
        camera_ids = list(self.camera_to_port.keys())
        
        for camera_id in camera_ids:
            try:
                self.stop_stream(camera_id)
            except Exception as e:
                print(f"Error stopping stream for camera {camera_id}: {e}")
        
        # Clear all tracking dictionaries
        self.active_streams.clear()
        self.camera_to_port.clear()
        self.gstreamer_processes.clear()
        self.gstreamer_log_files.clear()
        self.output_paths.clear()
        
        print("All resources cleaned up")