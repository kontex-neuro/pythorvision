import time
import requests
from pythorvision import XdaqClient, enable_logging

enable_logging(level="INFO")

client = None
try:
    client = XdaqClient()

    recordings_dir = "recordings"

    all_cameras = client.list_cameras()
    if not all_cameras:
        print("No cameras found.")
        exit()

    print(f"Found {len(all_cameras)} cameras:")
    for camera in all_cameras:
        print("-" * 20)
        print(f"Camera ID: {camera.id}")
        print(f"Name: {camera.name}")
        print("Capabilities:")
        for i, cap in enumerate(camera.capabilities):
            if cap.media_type != 'image/jpeg':
                continue
            print(f"  - {i}: {cap.media_type} @ {cap.width}x{cap.height} {cap.framerate} fps")
        print("-" * 20)

    camera_0 = all_cameras[0]
    camera_1 = all_cameras[1]

    if camera_0:
        jpeg_cap_0 = camera_0.capabilities[0]
        if jpeg_cap_0:
            try:
                print(f"\nStarting stream for Camera {camera_0.id} ({camera_0.name})...")
                stream_0 = client.start_stream_with_recording(
                    camera=camera_0,
                    capability=jpeg_cap_0,
                    output_dir=recordings_dir,
                    gstreamer_debug=True
                )
                print(
                    f"✓ Stream started for camera {camera_0.id}. "
                    f"Recording to: {stream_0.video_path.parent}"
                )
            except (ValueError, RuntimeError) as e:
                print(f"✗ Failed to start stream for camera {camera_0.id}: {e}")
        else:
            print(f"No 'image/jpeg' capability found for Camera {camera_0.id}")
    else:
        print("Camera with ID 0 not found.")

    if camera_1:
        jpeg_cap_1 = camera_1.capabilities[0]
        if jpeg_cap_1:
            try:
                print(f"\nStarting stream for Camera {camera_1.id} ({camera_1.name})...")
                stream_1 = client.start_stream_with_recording(
                    camera=camera_1, capability=jpeg_cap_1, output_dir=recordings_dir
                )
                print(
                    f"✓ Stream started for camera {camera_1.id}. "
                    f"Recording to: {stream_1.video_path.parent}"
                )
            except (ValueError, RuntimeError) as e:
                print(f"✗ Failed to start stream for camera {camera_1.id}: {e}")
        else:
            print(f"No 'image/jpeg' capability found for Camera {camera_1.id}")
    else:
        print("Camera with ID 1 not found.")

    if len(client.streams) > 0:
        print("\nRecording for 10 seconds...")
        time.sleep(10)

        print("\nStopping streams...")
        if camera_0 and camera_0.id in client.streams:
            try:
                client.stop_stream(camera_0.id)
                print(f"✓ Stream stopped for camera {camera_0.id}.")
            except (ValueError, RuntimeError) as e:
                print(f"✗ Error stopping stream for camera {camera_0.id}: {e}")

        if camera_1 and camera_1.id in client.streams:
            try:
                client.stop_stream(camera_1.id)
                print(f"✓ Stream stopped for camera {camera_1.id}.")
            except (ValueError, RuntimeError) as e:
                print(f"✗ Error stopping stream for camera {camera_1.id}: {e}")
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
