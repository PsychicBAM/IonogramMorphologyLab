# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\ionogram_morphology_lab\\app\\main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/ionogram_morphology_lab/i18n', 'ionogram_morphology_lab/i18n'), ('config', 'config'), ('knowledge_base', 'knowledge_base'), ('matlab_builtin', 'matlab_builtin'), ('rule_packs', 'rule_packs'), ('synthetic_data', 'synthetic_data'), ('docs', 'docs'), ('assets', 'assets'), ('matlab_helpers', 'matlab_helpers'), ('matlab_studio_library', 'matlab_studio_library')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IonogramMorphologyLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:\\ionog\\conference_presentation\\IonogramMorphologyLab\\assets\\IonogramMorphologyLab.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IonogramMorphologyLab',
)
