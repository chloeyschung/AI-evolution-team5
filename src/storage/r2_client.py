"""Cloudflare R2 object storage client."""

from src.config import settings


class R2ConfigError(Exception):
    pass


class R2Client:
    """Thin wrapper around boto3 for Cloudflare R2 uploads and presigned URLs."""

    def __init__(self) -> None:
        missing = [
            var
            for var, val in [
                ("R2_ACCOUNT_ID", settings.R2_ACCOUNT_ID),
                ("R2_ACCESS_KEY_ID", settings.R2_ACCESS_KEY_ID),
                ("R2_SECRET_ACCESS_KEY", settings.R2_SECRET_ACCESS_KEY),
                ("R2_BUCKET_NAME", settings.R2_BUCKET_NAME),
                ("R2_PUBLIC_URL", settings.R2_PUBLIC_URL),
            ]
            if not val
        ]
        if missing:
            raise R2ConfigError(f"R2 configuration missing: {', '.join(missing)}")

        import boto3

        self._bucket = settings.R2_BUCKET_NAME
        self._public_url = settings.R2_PUBLIC_URL.rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes to R2 and return the CDN URL."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{self._public_url}/{key}"

    def generate_presigned_url(self, key: str, expires_in: int = 86400) -> str:
        """Generate a presigned GET URL valid for expires_in seconds (default 24h)."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
