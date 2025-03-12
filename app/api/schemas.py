from marshmallow import Schema, fields, validate, EXCLUDE

class ConversionRequestSchema(Schema):
    """Schema for validating conversion request parameters"""
    
    chunk_size = fields.Integer(
        validate=validate.Range(min=1, max=500),
        required=False,
        metadata={"description": "Chunk size in MB (1-500)"}
    )
    
    bitrate = fields.String(
        validate=validate.OneOf(['64k', '128k', '192k', '256k', '320k']),
        required=False, 
        metadata={"description": "MP3 bitrate quality"}
    )
    
    class Meta:
        unknown = EXCLUDE  # Ignore unknown fields

class FileInfoSchema(Schema):
    """Schema for file information"""
    
    filename = fields.String(required=True)
    size = fields.Integer(required=True)
    download_url = fields.Url(required=True)

class ConversionResponseSchema(Schema):
    """Schema for conversion job response"""
    
    job_id = fields.String(required=True)
    filename = fields.String(required=True)
    file_size = fields.Integer(required=True)
    status = fields.String(required=True, validate=validate.OneOf(['processing', 'completed', 'failed']))

class ConversionStatusResponseSchema(Schema):
    """Schema for conversion status response"""
    
    job_id = fields.String(required=True)
    status = fields.String(required=True, validate=validate.OneOf(['processing', 'completed', 'failed']))
    files = fields.List(fields.Nested(FileInfoSchema), required=True)
