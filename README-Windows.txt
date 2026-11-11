CREDNA'S CREATION KIT — WINDOWS x64

RUN
1. Extract the Windows-x64 ZIP to a permanent folder.
2. Double-click Crednas-Creation-Kit.exe. Python and extra libraries are bundled.
3. Open data...: select your own extracted game/romfs/GameData folder.
4. English names...: select your own USen folder if it was not found automatically.

Windows 10/11, 64-bit Intel or AMD. No administrator access is needed.
You can create a desktop shortcut to the EXE. Opening the EXE from inside the
ZIP is not the supported workflow: extract the ZIP first.

All sixteen modules are included, including Appearance rules, Profiles & Affiliations, Facilities & Rewards, Shop & Loot, Battle deployment, Legion and Progression & Difficulty. Existing JSON
projects are compatible when paired with their original, unchanged game data.
Version 0.17 adds experimental Add entry / Duplicate entry / Undo last addition
controls inside existing learning lists. Projects with added rows need 0.17+.
Version 0.18 adds New list / Duplicate list / Remove new list controls. New
LIDs appear in the character learning chooser. Projects with new lists need
0.18+. Version 0.19 adds New item / Duplicate item / Remove new item in all
three supported item files. New items use the item v3 project format and need
0.19+. Version 0.20 adds New class / Duplicate class / Remove new class on
Classes > Overview, all 134 values and direct links, live JID choosers and Used
by navigation. Projects with new classes need 0.20+ (class v2). Character
creation is available in 0.21: Characters > Character tab > New character /
Duplicate character / Remove new character. Copies use a newly chosen serial
(default 0); nonzero serials must be unused, and original slots stay fixed. New
PIDs appear in pickers, Used by, v3 projects and exports. Independent support/
recruitment/story/assets and new localization text are not generated. Definitions are
experimental until tested in game; original IDs, indexes and serials stay unchanged.
Keep originals and test added learning rows in-game; runtime limits are unverified.
If a project was saved on Linux, use Open data... and English names... to pick
the Windows folders, then File > Open project... to load it. Save the project
again to associate Open last project with those Windows paths.

Settings/glossary/recent paths live in %APPDATA%\fw-character-editor.
An unexpected startup error is recorded in application.log in that folder.
Save project... keeps your editable JSON. Export mod... writes a separate mod
folder; it does not overwrite original game data. Edited mods need in-game tests.
See README.md for fields, source-file separation and interpretation limits.

UPGRADE
Save your project and close the old editor, then extract the new Windows ZIP
and use its EXE. Your settings are kept outside the application folder.

BUILD FROM SOURCE (optional, for maintainers)
Install official 64-bit Python 3.12 from python.org with Tcl/Tk, pip and the
Python launcher. Extract the complete source ZIP, then double-click
build-windows.bat. It creates a local virtual environment, installs the pinned
build dependencies, runs format tests, builds the windowed executable and
checks its GUI/native decompression before writing a Windows ZIP into dist.
Internet is needed for initial build dependencies, not for using the editor.
Alternatively, in an existing Windows Python environment:

  python -m pip install -r requirements-windows-build.txt
  python build_windows.py

Source-only launch: py -m pip install zstandard, then py fw_editor.py.
The packaged build needs neither command. Linux installation remains install.sh.

The EXE is unsigned. If Windows asks about an unknown publisher, verify that
you obtained the release from the project folder; this build has no signature.

VERSION 0.22: EVENTS
Module > Events adds 13 variable/timeline/chapter/situation sources. Edit existing
event conditions, arguments, flags and dates; names/hash keys/headers/counts/order
stay fixed. Majide cape tab links the exact Ink-Black Wen rules and duel. See
EVENT-RESEARCH.md for findings and a focused test; no cape change is pre-applied.
Projects use event v1 tied to original filename/SHA; full-folder exports now have
204 GameData files. The original wrapper/identifier inspector remains available.
Version 0.23 adds the separate compiled-script editor described below. Dialogue
message-file writing remains outside its scope.
Test event changes in-game with source/save backups; refresh timing is unverified.

VERSION 0.23: COMPILED SCRIPT EDITING
Tools > Script editor... (also Events > Compiled scripts > Open script editor)
opens the function/instruction and string-constant editor. Keep Script beside
GameData. Edit runtime strings, 32/64-bit literals, invert paired conditions or
replace calls with existing identical signatures. Instruction counts/stack slots/
branch targets stay fixed. This is not recovered source or a full compiler.
See SCRIPT-EDITOR.md for details, use links, translation previews and limits.
Normal Save project/Export mod include selected scripts; compressed outputs go
under romfs/Script. Script projects need 0.23+ (suite v2). Older GameData-only
projects still load. Original files stay unchanged. Structural checks do not
replace in-game tests; use separate mods and save backups.

VERSION 0.24: OFFICIAL RENAME
The program is now Credna's Creation Kit (formerly FW Hacking Suite). Download
Crednas-Creation-Kit-0.24-Windows-x64.zip and run Crednas-Creation-Kit.exe.
Existing projects and the fw-character-editor settings folder remain compatible.
See GITHUB-UPLOAD.md for source/release publishing instructions.
