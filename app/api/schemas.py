from marshmallow import Schema, fields, validate, EXCLUDE


class ConversionRequestSchema(Schema):
    """Schema untuk validasi parameter request konversi"""

    chunk_size = fields.Integer(
        validate=validate.Range(min=1, max=500),
        required=False,
        metadata={"description": "Ukuran potongan dalam MB (1-500)"}
    )

    bitrate = fields.String(
        validate=validate.OneOf(['64k', '128k', '192k', '256k', '320k']),
        required=False,
        metadata={"description": "Kualitas bitrate MP3"}
    )

    class Meta:
        unknown = EXCLUDE  # Abaikan field yang tidak dikenal


class URLConversionRequestSchema(ConversionRequestSchema):
    """Schema untuk validasi request konversi dari URL"""

    url = fields.Url(
        required=True,
        metadata={"description": "URL file MP4 yang akan dikonversi"}
    )

    filename = fields.String(
        required=False,
        metadata={"description": "Nama file untuk output (opsional)"}
    )


class FileInfoSchema(Schema):
    """Schema untuk informasi file"""

    filename = fields.String(required=True)
    size = fields.Integer(required=True)
    download_url = fields.String(required=True)


class ConversionResponseSchema(Schema):
    """Schema untuk response job konversi"""

    job_id = fields.String(required=True)
    filename = fields.String(required=False)
    url = fields.String(required=False)
    file_size = fields.Integer(required=False)
    status = fields.String(required=True, validate=validate.OneOf(['processing', 'queued', 'completed', 'failed']))
    is_queued = fields.Boolean(required=False)
    queue_position = fields.Integer(required=False)
    queue_length = fields.Integer(required=False)


class ConversionStatusResponseSchema(Schema):
    """Schema untuk response status konversi"""

    job_id = fields.String(required=True)
    status = fields.String(required=True, validate=validate.OneOf(['processing', 'queued', 'completed', 'failed']))
    queue_position = fields.Integer(required=False)
    queue_length = fields.Integer(required=False)
    error = fields.String(required=False)
    files = fields.List(fields.Nested(FileInfoSchema), required=True)