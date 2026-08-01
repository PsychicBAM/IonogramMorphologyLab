#!/usr/bin/env python3
"""Document synthetic-data screenshot capture; never fail headless CI."""
from __future__ import annotations
SCREENS=['Home','Import Data / Data Audit','Instrument Profile','Viewer','Results','Expert Review','Rule Builder','Rule Testing Lab','Reports']
def main():
 print('Required synthetic teaching screenshots:')
 print(*(' - '+x for x in SCREENS),sep='\n')
 try:
  from PySide6 import QtWidgets  # noqa: F401
 except ImportError:
  print('PySide6 unavailable; documentation-only mode (success).'); return 0
 print('Qt available. Capture only synthetic teaching projects; automated capture is intentionally not implemented.')
 return 0
if __name__=='__main__': raise SystemExit(main())
