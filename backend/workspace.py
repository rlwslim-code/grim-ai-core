"""Bounded project archive export. Never follow links or expose hidden configuration."""
import io
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .executor import MAX_FILE, MAX_WORKSPACE

def workspace_zip(root: Path) -> bytes:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Workspace does not exist')
    output = io.BytesIO()
    total = 0
    count = 0
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for item in sorted(root.rglob('*')):
            relative = item.relative_to(root)
            if item.is_symlink() or any(part.startswith('.') for part in relative.parts):
                continue
            if not item.is_file():
                continue
            if not item.resolve().is_relative_to(root):
                raise ValueError('Workspace path escaped its root')
            size = item.stat().st_size
            total += size
            count += 1
            if size > MAX_FILE or total > MAX_WORKSPACE or count > 500:
                raise ValueError('Workspace exceeds export limits')
            archive.write(item, arcname=relative.as_posix())
    return output.getvalue()
