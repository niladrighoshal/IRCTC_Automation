# -*- mode: python ; coding: utf-8 -*-

# This is a PyInstaller spec file. It tells PyInstaller how to build your application
# into a single executable file.
# To build the application, run the following command in your terminal:
# pyinstaller build.spec

block_cipher = None

# --- Analysis: Finding all the necessary files ---
a = Analysis(['master.py'],
             pathex=['.'],
             binaries=[],
             # Add all non-python files here (e.g., .json, .png)
             # The first item in the tuple is the source file, the second is the destination directory in the bundle.
             datas=[
                 ('src', 'src'),
                 ('main.py', '.'),
                 ('requirements.txt', '.')
             ],
             # Add modules that PyInstaller might not find automatically.
             hiddenimports=[
                 'streamlit',
                 'selenium',
                 'requests',
                 # Add other hidden imports if the build fails with ModuleNotFoundError
                 'blinker',
                 'watchdog',
                 'altair'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# --- PYC: Bundling the python bytecode ---
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# --- EXE: Creating the executable ---
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='IRCTC_Tatkal_Bot', # The name of your final executable
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True ) # True = shows a console window, False = hides it.

# --- COLLECT: Gathering all the files into one place ---
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='dist') # The output directory will be named 'dist'
