from io import BytesIO
from zipfile import ZipFile
import pytest
from backend.workspace import workspace_zip

def test_archive_includes_project_but_excludes_hidden_and_symlinks(tmp_path):
    (tmp_path/'src').mkdir()
    (tmp_path/'src'/'app.py').write_text('print(42)')
    (tmp_path/'.env').write_text('SECRET=hide')
    (tmp_path/'leak').symlink_to('/etc/passwd')
    with ZipFile(BytesIO(workspace_zip(tmp_path))) as z:
        assert z.namelist()==['src/app.py']
        assert z.read('src/app.py')==b'print(42)'

def test_archive_rejects_oversized_files(tmp_path):
    (tmp_path/'large.txt').write_bytes(b'x'*262145)
    with pytest.raises(ValueError,match='limits'):
        workspace_zip(tmp_path)
