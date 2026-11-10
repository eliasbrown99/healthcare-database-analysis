"""Check the explicitly reviewed publication file list before committing or deploying."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
policy = ROOT / 'publication-files.txt'
allowed = {line for line in policy.read_text().splitlines() if line}
errors = []
for rel in sorted(allowed):
    path = ROOT / rel
    if Path(rel).is_absolute() or '..' in Path(rel).parts:
        errors.append(f'Invalid path: {rel}')
    elif path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        errors.append(f'Missing or unsafe file: {rel}')
    elif path.stat().st_size >= 100 * 1024 * 1024:
        errors.append(f'File exceeds GitHub limit: {rel}')
if (ROOT / '.git').exists():
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().rstrip('\0').split('\0')) - {''}
    errors.extend(f'Tracked file has not been approved for publication: {p}' for p in sorted(tracked - allowed))
if errors:
    raise SystemExit('Publication check failed:\n' + '\n'.join(errors))
print(f'Publication check passed: {len(allowed)} explicitly listed files; no unapproved tracked files.')
