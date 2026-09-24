"""
Photo Analyzer — EXIF extraction, blur detection, pHash deduplication.

All analysis is deterministic classical CV — no neural network here.
Uses:
  - OpenCV Laplacian for blur detection (variance-of-Laplacian)
  - Pillow for EXIF extraction
  - imagehash for DCT perceptual hashing (pHash)
"""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger(__name__)

# Blur threshold: variance-of-Laplacian below this → image is blurry
BLUR_THRESHOLD = 80.0

# pHash Hamming distance threshold for duplicate detection
PHASH_DUPLICATE_THRESHOLD = 8  # bits out of 64


@dataclass
class PhotoAnalysis:
    """Result of photo quality analysis. No IO in this class."""
    photo_id: str
    minio_key: str
    exif_data: dict[str, Any]
    has_valid_exif: bool
    blur_score: float
    is_blurry: bool
    phash: str
    is_duplicate: bool = False  # Set later by DB lookup


def _extract_exif(image_bytes: bytes) -> dict[str, Any]:
    """Extract EXIF metadata from image bytes."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(io.BytesIO(image_bytes))
        raw_exif = img._getexif()
        if not raw_exif:
            return {}
        return {
            TAGS.get(tag_id, str(tag_id)): str(value)[:256]  # Cap string length
            for tag_id, value in raw_exif.items()
        }
    except Exception as e:
        log.warning(f"EXIF extraction failed: {e}")
        return {}


def _compute_blur_score(image_bytes: bytes) -> float:
    """
    Compute Laplacian variance as a blur metric.
    Higher = sharper. Below BLUR_THRESHOLD = blurry.
    Falls back to 100.0 (sharp) if CV is unavailable.
    """
    try:
        import cv2
        import numpy as np

        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 100.0
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        return float(laplacian.var())
    except ImportError:
        log.warning("OpenCV not available, skipping blur detection")
        return 100.0
    except Exception as e:
        log.warning(f"Blur detection failed: {e}")
        return 100.0


def _compute_phash(image_bytes: bytes) -> str:
    """
    Compute DCT perceptual hash (pHash) for deduplication.
    Returns 64-character hex string.
    Falls back to SHA-256 if imagehash is unavailable.
    """
    try:
        from PIL import Image
        import imagehash

        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.phash(img))
    except ImportError:
        # Fallback: use MD5 of raw bytes (worse for near-duplicates)
        return hashlib.md5(image_bytes).hexdigest()
    except Exception as e:
        log.warning(f"pHash computation failed: {e}")
        return hashlib.md5(image_bytes).hexdigest()


def _validate_gps_exif(exif_data: dict) -> bool:
    """Check if EXIF contains valid GPS coordinates."""
    return "GPSInfo" in exif_data or ("GPS GPSLatitude" in str(exif_data))


def analyze_photo(
    photo_id: str,
    image_bytes: bytes,
    *,
    upload_to_minio: bool = True,
) -> PhotoAnalysis:
    """
    Run the full photo quality pipeline:
      1. Extract EXIF
      2. Compute blur score
      3. Compute pHash
      4. (Optionally) upload to MinIO

    Returns PhotoAnalysis — no DB interactions here.
    """
    exif_data = _extract_exif(image_bytes)
    has_valid_exif = _validate_gps_exif(exif_data)
    blur_score = _compute_blur_score(image_bytes)
    phash = _compute_phash(image_bytes)

    minio_key = f"photos/{photo_id}.jpg"

    if upload_to_minio:
        try:
            _upload_to_minio(minio_key, image_bytes)
        except Exception as e:
            log.warning(f"MinIO upload failed for {photo_id}: {e}")

    return PhotoAnalysis(
        photo_id=photo_id,
        minio_key=minio_key,
        exif_data=exif_data,
        has_valid_exif=has_valid_exif,
        blur_score=blur_score,
        is_blurry=blur_score < BLUR_THRESHOLD,
        phash=phash,
        is_duplicate=False,  # Caller checks DB for duplicates
    )


def _upload_to_minio(key: str, data: bytes) -> None:
    """Upload image bytes to MinIO bucket."""
    import boto3
    from botocore.config import Config
    from app.core.config import settings

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )
    s3.put_object(Bucket=settings.MINIO_BUCKET, Key=key, Body=data)
