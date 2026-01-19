"""
Marshmallow schema for Version resource POST requests.
Replaces deprecated flask-restful reqparse.
"""

from marshmallow import Schema, fields, validate


class VersionUpdateSchema(Schema):
    """Schema for validating version update requests."""
    current_version_stable = fields.String(
        data_key='current-version-stable',
        required=False,
        validate=validate.Length(max=64)
    )
    current_version_prerelease = fields.String(
        data_key='current-version-prerelease',
        required=False,
        validate=validate.Length(max=64)
    )
    jwt_secret = fields.String(
        data_key='jwt-secret',
        required=True,
        validate=validate.Length(min=1, max=256),
        error_messages={'required': 'jwt-secret is required'}
    )
