import argparse
import pythorvision as ptv
import sys


def main():
    """
    Example script to extract and display metadata from a video file.
    """
    parser = argparse.ArgumentParser(
        description="Extract metadata from a ThorVision video file and print the first 10 records."
    )
    parser.add_argument(
        "video_path",
        type=str,
        help="Path to the video file (e.g., recordings/0_DF100_20250819_144301-00.mkv)."
    )
    args = parser.parse_args()

    # It's good practice to enable logging to see any potential errors from the library
    ptv.enable_logging("INFO")

    print(f"Attempting to extract metadata from '{args.video_path}'...")

    try:
        metadata = ptv.extract_metadata(args.video_path)
    except FileNotFoundError:
        print(f"Error: The file was not found at '{args.video_path}'", file=sys.stderr)
        sys.exit(1)

    if metadata.size == 0:
        print(
            "No metadata could be extracted. The file might be corrupted, have a different format, or contain no video stream."
        )
        return

    print(f"\nSuccessfully extracted {metadata.size} metadata records.")
    print("Showing the first 10 records:")
    print("=" * 30)

    # Iterate through the first 10 records and print fields directly from the NumPy array.
    # Accessing fields by name (e.g., record_np['frame_pts']) is highly efficient.
    for i, record_np in enumerate(metadata[:10]):
        print(f"\n--- Record {i+1} ---")
        print(f"  Frame PTS         : {record_np['frame_pts']}")
        print(f"  GStreamer PTS     : {record_np['gstreamer_pts']}")
        print(f"  XDAQ Timestamp    : {record_np['xdaq_timestamp']}")
        print(f"  Sample Index      : {record_np['sample_index']}")
        print(f"  TTL In            : {record_np['ttl_in']}")
        print(f"  TTL Out           : {record_np['ttl_out']}")


if __name__ == "__main__":
    main()
