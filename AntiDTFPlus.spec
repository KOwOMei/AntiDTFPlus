# -*- mode: python ; coding: utf-8 -*-

gui_a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('src/auto_service.py', 'src')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False
)
gui_pyz = PYZ(gui_a.pure, gui_a.zipped_data)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    gui_a.binaries,
    gui_a.zipfiles,
    gui_a.datas,
    name='AntiDTFPlus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False
)

service_a = Analysis(
    ['run_service.py'],
    pathex=[],
    binaries=[],
    datas=[('src/auto_service.py', 'src')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False
)
service_pyz = PYZ(service_a.pure, service_a.zipped_data)
service_exe = EXE(
    service_pyz,
    service_a.scripts,
    service_a.binaries,
    service_a.zipfiles,
    service_a.datas,
    name='AntiDTFPlusServiceHandler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False
)