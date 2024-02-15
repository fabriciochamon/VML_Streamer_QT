# -*- mode: python ; coding: utf-8 -*-
import os

datas = []

# add images
imgs = [('./images/'+item, './images') for item in sorted(os.listdir('./images'))]
datas.extend(imgs)

# add stream types
st_files = [item for item in os.listdir('.') if item.startswith('st_')]
for st_file in st_files:
    datas.append(
        (st_file, '.')
    )

# add qt stylesheet
datas.append(('stylesheet.qss', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('./models/*', './models')],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
splash = Splash(
    './images/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(180, 160),
    text_size=10,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='vml_streamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
