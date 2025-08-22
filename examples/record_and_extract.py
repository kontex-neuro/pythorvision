import time
import pythorvision as ptv
import requests
import sys


def main():
    """
    Example script that records a short video from the first available camera,
    then extracts and displays its metadata.
    """
    # It's good practice to enable logging to see any potential errors from the library
    ptv.enable_logging("INFO")

    client = None
    video_path = None

    try:
        client = ptv.ThorVisionClient()

        # --- 1. Find and select a camera ---
        print("Looking for cameras...")
        all_cameras = client.list_cameras()
        if not all_cameras:
            print("No cameras found.")
            return

        camera_to_use = all_cameras[0]
        print(
            f"Found {len(all_cameras)} cameras. Using camera ID: {camera_to_use.id} ({camera_to_use.name})"
        )

        # --- 2. Select a capability ---
        jpeg_cap = next(
            (cap for cap in camera_to_use.capabilities if cap.media_type == 'image/jpeg'),
            None,
        )
        if not jpeg_cap:
            print(f"No 'image/jpeg' capability found for Camera {camera_to_use.id}")
            return

        print(
            f"Selected capability: {jpeg_cap.media_type} @ {jpeg_cap.width}x{jpeg_cap.height} {jpeg_cap.framerate} fps"
        )

        # --- 3. Record a short video ---
        recordings_dir = "recordings"
        print(f"\nStarting stream for Camera {camera_to_use.id}...")
        stream = client.start_stream_with_recording(
            camera=camera_to_use,
            capability=jpeg_cap,
            output_dir=recordings_dir,
        )
        video_path = stream.video_path
        print(f"✓ Stream started. Recording to: {video_path}")

        print("\nRecording for 5 seconds...")
        time.sleep(5)

        print("\nStopping stream...")
        client.stop_stream(camera_to_use.id)
        print(f"✓ Stream stopped for camera {camera_to_use.id}.")

        # --- 4. Extract and display metadata ---
        if video_path:
            # The path from the client is a pattern for segmentation (e.g., ...-%02d.mkv).
            # We need to format it to point to the first segment of the video.
            first_segment_path = str(video_path) % 0
            print(f"\nAttempting to extract metadata from '{first_segment_path}'...")
            try:
                metadata = ptv.extract_metadata(first_segment_path)
            except FileNotFoundError:
                print(
                    f"Error: The file was not found at '{first_segment_path}'",
                    file=sys.stderr,
                )
                return

            if metadata.size == 0:
                print(
                    "No metadata could be extracted. The file might be corrupted or have no video stream."
                )
                return

            print(f"\nSuccessfully extracted {metadata.size} metadata records.")
            print("Showing the first 10 records:")
            print("=" * 30)

            for i, record_np in enumerate(metadata[:10]):
                print(f"\n--- Record {i+1} ---")
                print(f"  Frame PTS         : {record_np['frame_pts']}")
                print(f"  GStreamer PTS     : {record_np['gstreamer_pts']}")
                print(f"  XDAQ Timestamp    : {record_np['xdaq_timestamp']}")
                print(f"  Sample Index      : {record_np['sample_index']}")
                print(f"  TTL In            : {record_np['ttl_in']}")
                print(f"  TTL Out           : {record_np['ttl_out']}")

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
