import subprocess
import os
import signal
import time
import shutil
import logging
import shlex
from datetime import datetime
from typing import List, Dict, Any, Optional
import io
from pathlib import Path
from pydantic import BaseModel, Field, PrivateAttr
from typing_extensions import Annotated
import requests

from .camera import Camera, Capability

logger = logging.getLogger(__name__)


class Stream(BaseModel):
    """Represents an active video stream and its associated resources.

    Attributes:
        camera (Camera): The camera being streamed.
        capability (Capability): The capability used for the stream.
        port (int): The network port used for the SRT stream.
        video_path (Path): The path to the recorded video file.
        gstreamer_pipeline (str): The GStreamer pipeline command used.
        process (subprocess.Popen): The Popen object for the running GStreamer
            process.
        gstreamer_log_file (Optional[io.TextIOBase]): The file handle for GStreamer logs.
        gstreamer_log_file_path (Optional[Path]): The path to the GStreamer
            log file.
        created_at (datetime): The timestamp when the stream was created.
    """
    camera: Camera
    capability: Capability
    port: int
    video_path: Path
    gstreamer_pipeline: str
    process: subprocess.Popen
    gstreamer_log_file: Optional[io.TextIOBase] = None
    gstreamer_log_file_path: Optional[Path] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class XdaqClient(BaseModel):
    """Client for interacting with the XDAQ server to manage camera streams.

    Attributes:
        host (str): The hostname or IP address of the XDAQ server.
        port (int): The port number of the XDAQ server.
        streams (Dict[int, Stream]): A dictionary of active streams, keyed by
            camera ID.
    """
    host: str = "192.168.177.100"
    port: int = 8000
    _base_url: str = PrivateAttr("")
    _gst_launch_path: str = PrivateAttr("")
    streams: Annotated[Dict[int, Stream], Field(default_factory=dict, repr=False)]

    def model_post_init(self, __context: Any) -> None:
        """Initialize the client after the model is created.

        This method sets up the base URL for the server and performs initial
        checks for server connectivity and GStreamer installation.

        Args:
            __context (Any): The context for model initialization.
        """
        self._base_url = f"http://{self.host}:{self.port}"
        logger.info(f"Initializing XdaqClient for {self._base_url}")
        self._check_host()
        self._check_gstreamer()

    def _check_host(self):
        """Check if the XDAQ server is reachable.

        Raises:
            ConnectionError: If the server is not reachable.
        """
        try:
            logger.debug("Checking connection to XDAQ server")
            requests.get(f"{self._base_url}/cameras", timeout=5).raise_for_status()
            logger.info("Successfully connected to XDAQ server")
        except requests.exceptions.RequestException as e:
            logger.error(f"XDAQ is not reachable at {self._base_url}: {e}")
            raise ConnectionError(f"XDAQ is not reachable. Please check the connection.") from e

    def _check_gstreamer(self):
        """Check if GStreamer is installed and available in the system's PATH.

        Raises:
            RuntimeError: If 'gst-launch-1.0' command is not found.
        """
        gst_launch_path = shutil.which("gst-launch-1.0")
        if not gst_launch_path:
            logger.error("GStreamer command 'gst-launch-1.0' not found")
            raise RuntimeError(
                "GStreamer command 'gst-launch-1.0' not found. "
                "Please ensure GStreamer is installed and in your system's PATH."
            )
        self._gst_launch_path = gst_launch_path
        logger.info(f"GStreamer is available at: {self._gst_launch_path}")

    def __del__(self):
        """Ensure all streams are cleaned up when the client is destroyed."""
        self.clean_streams()

    def list_cameras(self) -> List[Camera]:
        """Retrieve a list of available cameras from the XDAQ server.

        Returns:
            List[Camera]: A list of Camera objects.

        Raises:
            requests.exceptions.RequestException: If there is an issue
                communicating with the server.
        """
        response = requests.get(f"{self._base_url}/cameras", timeout=5)
        response.raise_for_status()
        cameras_data = response.json()
        return [Camera(**cam_data) for cam_data in cameras_data]

    def start_stream_with_recording(
        self,
        camera: Camera,
        capability: Capability,
        output_dir: str,
        split_max_files: Optional[int] = 0,
        split_max_time_sec: Optional[int] = 0,
        split_max_size_mb: Optional[int] = 0,
        gstreamer_debug: bool = False
    ) -> Stream:
        """Start a camera stream and record it to a file.

        This method requests the server to start streaming a camera's feed,
        then launches a local GStreamer process to receive and record the
        stream. The recording can be split into multiple files based on
        time, size, or number of files.

        Args:
            camera (Camera): The camera to start streaming.
            capability (Capability): The desired stream capability (resolution,
                format, etc.).
            output_dir (str): The directory to save the recording files.
            split_max_files (Optional[int]): The maximum number of files to
                create before overwriting. 0 for no limit. Defaults to 0.
            split_max_time_sec (Optional[int]): The maximum duration of each
                file in seconds. 0 for no limit. Defaults to 0.
            split_max_size_mb (Optional[int]): The maximum size of each file in
                megabytes. 0 for no limit. Defaults to 0.
            gstreamer_debug (bool): If True, enables GStreamer debug logging.
                Defaults to False.

        Returns:
            Stream: A Stream object representing the active stream.

        Raises:
            ValueError: If the selected capability is not a supported format.
            RuntimeError: If the stream fails to start on the server or if the
                local GStreamer process fails.
        """

        camera_id = camera.id
        capability_str = capability.to_gstreamer_capability()

        logger.info(
            f"Starting stream for camera {camera_id} ({camera.name}) "
            f"with capability: {capability_str}"
        )

        if capability.media_type != "image/jpeg":
            error_msg = (
                f"Capability {capability_str} is not in a supported format. "
                "Only image/jpeg capabilities are supported"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if camera_id in self.streams:
            existing_stream = self.streams[camera_id]
            logger.info(
                f"Camera {camera_id} is already streaming on port {existing_stream.port}. "
                "Returning existing stream."
            )
            return existing_stream

        port = self._get_available_port()
        logger.debug(f"Assigned port {port} for camera {camera_id}")

        payload = {"id": camera_id, "port": port, "capability": capability_str}

        try:
            response = requests.post(f"{self._base_url}/jpeg", json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Started JPEG stream for camera {camera_id} on port {port}")
        except requests.RequestException as e:
            logger.error(f"Failed to start stream on server: {e}")
            raise RuntimeError(f"Failed to start stream on server for camera {camera_id}") from e

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        refined_camera_name = ''.join(c if c.isalnum() else '_' for c in camera.name)
        file_basename = f"{camera_id}_{refined_camera_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        video_path = output_path / f"{file_basename}-%02d.mkv"
        gst_output_path = video_path.as_posix()

        gstreamer_log_file: Optional[io.TextIOBase] = None
        try:
            if gstreamer_debug:
                gstreamer_log_file_path = (output_path / f"{file_basename}.gstreamer.log")
                logger.info(f"GStreamer debug logs will be saved to: {gstreamer_log_file_path}")
                gstreamer_log_file = open(gstreamer_log_file_path, 'w', buffering=1)
                stdout_dest = stderr_dest = gstreamer_log_file
            else:
                gstreamer_log_file_path = None
                stdout_dest = stderr_dest = subprocess.DEVNULL

            pipeline_cmd = (
                f'"{self._gst_launch_path}" -e -v '
                f'srtclientsrc uri=srt://{self.host}:{port} latency=500 ! '
                'queue ! jpegparse ! tee name=t ! '
                f'queue ! splitmuxsink max-files={split_max_files} '
                f'max-size-time={split_max_time_sec * 1000000000} '
                f'max-size-bytes={split_max_size_mb * 1000000} '
                f'muxer-factory=matroskamux location="{gst_output_path}" '
                't. ! queue ! fpsdisplaysink fps-update-interval=30000 '
                'text-overlay=false video-sink=fakesink sync=false'
            )

            env = os.environ.copy()
            if gstreamer_debug:
                env['GST_DEBUG'] = '3'

            pipeline_args = shlex.split(pipeline_cmd)

            popen_kwargs = {
                "stdout": stdout_dest,
                "stderr": stderr_dest,
                "text": True,
                "bufsize": 1,
                "env": env
            }

            if os.name == 'nt':
                popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

            logger.debug(f"Starting GStreamer with FPS monitoring: {pipeline_cmd}")
            process = subprocess.Popen(pipeline_args, **popen_kwargs)

            time.sleep(1)

            if process.poll() is not None:
                logger.error("GStreamer process failed to start")
                if gstreamer_debug:
                    error_msg = (
                        "Failed to start GStreamer. Check debug log file at "
                        f"{gstreamer_log_file_path}."
                    )
                else:
                    error_msg = (
                        "Failed to start GStreamer. Enable gstreamer_debug=True for details."
                    )
                raise RuntimeError(error_msg)

            logger.info(f"Started recording for camera {camera_id} to {video_path}")

            new_stream = Stream(
                camera=camera,
                capability=capability,
                port=port,
                video_path=video_path,
                gstreamer_pipeline=pipeline_cmd,
                process=process,
                gstreamer_log_file=gstreamer_log_file,
                gstreamer_log_file_path=gstreamer_log_file_path,
            )
            self.streams[camera_id] = new_stream

            return new_stream

        except Exception as e:
            logger.error(f"Failed to start GStreamer process: {e}")

            if 'process' in locals() and process.poll() is None:
                logger.warning(f"Cleaning up orphaned GStreamer process for camera {camera_id}")
                if os.name == 'nt':
                    process.send_signal(signal.CTRL_C_EVENT)
                else:
                    process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)

            if gstreamer_log_file:
                gstreamer_log_file.close()

            try:
                requests.post(f"{self._base_url}/stop", json={"id": camera_id}, timeout=5)
            except requests.RequestException:
                pass
            raise RuntimeError(f"Failed to start GStreamer for camera {camera_id}") from e

    def stop_stream(self, camera_id: int) -> None:
        """Stop the stream for a specific camera.

        This terminates the local GStreamer process by sending an interrupt
        signal, allowing it to finalize recordings. It then sends a request to
        the server to stop sending the stream.

        Args:
            camera_id (int): The ID of the camera to stop.

        Raises:
            ValueError: If no active stream is found for the given camera ID.
        """
        logger.info(f"Stopping stream for camera {camera_id}")
        stream = self.streams.pop(camera_id, None)

        if not stream:
            raise ValueError(f"No active stream found for camera {camera_id}")

        try:
            if stream.process and stream.process.poll() is None:
                logger.debug(f"Terminating GStreamer process for camera {camera_id}")

                if os.name == 'nt':
                    stream.process.send_signal(signal.CTRL_C_EVENT)
                else:
                    stream.process.send_signal(signal.SIGINT)

                try:
                    stream.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Process didn't terminate gracefully, forcing kill")
                    stream.process.kill()
                    stream.process.wait(timeout=2)

            logger.info(f"Successfully stopped local recording process for camera {camera_id}")
        except Exception as e:
            logger.error(f"Error stopping GStreamer process: {e}")
        finally:
            if stream.gstreamer_log_file:
                stream.gstreamer_log_file.close()

        payload = {"id": camera_id}

        try:
            response = requests.post(f"{self._base_url}/stop", json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Successfully stopped stream on server for camera {camera_id}")
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Server error stopping stream: {e.response.status_code} - {e.response.text}"
            )
            logger.warning(
                "Failed to stop stream on server, but local resources have been cleaned up."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to communicate with server to stop stream: {e}")
            logger.warning(
                "Failed to stop stream on server, but local resources have been cleaned up."
            )

    def _get_available_port(self, start: int = 9001, end: int = 9099) -> int:
        """Find an available network port in a given range for the SRT stream.

        Args:
            start (int): The starting port number. Defaults to 9001.
            end (int): The ending port number. Defaults to 9099.

        Returns:
            int: An available port number.

        Raises:
            RuntimeError: If no available ports are found in the specified range.
        """
        active_ports = [stream.port for stream in self.streams.values()]
        for port in range(start, end + 1):
            if port not in active_ports:
                return port

        logger.error(f"No available ports in range {start}-{end}")
        raise RuntimeError(f"No available ports in range {start}-{end}")

    def clean_streams(self):
        """Stop all active streams and clean up all resources.

        This is useful for gracefully shutting down the client.
        """
        logger.info("Starting cleanup of all streams")
        camera_ids = list(self.streams.keys())

        for camera_id in camera_ids:
            try:
                self.stop_stream(camera_id)
            except Exception as e:
                logger.error(f"Error stopping stream for camera {camera_id}: {e}")

        logger.info("All resources cleaned up")
