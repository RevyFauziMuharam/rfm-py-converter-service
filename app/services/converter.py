import os
from moviepy.editor import VideoFileClip
from app.utils.logger import get_logger

class MP4ToMP3Converter:
    """Service for converting MP4 videos to MP3 audio files"""
    
    def __init__(self, bitrate="192k", sample_rate=44100):
        """
        Initialize the converter with given settings
        
        Args:
            bitrate (str): Bitrate for the MP3 file (e.g. '192k')
            sample_rate (int): Sample rate in Hz
        """
        self.bitrate = bitrate
        self.sample_rate = sample_rate
        self.logger = get_logger(__name__)
    
    def convert(self, mp4_path, output_folder, output_filename=None):
        """
        Convert an MP4 file to MP3
        
        Args:
            mp4_path (str): Path to the MP4 file
            output_folder (str): Directory to save the MP3 file
            output_filename (str, optional): Custom name for the output file.
                If None, will use the input filename with _temp suffix.
        
        Returns:
            str: Path to the converted MP3 file
        
        Raises:
            IOError: If the input file doesn't exist
            Exception: For any conversion errors
        """
        if not os.path.exists(mp4_path):
            self.logger.error(f"Input file not found: {mp4_path}")
            raise IOError(f"Input file not found: {mp4_path}")
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Determine output filename
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(mp4_path))[0]
            output_filename = f"{base_name}_temp.mp3"
        
        output_path = os.path.join(output_folder, output_filename)
        
        self.logger.info(f"Starting conversion of {mp4_path} to {output_path}")
        
        try:
            # Extract audio from video
            video = VideoFileClip(mp4_path)
            
            # Check if video has audio
            if not video.audio:
                self.logger.error(f"Video has no audio track: {mp4_path}")
                raise ValueError(f"Video has no audio track: {mp4_path}")
            
            # Write audio to file
            video.audio.write_audiofile(
                output_path,
                bitrate=self.bitrate,
                fps=self.sample_rate,
                logger=None  # Disable moviepy's internal logger
            )
            
            # Close the video to release resources
            video.close()
            
            self.logger.info(f"Conversion completed: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error during conversion: {str(e)}")
            # Clean up partial output file if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
            raise Exception(f"Conversion failed: {str(e)}")
