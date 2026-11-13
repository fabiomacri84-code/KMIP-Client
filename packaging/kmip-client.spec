# Build: python -m PyInstaller --noconfirm --clean packaging/kmip-client.spec
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from app_version import __version__
analysis = Analysis(
    [str(root / 'desktop.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'assets'), 'assets'),
           (str(root / 'templates' / 'index.html'), 'templates'),
           (str(root / 'templates' / 'readme.html'), 'templates')] + collect_data_files('kmip', includes=['version.py'], include_py_files=True),
    hiddenimports=['webview.platforms.qt', 'PySide6.QtWebEngineWidgets',
                   'PySide6.QtWebChannel', 'PySide6.QtNetwork'],
    hookspath=[],
    excludes=['tkinter', 'webview.platforms.gtk', 'webview.platforms.cocoa',
              'webview.platforms.winforms', 'webview.platforms.edgechromium',
              'PyQt5', 'PyQt6', 'PySide2', 'pytest', 'IPython', 'notebook'],
    noarchive=False,
)
if sys.platform.startswith('linux'):
    # Driver e configurazione dei font devono usare le librerie del desktop,
    # non copie più vecchie che possono confliggere con Fedora/Ubuntu recenti.
    system_libraries = {'libstdc++.so.6', 'libgcc_s.so.1', 'libfontconfig.so.1', 'libfreetype.so.6'}
    analysis.binaries = [entry for entry in analysis.binaries
                         if Path(entry[0]).name not in system_libraries]
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='kmip-test-client',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=sys.platform != 'win32', disable_windowed_traceback=False,
          icon=str(root / 'assets' / 'icon.ico') if sys.platform == 'win32' else None)
collection = COLLECT(exe, analysis.binaries, analysis.datas, strip=False,
                     upx=False, name='KMIP-Test-Client')
if sys.platform == 'darwin':
    app = BUNDLE(collection, name='KMIP Test Client.app',
                 icon=str(root / 'assets' / 'icon.icns'),
                 bundle_identifier='it.kmiptest.client',
                 info_plist={'CFBundleShortVersionString': __version__,
                             'CFBundleVersion': __version__,
                             'NSHighResolutionCapable': True})
