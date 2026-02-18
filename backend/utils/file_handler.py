import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from backend.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, MAX_RETAINED_FILES


def prune_directory(directory: Path, keep: int = MAX_RETAINED_FILES) -> None:
    """Delete the oldest files in a directory, keeping only the newest `keep` files."""
    files = sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime)
    for old_file in files[:-keep] if len(files) > keep else []:
        old_file.unlink(missing_ok=True)


class FileHandler:
    """Utility for handling file uploads"""

    @staticmethod
    async def save_upload_file(upload_file: UploadFile) -> tuple[str, Path]:
        """
        Save an uploaded file to the uploads directory.

        Args:
            upload_file: Uploaded file from FastAPI

        Returns:
            Tuple of (file_id, file_path)

        Raises:
            ValueError: If file is invalid
        """
        # Validate file extension
        filename = upload_file.filename or "unknown"
        file_ext = Path(filename).suffix.lower()

        if file_ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Create filename with ID to avoid collisions
        safe_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / safe_filename

        # Read and save file
        content = await upload_file.read()

        # Check file size
        if len(content) > MAX_UPLOAD_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB")

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Remove oldest uploads beyond the retention limit
        prune_directory(UPLOAD_DIR)

        return file_id, file_path

    @staticmethod
    def get_upload_path(file_id: str, file_type: str) -> Optional[Path]:
        """
        Get the path to an uploaded file.

        Args:
            file_id: File ID
            file_type: File extension (csv or xml)

        Returns:
            Path to file or None if not found
        """
        file_ext = f".{file_type}" if not file_type.startswith('.') else file_type
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

        if file_path.exists():
            return file_path
        return None

    @staticmethod
    def delete_upload(file_id: str, file_type: str) -> bool:
        """
        Delete an uploaded file.

        Args:
            file_id: File ID
            file_type: File extension

        Returns:
            True if deleted, False if not found
        """
        file_path = FileHandler.get_upload_path(file_id, file_type)
        if file_path and file_path.exists():
            file_path.unlink()
            return True
        return False

    @staticmethod
    def get_file_type(filename: str) -> str:
        """Get file type from filename"""
        return Path(filename).suffix.lower().replace('.', '')
