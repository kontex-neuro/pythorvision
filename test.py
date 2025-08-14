from pythorvision import XdaqClient, enable_logging
import time
import os

enable_logging(level="INFO")

client = XdaqClient()

try:
    all_cameras = client.list_cameras()
    if not all_cameras:
        print("No cameras found.")
        exit()

    print(f"Found {len(all_cameras)} cameras:")
    for camera in all_cameras:
        print("-" * 20)
        print(f"Camera ID: {camera.id}")
        print(f"Name: {camera.name}")

        grouped_caps = {}
        print(f"Caps:")
        for cap in camera.caps:
            print('    - ' + cap.to_string())

        print("-" * 20)

    camera_0 = next((cam for cam in all_cameras if cam.id == 0), None)
    camera_2 = next((cam for cam in all_cameras if cam.id == 2), None)

    recordings_dir = os.path.join(os.getcwd(), "recordings")

    if camera_0:
        jpeg_cap_0 = next((cap for cap in camera_0.caps if cap.media_type == 'image/jpeg'), None)

        if jpeg_cap_0:
            print(f"\nStarting stream for Camera {camera_0.id} ({camera_0.name})...")
            result_0 = client.start_stream_with_recording(
                camera=camera_0, capability=jpeg_cap_0, output_dir=recordings_dir
            )
            if result_0["success"]:
                print(f"✓ Stream started: {result_0['message']}")

        else:
            print(f"No 'image/jpeg' capability found for Camera {camera_0.id}")
    else:
        print("Camera with ID 0 not found.")

    if camera_2:
        jpeg_cap_2 = next((cap for cap in camera_2.caps if cap.media_type == 'image/jpeg'), None)

        if jpeg_cap_2:
            print(f"\nStarting stream for Camera {camera_2.id} ({camera_2.name})...")
            result_2 = client.start_stream_with_recording(
                camera=camera_2, capability=jpeg_cap_2, output_dir=recordings_dir
            )
            if result_2["success"]:
                print(f"✓ Stream started: {result_2['message']}")

        else:
            print(f"No 'image/jpeg' capability found for Camera {camera_2.id}")
    else:
        print("Camera with ID 2 not found.")

    print("\nRecording for 10 seconds...")
    time.sleep(10)

    print("\nStopping streams...")
    client.stop_stream(camera_0.id)
    client.stop_stream(camera_2.id)

except Exception as e:
    print(f"\nAn error occurred: {e}")
finally:
    client.cleanup()
    print("Cleanup complete.")
