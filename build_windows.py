"""Build on 64-bit Windows after installing requirements-windows-build.txt."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import zipfile
from importlib.metadata import distribution
from branding import APP_NAME, APP_SLUG


def main():
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise SystemExit('Build with 64-bit Windows Python; PyInstaller is not a cross-compiler.')
    root = Path(__file__).resolve().parent
    import fw_editor
    name = APP_SLUG
    # Synthetic format tests never require or bundle game files.
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onefile', '--windowed', '--noupx', '--name', name,
                    '--collect-all', 'zstandard', '--copy-metadata', 'zstandard',
                    'windows_launcher.py'], cwd=root, check=True)
    executable = root/'dist'/(name+'.exe')
    report = root/'dist'/'windows-self-test.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(executable), '--self-test', str(report)], cwd=root, check=True, timeout=120)
    health = json.loads(report.read_text(encoding='utf8'))
    if not health.get('frozen') or not health.get('zstandard') or health.get('version') != fw_editor.VERSION or health.get('app_name') != APP_NAME:
        raise SystemExit('Packaged executable failed its health check.')
    bundle = root/'dist'/f'{name}-{fw_editor.VERSION}-Windows-x64.zip'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        folder = name+'/'
        archive.write(executable, folder+executable.name)
        for filename in ('README-Windows.txt', 'README.md', 'EVENT-RESEARCH.md', 'SCRIPT-EDITOR.md', 'GITHUB-UPLOAD.md', 'LICENSE'):
            archive.write(root/filename, folder+filename)
        # Preserve notices for bundled libraries, including Python, Tcl/Tk and Zstd.
        python_license = Path(sys.base_prefix)/'LICENSE.txt'
        if not python_license.is_file():
            raise SystemExit('Python LICENSE.txt is missing from the build installation.')
        archive.write(python_license, folder+'licenses/Python-LICENSE.txt')
        tcl = Path(sys.base_prefix)/'tcl'
        for notice in sorted(tcl.glob('*/license.terms')):
            archive.write(notice, folder+'licenses/'+notice.parent.name+'-license.terms')
        for notice in sorted((root/'licenses').iterdir()):
            if notice.is_file():archive.write(notice, folder+'licenses/'+notice.name)
        for project in ('zstandard', 'pyinstaller'):
            package = distribution(project)
            notices = [file for file in package.files or [] if 'licenses/' in str(file).replace('\\', '/')]
            if not notices:
                raise SystemExit(project+' license notices were not found.')
            for notice in notices:
                if package.locate_file(notice).is_file():
                    archive.write(package.locate_file(notice), folder+'licenses/'+project+'-'+notice.name)
    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
    print('Created '+str(bundle))


if __name__ == '__main__':
    main()
