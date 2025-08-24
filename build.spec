# -*- mode: python ; coding: utf-8 -*-

# To build the executable, run the following command from your terminal
# in the project root directory:
#
# pyinstaller --onefile --windowed --icon="G:\Downloads\ABDM\Pictures\irctc_icon.ico" build.spec
#
# Note: You might need to adjust the icon path.
# The '--windowed' flag hides the console window. For debugging, you can remove it.

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# The entry point is the Streamlit UI
a = Analysis(['Form/passenger_details.py'],
             pathex=[os.getcwd()],
             binaries=[],
             datas=[],
             hiddenimports=[
                'streamlit.web.server.server',
                'engineio.async_drivers.threading',
                'streamlit.runtime.scriptrunner',
                'pandas',
                'numpy'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Add data files. This is crucial for Streamlit and our own JSON files.
# It ensures that files inside these folders are bundled with the exe.
a.datas += collect_data_files('Form')
a.datas += collect_data_files('Automation')
a.datas += copy_metadata('streamlit')
a.datas += copy_metadata('undetected-chromedriver')

# Add root-level files manually
a.datas += [('requirements-cpu.txt', '.', 'DATA'),
            ('requirements-gpu.txt', '.', 'DATA'),
            ('gui_manager.py', '.', 'DATA'),
            ('main.py', '.', 'DATA')]


pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='IRCTC_Booking_Bot',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False, # Set to False for windowed app
          icon='G:\\Downloads\\ABDM\\Pictures\\irctc_icon.ico')
