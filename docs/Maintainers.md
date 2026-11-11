# Building and publishing

The source contains the editor, tests, documentation and third-party notices. It includes no game files. Keep game content, personal projects, exports and build caches outside source-control uploads.

## Checks

Run `python -m unittest discover -s tests -v` from the source folder. Tests that require private inputs skip when those inputs are unavailable; the synthetic fixtures are authored test data. Format tests and GUI startup checks do not validate a mod in-game.

## Windows build

Use 64-bit Windows Python 3.12 with Tcl/Tk. Install `requirements-windows-build.txt`, then run `python build_windows.py` or the supplied build batch file. The build runs tests, creates the windowed executable and checks frozen startup, branding and decompression. It includes the user guide and required license notices in the Windows ZIP.

## GitHub releases

The **Publish Linux and Windows release** workflow is manually triggered from Actions. Supply a source commit, tag or branch. It packages the Linux Python application/installer, builds Windows from the same resolved commit, validates the archives, and uploads both with SHA-256 checksums. Only the publishing job requests repository-content write access.

A version comes from the application's `VERSION` value. The workflow refuses to replace an already published release; use a new application version for a new release. The separate Windows workflow can build a downloadable Actions artifact without publishing a release.

The application version is **1.00**. Game-format support and serialized project format identifiers are separate from the application version. Existing configuration locations and project identifiers remain stable for compatibility.

[Guide home](Home.md)
