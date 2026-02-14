import aiofiles
import uuid
from pathlib import Path
from fastapi import UploadFile

from ..config import settings


class ImageStorage:
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> tuple[str, str]:
        """Save uploaded file and return (filename, filepath)."""
        ext = Path(file.filename).suffix if file.filename else ".jpg"
        unique_name = f"{uuid.uuid4()}{ext}"
        filepath = self.upload_dir / unique_name

        async with aiofiles.open(filepath, "wb") as f:
            content = await file.read()
            await f.write(content)

        return unique_name, str(filepath)

    async def delete(self, filepath: str) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        path = Path(filepath)
        if path.exists():
            path.unlink()
            return True
        return False

    def get_path(self, filename: str) -> Path:
        """Get full path for a filename."""
        return self.upload_dir / filename


image_storage = ImageStorage()
