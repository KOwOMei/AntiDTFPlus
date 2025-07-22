# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_gui.py', 'run_service.py'], # Указываем оба файла
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32service', 
        'win32serviceutil',
        'win32event',
        'servicemanager',
        'pywintypes',
        'win32timezone'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'], # Явно исключаем tkinter из сборки службы
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Собираем основной EXE для GUI
exe_gui = EXE(
    pyz,
    a.scripts[0], # Первый скрипт (run_gui.py)
    name='AntiDTFPlus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/assets/icon.ico' # Укажите путь к иконке, если есть
)

# Собираем второй, "служебный" EXE
exe_service = EXE(
    pyz,
    a.scripts[1], # Второй скрипт (run_service.py)
    name='AntiDTFPlusServiceHandler', # Даем ему другое имя
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # С консолью для отладки, потом можно убрать
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_gui,
    exe_service, # Добавляем оба EXE в итоговую папку
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntiDTFPlus'
)
