"""Acquisition boundary for local images."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Tuple, Union

from PIL import Image

from .contracts import Availability, SourceInput, SourceValidation


def source_hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def validate_source(source: SourceInput) -> SourceValidation:
    digest = source_hash(source.data)
    try:
        with Image.open(BytesIO(source.data)) as image:
            image.verify()
        with Image.open(BytesIO(source.data)) as image:
            return SourceValidation(
                valid=True,
                content_hash=digest,
                availability=Availability.AVAILABLE,
                format=image.format,
                width=image.width,
                height=image.height,
            )
    except (OSError, ValueError) as exc:
        return SourceValidation(
            valid=False,
            content_hash=digest,
            availability=Availability.UNAVAILABLE,
            error=f"invalid image: {exc}",
        )


def load_source(path: Union[str, Path]) -> Tuple[SourceInput, SourceValidation]:
    path = Path(path)
    source = SourceInput(path.read_bytes(), name=path.name)
    return source, validate_source(source)
