import av
import numpy as np
import logging
from dataclasses import dataclass, fields

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameMetadata:
    """Schema for per-frame metadata in a ThorVision video.

    This dataclass defines the field names and types for frame metadata.
    It is used to generate a matching NumPy dtype, enabling efficient
    storage and vectorized operations when handling large numbers of frames.

    Attributes:
        frame_pts (np.int64): The presentation timestamp (PTS) of the frame from the video container.
        gstreamer_pts (np.uint64): The GStreamer timestamp when the frame was produced on the server.
        xdaq_timestamp (np.uint64): The timestamp from the XDAQ system.
        sample_index (np.uint32): The sample index from the rhythm system.
        ttl_in (np.uint32): The state of the TTL input lines.
        ttl_out (np.uint32): The state of the TTL output lines.
    """
    frame_pts: np.int64
    gstreamer_pts: np.uint64
    xdaq_timestamp: np.uint64
    sample_index: np.uint32
    ttl_in: np.uint32
    ttl_out: np.uint32

    @classmethod
    def to_numpy_dtype(cls) -> np.dtype:
        """Generates a NumPy dtype from the dataclass fields."""
        numpy_fields = []
        for field in fields(cls):
            numpy_fields.append((field.name, field.type))
        return np.dtype(numpy_fields)


frame_metadata_dtype = FrameMetadata.to_numpy_dtype()


def extract_metadata(video_path: str) -> np.ndarray:
    """Extracts per-frame metadata from a ThorVision video.

    Opens the video, parses embedded metadata, and returns it as a
    structured NumPy array using the dtype generated from FrameMetadata.

    Args:
        video_path: Path to the video file (e.g., .mkv).

    Returns:
        np.ndarray: Structured array of frame metadata. Empty array if no metadata is found.

    Raises:
        av.error.AVError: If there is an error opening or processing the video file.
    """

    RAW_RECORD_DTYPE = np.dtype(
        [
            ('video_timestamp', '<u8'),
            (
                'metadata',
                np.dtype(
                    [
                        ('fpga_timestamp', '<u8'), ('rhythm_timestamp', '<u4'), ('ttl_in', '<u4'),
                        ('ttl_out', '<u4'), ('spi_perf_counter', '<u4'), ('reserved', '<u8')
                    ]
                )
            )
        ]
    )

    def _parse_packet_metadata(raw_packet_data):
        """Extracts and parses metadata from a raw packet's bytes."""
        if len(raw_packet_data) < 46:
            return None
        metadata_slice = raw_packet_data[6:46]
        return np.frombuffer(metadata_slice, dtype=RAW_RECORD_DTYPE)[0]

    records = []
    try:
        with av.open(video_path) as container:
            if not container.streams.video:
                logger.warning(f"No video stream found in file: {video_path}")
                return np.array([], dtype=frame_metadata_dtype)

            video_stream = container.streams.video[0]

            for packet in container.demux(video_stream):
                if packet.pts is None:
                    logger.warning(f"Packet has no PTS: {packet}")
                    continue

                raw_record = _parse_packet_metadata(bytes(packet))

                if raw_record:
                    # IMPORTANT: The order of elements MUST match the field order
                    # in the FrameMetadata dataclass.
                    record = (
                        packet.pts,
                        raw_record['video_timestamp'],
                        raw_record['metadata']['fpga_timestamp'],
                        raw_record['metadata']['rhythm_timestamp'],
                        raw_record['metadata']['ttl_in'],
                        raw_record['metadata']['ttl_out'],
                    )
                    records.append(record)
    except av.error.AVError as e:
        logger.error(f"Error processing video file {video_path}: {e}")

    return np.array(records, dtype=frame_metadata_dtype)
