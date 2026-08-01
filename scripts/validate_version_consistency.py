#!/usr/bin/env python3
"""Reject obsolete active product versions while allowing changelog history."""
from __future__ import annotations
import re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['pyproject.toml','README.md','README_RU.md','src/ionogram_morphology_lab/__init__.py','src/ionogram_morphology_lab/app/settings_store.py']
ABOUT_FILES=['src/ionogram_morphology_lab/i18n/en.json','src/ionogram_morphology_lab/i18n/ru.json']
def main():
 errors=[]
 for rel in FILES:
  p=ROOT/rel
  if not p.exists(): errors.append(f'missing {rel}'); continue
  text=p.read_text(encoding='utf-8')
  if '1.1.1' not in text: errors.append(f'{rel}: missing active version 1.1.1')
  if re.search(r'(?<![0-9])1\.(?:0\.0|1\.0)(?![0-9])',text): errors.append(f'{rel}: obsolete active version')
 for rel in ABOUT_FILES:
  p=ROOT/rel
  if not p.exists(): errors.append(f'missing {rel}'); continue
  text=p.read_text(encoding='utf-8')
  if 'about.body' not in text: errors.append(f'{rel}: missing About string')
  if re.search(r'(?<![0-9])1\.(?:0\.0|1\.0)(?![0-9])',text): errors.append(f'{rel}: obsolete About version')
 if errors: print(*errors,sep='\n'); return 1
 print('Version consistency passed.'); return 0
if __name__=='__main__': raise SystemExit(main())
