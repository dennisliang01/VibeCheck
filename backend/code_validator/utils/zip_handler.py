"""ZIP file handler for extracting and processing code archives."""

import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional


class ZipHandler:
    """Handles ZIP file extraction and cleanup."""

    def __init__(self):
        self.temp_dir: Optional[Path] = None

    def extract(self, zip_path: str) -> str:
        """Extract ZIP file to temporary directory.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Path to the extracted directory

        Raises:
            FileNotFoundError: If ZIP file doesn't exist
            zipfile.BadZipFile: If file is not a valid ZIP
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="code_validator_"))

        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(self.temp_dir)

        # Handle nested directories (if ZIP contains a single root folder)
        extracted_items = list(self.temp_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            return str(extracted_items[0])

        return str(self.temp_dir)

    def cleanup(self):
        """Clean up temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
