from pythorvision import ThorVisionClient
import time
import os

# Use the context manager for automatic cleanup
with ThorVisionClient() as client:
    # List cameras and get formatted capabilities
    capabilities = client.format_camera_capabilities()
    
    # Get a camera ID and capability
    camera_id = 0  # First camera
    camera_caps = capabilities[camera_id]
    jpeg_caps = [cap for cap in camera_caps if "image/jpeg" in cap]
    
    # Start a stream with recording using the first JPEG capability
    if jpeg_caps:
        # Create recordings directory in current working directory
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        
        # Start stream with recording
        stream_info = client.start_stream_with_recording(
            camera_id=camera_id,
            capability=jpeg_caps[0],
            output_dir=recordings_dir,
            max_size_time=60,  # 1 minute segments
            max_size_bytes=500000000,  # 500MB segments
            gstreamer_log='console'
        )
        
        print(f"Stream info: {stream_info}")
        
        # Show active streams
        print("Active streams:")
        print(client.list_active_streams())
        
        # Record for 10 seconds
        print("Recording for 120 seconds...")
        time.sleep(120)
        
        # Stop the stream and recording
        result = client.stop_stream(camera_id)
        print(f"Stop result: {result}")