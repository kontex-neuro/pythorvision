import requests
import subprocess
import os
import signal
import time
import sys
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .camera import Camera, Capability
import threading
import re

logger = logging.getLogger(__name__)


class Stream:

    def __init__(
        self, camera: Camera, capability: Capability, log_file: Any, port: int, video_path: str,
        log_file_path: str, gstreamer_pipeline: str, process: subprocess.Popen
    ):
        self.camera = camera
        self.capability = capability
        self.log_file = log_file
        self.port = port
        self.video_path = video_path
        self.log_file_path = log_file_path
        self.gstreamer_pipeline = gstreamer_pipeline
        self.process = process
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Stream(camera_id={self.camera.id}, camera_name='{self.camera.name}', \
            port={self.port}, capability='{self.capability.to_string()}', \
            video_path='{self.video_path}', log_file_path='{self.log_file_path}', \
            gstreamer_pipeline='{self.gstreamer_pipeline}', created_at={self.created_at})"


class XdaqClient:

    def __init__(self, host: str = "192.168.177.100", port: int = 8000):
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        logger.info(f"Initializing XdaqClient for {self._base_url}")
        self._check_host()
        self._check_gstreamer()
        self.streams: Dict[int, Stream] = {}

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
                "GStreamer command 'gst-launch-1.0' not found. Please ensure GStreamer is installed and in your system's PATH."
            )
        logger.info("GStreamer is available")

    def __del__(self):
        self.cleanup()

    def list_cameras(self) -> List[Camera]:
        response = requests.get(f"{self._base_url}/cameras")
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
    ) -> Dict[str, Any]:

        camera_id = camera.id
        capability_str = capability.to_string()

        logger.info(
            f"Starting stream for camera {camera_id} ({camera.name}) with capability: {capability_str}"
        )

        if capability.media_type != "image/jpeg":
            logger.error(f"Unsupported capability format: {capability_str}")
            return {
                "success": False,
                "stream": None,
                "error": f"Capability {capability_str} is not in a supported format",
                "message": "Only image/jpeg capabilities are supported"
            }

        if camera_id in self.streams:
            existing_stream = self.streams[camera_id]
            logger.info(f"Camera {camera_id} is already streaming on port {existing_stream.port}")
            return {
                "success": True,
                "stream": existing_stream,
                "error": None,
                "message": f"Camera {camera_id} already streaming on port {existing_stream.port}"
            }

        port = self._get_available_port()
        logger.debug(f"Assigned port {port} for camera {camera_id}")

        payload = {"id": camera_id, "port": port, "capability": capability_str}

        try:
            response = requests.post(f"{self._base_url}/jpeg", json=payload)
            response.raise_for_status()
            logger.info(f"Started JPEG stream for camera {camera_id} on port {port}")
        except requests.RequestException as e:
            logger.error(f"Failed to start stream on server: {e}")
            raise

        os.makedirs(output_dir, exist_ok=True)
        refined_camera_name = ''.join(c if c.isalnum() else '_' for c in camera.name)
        video_path = os.path.join(
            output_dir,
            f"{camera_id}_{refined_camera_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}-%02d.mkv"
        )

        if os.name == 'nt':
            gst_output_path = video_path.replace('\\', '/')
        else:
            gst_output_path = video_path

        pipeline_cmd = (
            f'gst-launch-1.0 -e -v '
            f'srtclientsrc uri=srt://{self._host}:{port} latency=500 ! '
            f'queue ! jpegparse ! tee name=t ! '
            f'queue ! splitmuxsink max-files={split_max_files} '
            f'max-size-time={split_max_time_sec * 1000000000} '
            f'max-size-bytes={split_max_size_mb * 1000000} '
            f'muxer-factory=matroskamux location={gst_output_path} '
            f't. ! queue ! fpsdisplaysink fps-update-interval={30000} '
            f'text-overlay=false video-sink=fakesink sync=false'
        )

        log_file = None
        log_file_path = None

        if gstreamer_debug:
            log_filename = f"{video_path.split('/')[-1]}.gstreamer.log"
            log_file_path = os.path.join(output_dir, log_filenae)
            logger.info(f"GStreamer debug logs will be saved to: {log_file_path}")
            log_file = open(log_file_path, 'w', buffering=1)
            stdout_dest = stderr_dest = log_file
        else:
            stdout_dest = stderr_dest = subprocess.DEVNULL

        try:
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

            log_threads = []

            time.sleep(1)

            if process.poll() is not None:
                logger.error("GStreamer process failed to start")
                if gstreamer_debug:
                    error_msg = f"Failed to start GStreamer. Check debug log file at {log_file_path}."
                else:
                    error_msg = "Failed to start GStreamer. Enable gstreamer_debug=True for details."

                self.stop_stream(camera_id)
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "Failed to start GStreamer"
                }

            if gstreamer_debug:
                logger.info(
                    f"Started recording for camera {camera_id} to {video_path} (debug logging enabled)"
                )
            else:
                logger.info(f"Started recording for camera {camera_id} to {video_path}")

            new_stream = Stream(
                camera, capability, log_file, port, video_path, log_file_path, pipeline_cmd, process
            )
            self.streams[camera_id] = new_stream

            return {
                "success": True,
                "stream": new_stream,
                "error": None,
                "message": f"Stream started successfully for camera {camera_id}"
            }

        except Exception as e:
            logger.error(f"Failed to start GStreamer: {e}")
            self.stop_stream(camera_id)
            return {
                "success": False,
                "stream": None,
                "error": str(e),
                "message": "Failed to start GStreamer"
            }

    def stop_stream(self, camera_id: int) -> Dict[str, Any]:
        logger.info(f"Stopping stream for camera {camera_id}")
        stream = self.streams.pop(camera_id, None)

        if stream:
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
                        logger.warning(f"Process didn't terminate gracefully, forcing kill")
                        stream.process.kill()
                        stream.process.wait(timeout=2)

                logger.info(f"Successfully stopped local recording process for camera {camera_id}")
            except Exception as e:
                logger.error(f"Error stopping GStreamer process: {e}")
            finally:
                if stream.log_file:
                    stream.log_file.close()

        else:
            logger.warning(f"No active stream found for camera {camera_id}")
            return {
                "message": "No active stream found",
                "camera_id": camera_id,
            }

        payload = {"id": camera_id}

        try:
            response = requests.post(f"{self._base_url}/stop", json=payload)
            response.raise_for_status()
            logger.info(f"Successfully stopped stream for camera {camera_id}")
            return {
                "message": "Stream and recording stopped",
                "camera_id": camera_id,
                "output_path": stream.video_path
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"Server error details: {response.text}")
            logger.warning(
                f"Failed to stop stream on server, but local resources have been cleaned up"
            )
            return {
                "message": "Stream recording stopped, but server reported an error",
                "camera_id": camera_id,
                "output_path": stream.video_path,
                "error": str(e)
            }

    def _get_available_port(self, start: int = 9001, end: int = 9099) -> int:
        active_ports = [stream.port for stream in self.streams.values()]
        for port in range(start, end + 1):
            if port not in active_ports:
                return port

        logger.error(f"No available ports in range {start}-{end}")
        raise RuntimeError(f"No available ports in range {start}-{end}")

    def cleanup(self):
        logger.info("Starting cleanup of all streams")
        camera_ids = list(self.streams.keys())

        for camera_id in camera_ids:
            try:
                self.stop_stream(camera_id)
            except Exception as e:
                logger.error(f"Error stopping stream for camera {camera_id}: {e}")

        logger.info("All resources cleaned up")
