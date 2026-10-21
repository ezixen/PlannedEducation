import zipfile
import os
from pathlib import Path

modules_dir = Path('modules')
output_zip = Path('../modules_by_country.zip')

with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for file_path in modules_dir.rglob('*'):
        if file_path.is_file():
            arcname = file_path.relative_to(modules_dir)
            zf.write(file_path, arcname)

print(f'Created {output_zip}')
print(f'Size: {output_zip.stat().st_size / (1024*1024):.2f} MB')
all_files = list(modules_dir.rglob('*'))
files_only = [f for f in all_files if f.is_file()]
print(f'Files: {len(files_only)}')