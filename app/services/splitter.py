import os
import math
from pydub import AudioSegment
from app.utils.logger import get_logger

class MP3Splitter:
    """Service for splitting MP3 files into smaller chunks"""
    
    def __init__(self, max_size_mb=25):
        """
        Initialize the splitter
        
        Args:
            max_size_mb (int): Maximum size in MB for each chunk
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = get_logger(__name__)
    
    def split(self, mp3_path, output_folder, base_filename=None, delete_source=True):
        """
        Split an MP3 file into chunks of specified maximum size
        
        Args:
            mp3_path (str): Path to the MP3 file
            output_folder (str): Directory to save the split files
            base_filename (str, optional): Base name for output files.
                If None, uses the input filename without _temp suffix.
            delete_source (bool): Whether to delete the source file after splitting
        
        Returns:
            list: List of paths to the split MP3 files
        
        Raises:
            IOError: If the input file doesn't exist
            Exception: For any splitting errors
        """
        if not os.path.exists(mp3_path):
            self.logger.error(f"Input file not found: {mp3_path}")
            raise IOError(f"Input file not found: {mp3_path}")
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Determine base filename for output
        if base_filename is None:
            base_filename = os.path.splitext(os.path.basename(mp3_path))[0]
            base_filename = base_filename.replace("_temp", "")  # Remove temp suffix
        
        self.logger.info(f"Loading MP3 for splitting: {mp3_path}")
        
        try:
            # Load the MP3 file
            audio = AudioSegment.from_mp3(mp3_path)
            
            # Calculate duration and bytes per millisecond
            duration_ms = len(audio)
            file_size = os.path.getsize(mp3_path)
            bytes_per_ms = file_size / duration_ms
            
            # Calculate segment duration
            segment_duration_ms = int(self.max_size_bytes / bytes_per_ms)
            
            # Calculate number of segments
            total_segments = math.ceil(duration_ms / segment_duration_ms)
            
            self.logger.info(f"Splitting file into {total_segments} parts of ~{self.max_size_bytes/1024/1024:.1f}MB each")
            
            output_files = []
            
            # Create segments
            for i in range(total_segments):
                start_ms = i * segment_duration_ms
                end_ms = min((i + 1) * segment_duration_ms, duration_ms)
                
                segment = audio[start_ms:end_ms]
                
                # Generate output filename
                output_file = os.path.join(output_folder, f"{base_filename}_part{i+1}.mp3")
                
                self.logger.info(f"Exporting part {i+1}/{total_segments} to {output_file}")
                
                # Export segment
                segment.export(output_file, format="mp3")
                
                # Verify size
                actual_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                self.logger.info(f"Part {i+1} size: {actual_size_mb:.2f} MB")
                
                output_files.append(output_file)
            
            # Delete source file if requested
            if delete_source:
                self.logger.info(f"Deleting source file: {mp3_path}")
                os.remove(mp3_path)
            
            return output_files
            
        except Exception as e:
            self.logger.error(f"Error during splitting: {str(e)}")
            raise Exception(f"Splitting failed: {str(e)}")
