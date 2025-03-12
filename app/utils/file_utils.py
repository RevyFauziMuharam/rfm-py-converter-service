import os
import magic
from flask import current_app
from datetime import datetime, timedelta

def allowed_file(filename):
    """
    Check if a file has an allowed extension
    
    Args:
        filename (str): The name of the file to check
    
    Returns:
        bool: True if file extension is allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_file_info(file_path):
    """
    Get information about a file
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        dict: Dictionary containing file information
    """
    if not os.path.exists(file_path):
        return None
    
    stat_info = os.stat(file_path)
    
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
    except:
        file_type = "unknown"
    
    return {
        'name': os.path.basename(file_path),
        'path': file_path,
        'size': stat_info.st_size,
        'created': datetime.fromtimestamp(stat_info.st_ctime),
        'modified': datetime.fromtimestamp(stat_info.st_mtime),
        'type': file_type
    }

def clean_expired_files(directory, expiry_hours=24):
    """
    Clean up files older than the specified expiry time
    
    Args:
        directory (str): Directory to clean
        expiry_hours (int): Number of hours after which files are considered expired
    """
    now = datetime.now()
    expiry_time = now - timedelta(hours=expiry_hours)
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        # Check file age
        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_modified < expiry_time:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")
