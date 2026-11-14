# **NO GAME FILES ARE INCLUDED.**

**This program cannot run or emulate games. It only edits files that you provide.**

# Credna's Creation Kit 1.02

A Windows and Linux file editor for **Fortune's Weave**, supporting game version **1.00**.

## Features

- Edit characters, classes, stats, aptitudes, skills and items.
- Create or duplicate characters, classes, items and learning lists; expand supported learning entries.
- Browse appearance IDs and edit appearance rules, profiles and affiliations.
- Edit supports, recruitment, Wings of Salvation percentages, facilities, rewards, shops and loot.
- Add or duplicate inventory entries in existing shops, including newly created items.
- Edit battle deployment, Legion definitions, automatic progression and difficulty adjustments.
- Edit event conditions and timelines, plus supported compiled-script constants and instructions.
- Browse forced tutorial sequences, inspect progression dependencies and test supported guidance bypasses.
- View English/glossary previews beside stored values and follow supported reference links.
- Save projects, reopen your last project and export edits to a separate mod folder.

## Install

Download the package for your system from [Releases](https://github.com/Donlott/crednas-creation-kit/releases/latest).

### Windows

Extract the **Windows-x64 ZIP**, then run **Crednas-Creation-Kit.exe**. Python and required libraries are included. Supports Windows 10/11 on Intel/AMD 64-bit systems.

### Linux

Extract the **Linux ZIP**. It contains the Python application and shortcut installer, not a standalone executable. Requires Python 3.10+, Tk and the system Zstandard library.

On Pop!_OS/Ubuntu:

```sh
sudo apt install python3 python3-tk libzstd1
```

From the extracted application folder:

```sh
bash install.sh
```

You can also start it with `python3 fw_editor.py`.

## Use and documentation

Choose **Open data…** to select your own extracted data. Optionally choose **English names…** for readable previews. Save your work with **Save project…** and use **Export mod…** to write a separate output folder.

The [user guide](docs/Home.md) explains setup, projects and each module. The editor does not create game dumps, supply missing content, or test mods in-game.

## License

[MIT](LICENSE). Required third-party notices are in [licenses](licenses/).
