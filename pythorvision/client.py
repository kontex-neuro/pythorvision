import subprocess
import os
import signal
import time
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, PrivateAttr
from typing_extensions import Annotated
import requests

from .camera import Camera, Capability

logger = logging.getLogger(__name__)


class Stream(BaseModel):
    camera: Camera
    capability: Capability
    port: int
    video_path: Path
    gstreamer_pipeline: str
    process: Any
    gstreamer_log_file: Optional[Any] = None
    gstreamer_log_file_path: Optional[Path] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class XdaqClient(BaseModel):
    host: str = "192.168.177.100"
    port: int = 8000
    _base_url: str = PrivateAttr("")
    streams: Annotated[Dict[int, Stream], Field(default_factory=dict, repr=False)]

    def model_post_init(self, __context: Any) -> None:
        self._base_url = f"http://{self.host}:{self.port}"
        logger.info(f"Initializing XdaqClient for {self._base_url}")
        self._check_host()
        self._check_gstreamer()

    def _check_host(self):
        try:
            logger.debug("Checking connection to XDAQ server")
            requests.get(f"{self._base_url}/cameras", timeout=5).raise_for_status()
            logger.info("Successfully connected to XDAQ server")
        except requests.exceptions.RequestException as e:
            logger.error(f"XDAQ is not reachable at {self._base_url}: {e}")
            raise ConnectionError(f"XDAQ is not reachable. Please check the connection.") from e

    def _check_gstreamer(self):
        if not shutil.which("gst-launch-1.0"):
            logger.error("GStreamer command 'gst-launch-1.0' not found")
            raise RuntimeError(
                "GStreamer command 'gst-launch-1.0' not found. "
                "Please ensure GStreamer is installed and in your system's PATH."
            )
        logger.info("GStreamer is available")

    def __del__(self):
        self.clean_streams()

    def list_cameras(self) -> List[Camera]:
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

        gstreamer_log_file: Optional[Any] = None
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
                'gst-launch-1.0 -e -v '
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

            logger.debug(f"Starting GStreamer with FPS monitoring: {pipeline_cmd}")
            process = subprocess.Popen(
                pipeline_cmd,
                stdout=stdout_dest,
                stderr=stderr_dest,
                text=True,
                bufsize=1,
                shell=True,
                env=env,
                universal_newlines=True
            )

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
            if gstreamer_log_file:
                gstreamer_log_file.close()

            try:
                requests.post(f"{self._base_url}/stop", json={"id": camera_id}, timeout=5)
            except requests.RequestException:
                pass
            raise RuntimeError(f"Failed to start GStreamer for camera {camera_id}") from e

    def stop_stream(self, camera_id: int) -> None:
        logger.info(f"Stopping stream for camera {camera_id}")
        stream = self.streams.pop(camera_id, None)

        if not stream:
            raise ValueError(f"No active stream found for camera {camera_id}")

        try:
            if stream.process and stream.process.poll() is None:
                logger.debug(f"Terminating GStreamer process for camera {camera_id}")

                if os.name == 'nt':
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/T', '/PID',
                             str(stream.process.pid)],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                    except (FileNotFoundError, subprocess.CalledProcessError) as e:
                        logger.warning(f"taskkill failed: {e}. Falling back to process.kill()")
                        if stream.process.poll() is None:
                            stream.process.kill()
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
        active_ports = [stream.port for stream in self.streams.values()]
        for port in range(start, end + 1):
            if port not in active_ports:
                return port

        logger.error(f"No available ports in range {start}-{end}")
        raise RuntimeError(f"No available ports in range {start}-{end}")

    def clean_streams(self):
        logger.info("Starting cleanup of all streams")
        camera_ids = list(self.streams.keys())

        for camera_id in camera_ids:
            try:
                self.stop_stream(camera_id)
            except Exception as e:
                logger.error(f"Error stopping stream for camera {camera_id}: {e}")

        logger.info("All resources cleaned up")
