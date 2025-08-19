import time
from typing import Optional
import requests
from pythorvision import ThorVisionClient, enable_logging, Camera, Capability

enable_logging(level="INFO")


def start_camera_stream(
    client: ThorVisionClient,
    camera: Camera,
    jpeg_cap: Capability,
    recordings_dir: str,
    gstreamer_debug: bool = False
):
    try:
        print(f"\nStarting stream for Camera {camera.id} ({camera.name})...")
        stream = client.start_stream_with_recording(
            camera=camera,
            capability=jpeg_cap,
            output_dir=recordings_dir,
            gstreamer_debug=gstreamer_debug
        )
        print(f"✓ Stream started for camera {camera.id}. Recording to: {stream.video_path.parent}")
    except (ValueError, RuntimeError) as e:
        print(f"✗ Failed to start stream for camera {camera.id}: {e}")


def stop_camera_stream(client: ThorVisionClient, camera: Optional[Camera]):
    if camera and camera.id in client.streams:
        try:
            client.stop_stream(camera.id)
            print(f"✓ Stream stopped for camera {camera.id}.")
        except (ValueError, RuntimeError) as e:
            print(f"✗ Error stopping stream for camera {camera.id}: {e}")


def main():
    client = None
    try:
        client = ThorVisionClient()

        recordings_dir = "recordings"

        all_cameras = client.list_cameras()
        if not all_cameras:
            print("No cameras found.")
            return

        print(f"Found {len(all_cameras)} cameras:")
        for camera in all_cameras:
            print("-" * 20)
            print(f"Camera ID: {camera.id}")
            print(f"Name: {camera.name}")
            print("Capabilities:")
            for i, cap in enumerate(camera.capabilities):
                if cap.media_type == 'image/jpeg':
                    print(
                        f"  - {i}: {cap.media_type} @ {cap.width}x{cap.height} {cap.framerate} fps"
                    )
            print("-" * 20)

        cameras_to_stream = all_cameras[:2]
        if not cameras_to_stream:
            print("Not enough cameras available to start streaming.")
            return

        for i, camera in enumerate(cameras_to_stream):
            jpeg_cap = None
            for cap in camera.capabilities:
                if cap.media_type == 'image/jpeg':
                    jpeg_cap = cap
                    break
            if jpeg_cap:
                start_camera_stream(client, camera, jpeg_cap, recordings_dir)
            else:
                print(f"No 'image/jpeg' capability found for Camera {camera.id}")

        if client.streams:
            print("\nRecording for 10 seconds...")
            time.sleep(10)

            print("\nStopping streams...")
            for camera in cameras_to_stream:
                stop_camera_stream(client, camera)
        else:
            print("\nNo streams were started.")

    except (ConnectionError, requests.exceptions.RequestException) as e:
        print(f"\n✗ An error occurred communicating with the server: {e}")
    except Exception as e:
        print(f"\n✗ An unexpected error occurred: {e}")
    finally:
        if client and client.streams:
            print("\nRunning final cleanup...")
            client.clean_streams()
            print("Cleanup complete.")
        else:
            print("\nNo active streams to clean up.")


if __name__ == "__main__":
    main()
