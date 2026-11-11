# Credna's Creation Kit 0.24

An original Windows and Linux desktop editor for Fortune's Weave **1.00**. Modules currently available: **Characters**, **Classes**, **Learning tables (LID)**, **GLID progression**, **Skills (SID)**, **Items (IID)**, **Supports & Recruitment**, **Appearance rules**, **Profiles & Affiliations**, **Facilities & Rewards**, **Shop & Loot**, **Battle deployment**, **Legion**, **Progression & Difficulty** the **AID browser**, and **Events**. Paragon was a UI reference only; no Paragon code or game files are included.

**New in 0.24:** the program is now officially **Credna's Creation Kit** (formerly **FW Hacking Suite**). Window titles, launchers, executable and release names use the new name. Existing projects, preferences and the translation glossary remain compatible. See [GITHUB-UPLOAD.md](GITHUB-UPLOAD.md) to publish the source and downloadable packages on GitHub.

**Added in 0.23:** **Tools → Script editor…** edits compiled ASF scripts: runtime string constants, numeric literals, paired condition inversion and existing calls with identical signatures. It rebuilds string caches, preserves instruction count/branch destinations, validates the result and exports compressed files under `romfs/Script`. It is a limited instruction editor, not a source decompiler/compiler. See [SCRIPT-EDITOR.md](SCRIPT-EDITOR.md) for supported changes and usage. All sixteen modules and earlier creation features remain included; the **Events** module and [Majide cape investigation](EVENT-RESEARCH.md) remain available.

## Install or upgrade

### Windows — new in 0.10.1

Download **Crednas-Creation-Kit-0.24-Windows-x64.zip**, extract it, then double-click **Crednas-Creation-Kit.exe**. Python, Tcl/Tk and Windows Zstandard support are bundled. Windows 10/11 on 64-bit Intel/AMD is supported by the package; no Python installation, administrator access or terminal commands are required to run it. You can create a normal Windows desktop shortcut to the executable.

All sixteen modules are included. Select your own game folder with **Open data…** and your own **USen** folder with **English names…**. Nothing from the game's data is included in the release. Save a project before closing the old version to upgrade. Settings and the local glossary are kept separately in `%APPDATA%\fw-character-editor`; unexpected startup errors are logged there in `application.log`. `FW_EDITOR_CONFIG` still overrides that path for testing/portable setups.

Projects use the same binary fingerprints and JSON format on both platforms. When moving a project between computers, open the original matching game data and English folder on the new computer, then **File → Open project…**. Saving it again associates **Open last project** with the new machine's paths. The Linux source package and Windows executable are separate downloads; `install.sh` remains the Linux shortcut installer.

The executable is unsigned. The Windows binary is built with Windows CPython/PyInstaller and exercised through Wine in the Linux build environment; it has not been independently tested on a physical Windows installation. The source includes a Windows build script and GitHub Actions workflow for native Windows rebuilds. See **README-Windows.txt** for details.

### Linux / source package

Close the previous editor after saving your edits as a JSON project. Extract the **whole** new ZIP into a permanent folder. Keep all Python modules from the archive together, including `branding.py`, `script_bytecode.py`, `script_data.py`, `script_opcodes.py`, `script_ui.py`, `event_data.py`, `event_ui.py`, `script_inspector.py`, `person_creation.py`, `person_index.py`, `person_ui.py`, `class_creation.py`, `class_index.py`, `class_ui.py`, `record_expansion.py`, `expanded_data.py`, `expanded_ui.py`, `legion_data.py`, `legion_ui.py`, `deployment_data.py`, `deployment_ui.py`, `shop_data.py`, `shop_ui.py`, `facility_data.py`, `facility_ui.py`, `profile_data.py`, `profile_ui.py`, `platform_support.py`, `appearance_data.py`, `appearance_ui.py`, `reliance_data.py`, `supports_ui.py`, `item_ui.py`, `item_index.py`, `skill_ui.py`, `skill_index.py`, `progression_ui.py`, `learning_ui.py`, `asset_index.py` and `aid_ui.py`. On Pop!_OS/Ubuntu, install Tk if needed:

```sh
sudo apt install python3-tk
```

Run this inside the extracted software folder to create/update the desktop and applications-menu shortcuts:

```sh
bash install.sh
```

The shortcut is now called **Credna's Creation Kit**. The old launcher file is reused to avoid duplicate entries. Keep the extracted folder in place. If the desktop icon opens as text, right-click it and choose **Allow Launching**.

You can also run directly:

```sh
python3 fw_editor.py
python3 fw_editor.py /path/to/game
```

Python 3.10+ and Tk are required. The system `libzstd` library reads compressed message tables. The Linux source editor has no pip dependencies. No Google Drive sync setup is required.

## Remembered paths and reopening (0.4.1)

Credna's Creation Kit remembers the last successful game-data folder, English-name folder, opened/saved project and mod-export folder. Folder/file dialogs start in the corresponding remembered location. Opening data also tries the last English-name folder when no adjacent USen folder was found.

After you **save or open a project once**, the **Open last project** button is enabled at startup (also available in File). It restores that JSON project with its own original game-data folder, English names and saved module. Browsing a different game-data folder later does not replace the remembered project's source-folder association.

This reopens the last saved/opened JSON project; it is not an autosave of unsaved edits. Export destinations are remembered separately. A missing project/source folder or a fingerprint mismatch produces an error before the active workspace is replaced. If only the saved English folder is unavailable, the project still opens and you can choose English names again.

Preferences store paths and the last project's module, without game data or unsaved edits. On Linux they are stored locally at `~/.config/fw-character-editor/recent-paths.json` (or the equivalent XDG configuration directory), beside the existing translation glossary. They persist across software upgrades. No paths or game files are uploaded by this feature. The first launch of 0.4.1 has no history from older versions until you open/save data and a project.

## Basic workflow

1. **Open data…**: select your extracted game folder, `romfs`, or `GameData`. The suite loads supported character, class, Growth, Skill, Item, Reliance, Profile, AssetTable, Facility, Reward and Legion files, including supported side files, plus battle files in `Dispos`. It also indexes readable GameData string pools for AIDs. A folder containing only one supported editable table or just appearance tables also works. A direct file path can be passed on the command line.
2. **English names…**: choose **USen** if names did not load automatically. Its parent folder is accepted too. The suite reads supported character/class/skill/item, profile, facility and reward message tables from your own extracted data.
3. Choose a module using the selector above the search box. All sixteen modules listed above are available, including **Battle deployment**, **Legion**, and **Progression & Difficulty**.
4. Search by English name or raw ID. Character search also accepts slot serials; class search accepts the numeric rank. All 137 class records are shown, including placeholders and enemy classes. Duplicate display names may represent different raw class IDs; inspect the heading and fields to distinguish them.
5. Edit fields, then choose **Apply edits**. Selecting another entry or switching modules also applies valid form edits to the in-memory project. Invalid input blocks the switch so it can be corrected.
6. **Save project…** saves the editable modules together in JSON, tied to the SHA-256 of each original table. **File → Open project…** restores them against the same original source files. Loading a project replaces workspace edits. Old 0.1/0.2 character-only JSON projects remain supported; loading one clears class edits after the replacement confirmation.
7. **Export mod…** writes every loaded supported table into a separate mod folder. All loaded editable modules' edits are included, regardless of which module is visible. Use an empty folder initially. Existing editor exports receive dated binary backups.
8. Put the entire output mod folder inside Eden's **Open Mod Data Location** directory, enable the mod, and restart the game to test. Existing saves may retain already-created unit values.

Example output when all **191 supported files** are loaded (20 root files and 171 Dispos files):

```text
MyMod/
  suite-edits.json
  romfs/
    GameData/
      Person.bin
      Job.bin
      Growth.bin
      Growth_P0.bin
      Variable.bin
      Variable_P0.bin
      Variable_P1.bin
      Timeline_Com.bin
      Timeline_Part0_Ism.bin
      Timeline_Part1_Dit.bin
      Timeline_Part1_Kai.bin
      Timeline_Part1_Led.bin
      Timeline_Part1_Seo.bin
      Timeline_Part2.bin
      Timeline_Part3_Ism.bin
      Chapter.bin
      Situation.bin
      Legion.bin
      Skill.bin
      Skill_P0.bin
      Skill_P1.bin
      Item.bin
      Item_P0.bin
      Item_P1.bin
      Reliance.bin
      Profile.bin
      Facility.bin
      Reward.bin
      Reward_P0.bin
      Reward_P1.bin
      AssetTable.bin
      AssetTable_P0.bin
      AssetTable_P1.bin
      Dispos/
        ... 171 battle files ...
```

Original game files are never overwritten. An existing unrelated binary is refused as an export target, including any Skill, Item, Reliance, Profile, Facility, Reward or AssetTable file. A prior character-only export can be upgraded to a suite export. If an output already contains tables not loaded in the current session, open the full source folder or choose a fresh output folder.

## Learning-table editor (LID) — new in 0.5

Choose **Module → Learning tables** with the original **Growth.bin** present in GameData. A standalone folder containing Growth.bin also works. The supplied file contains **96 LID collections and 4,034 learning entries**. The GLID progression editor below shares the same Growth.bin document.

The sidebar searches English/glossary names and raw LIDs and displays each table's entry count. The Entries tab lists each row's level, skill-type code, skill-level code, English skill name, raw SID and condition count. Select a row to edit:

| Field | Contents |
|---|---|
| Level | Original unsigned 8-bit value (`0–255`) |
| Skill type code | Original unsigned 8-bit category code; enum names are not inferred |
| Skill level code | Original unsigned 8-bit rank/threshold code; rank letters and zero-value behavior are not inferred |
| Skill reference | A raw SID with live English/glossary preview; **…** searches the loaded skill catalog |
| Required conditions | One raw condition ID per line, with matching English previews; **+** selects observed conditions |

**Apply edits** commits the selected row. Selecting another row/table/module also commits valid form changes; invalid values block navigation. **Copy entry** and **Paste values** transfer all five fields into an existing or added row, including across LID tables. **Swap ↑/↓** exchange adjacent row values while retaining the row headers. **Reset table** restores the selected LID's original values and removes its additions without resetting other LIDs, GLID, auxiliary Growth sections or modules.

**Used by** shows current direct Person.bin learning-list references, including unsaved character edits. Double-click or use **Open selected entry** to open that character. This is not a scan of scripts or GLID-derived behavior. The supplied primary Job.bin schema has no learning-list field to include here.

### Adding learning entries — experimental in 0.17

- **Add entry** appends a blank row to the selected existing LID. Defaults are level 1, type/rank code 0, an empty SID and no conditions. Choose the desired skill and requirements before exporting. Empty existing lists can receive their first row.
- **Duplicate entry** appends a copy of the selected row's five current values, including valid pending form edits. Changes to the copy's conditions do not change the source row.
- **Undo last addition** removes only the last row added to the selected list. It never deletes an original entry. You can undo repeatedly; the button is disabled when no additions remain.
- Existing LID IDs and original row numbers stay fixed. New rows are appended at the end. Entire learning lists can now be created as described below. Renaming existing tables, middle insertion and deletion of original rows are not implemented. Character creation is available in 0.21, class creation in 0.20, and item creation in 0.19. GLID and other modules retain their existing fixed row counts.

The exporter inserts new row blocks, updates collection counts and rebuilds pointer locations, targets, indexed labels, schema pointers and string-pool offsets. Existing record-header tags and opaque bytes are preserved. New rows receive unused ascending 16-bit tags within the learning group. **The runtime meaning of that extra header field remains unverified, so additions are experimental and require an in-game test.** Format count/tag bounds are checked; these bounds do not establish the game's runtime list limits or save compatibility. Initially test one useful additional skill in a separate mod and keep your original data and save backups.

Projects containing additions use **`fw-growth-edits-v3`** and require **0.17 or newer**. They store the new rows alongside original LID, GLID and auxiliary Growth edits, tied to the unchanged original Growth.bin fingerprint. **Open last project** restores the additions. Projects without additions retain the existing v1/v2 formats. Loading an older project replaces additions as well as edits, with the normal replacement prompt. An addition with untouched default values still counts as a workspace edit.

### Creating complete learning lists — experimental in 0.18

1. Choose **New list…** above the entry grid and enter an unused ID beginning with **`LID_`**, for example `LID_MyCustomList`. The new list starts empty. Add its first row with **Add entry**.
2. Alternatively select a source list, then choose **Duplicate list…** and give the copy a new ID. This copies **all five current values of every row**, including pending valid edits and added rows, into an independent list. Changing the copy does not change its source. This also works for empty lists or another new list.
3. In **Characters**, select the character and edit **Learning tables** (`0x88`). Its chooser includes current Growth learning lists immediately, including new ones. Remove unwanted old references if replacing a list; the chooser appends its selection. Multiple assigned lists stay a stored list of references. The learning chooser is scoped to learning lists rather than the unrelated Legion LID namespace.
4. **Used by** shows loaded characters currently assigned to the new list. **Skills → Used by** also finds skills in new lists and navigates to the exact new row.
5. **Reset table** clears a new list's rows but keeps its ID. **Remove new list** deletes a newly created list and its rows; it is disabled for original lists. Removal is blocked while a loaded character's current learning references use that ID. Unloaded files/scripts and implicit references cannot be checked here.

IDs must be unique within Growth.bin, begin with `LID_` plus a name, and contain no nulls, line breaks, surrounding whitespace or the reserved `::` row separator. Original IDs, source list indexes and original row ordinals remain intact. New headers are appended to the existing collection-header array and indexed in the label table; their rows and all original targets/pointers are relocated together. Blank lists have an actual indexed header and zero rows, not an unregistered reference string.

Projects with new lists use **`fw-growth-edits-v4`** and require **0.18 or newer**. List definitions are restored before their rows and field edits. Older v1/v2/v3 Growth and suite projects remain supported; replacing a project clears omitted new lists. Invalid loads restore both headers and row edits transactionally. All changes and character assignments export together in one Growth.bin and the corresponding Person.bin when loaded. No original source is overwritten.

**New lists remain experimental.** New header tags use unused values while existing tags are preserved, but their runtime meaning, engine limits and save compatibility have not been verified in-game. First test a short new list assigned to one character in a separate mod and retain your original files/save backups. Creating a list does not automatically assign it, evaluate skill requirements, or create new SIDs. New GLID tables/category rows remain outside this update; character creation is available in 0.21, class creation in 0.20, and item creation in 0.19 below.

Learning data shares Growth.bin with GLID progression, experience and other groups. Export writes Growth.bin with both learning and GLID edits and rebuilt relocation/string metadata, preserving all other groups. Changed condition lists use separate arrays so shared lists are not edited in place. The additional supplied Growth_P0.bin contains another data group, not LIDs, and is not modified or exported by this module.

Character, class, learning and GLID edits save together in the suite project, and export together when their source tables are loaded. Growth.bin retains its own source fingerprint. Earlier character/class projects remain loadable and clear learning edits when replacing the workspace. **Open last project** also restores the Learning tables module.

Changes to a shared LID affect every character that references it. Reference strings can be typed manually; structural validation does not prove a new SID/condition exists or that its gameplay behavior is valid. Edited learning tables still need an in-game test.

## GLID automatic-progression editor — new in 0.6

Choose **Module → GLID progression** with the original **Growth.bin** loaded. The supplied 1.00 file contains **206 GLID collections, 1,630 category rows and 81 fields per row**: a category byte plus 80 string cells for levels **1–79 and 80+**. A folder containing only Growth.bin works too.

Search the sidebar by English/glossary name or raw GLID. Select a table, then choose a **Category row** from the dropdown. The level list displays the stored raw value beside its English preview. Select a level to edit it in the compact form below. **Show empty levels** can hide blank cells; the selected level remains visible while editing. The editor shows stored entries, without filling blank cells or simulating runtime progression.

### Category meanings and bare names

The schema names the category byte but does not document its enum. The supplied data supports the following observations; these are not claims about the complete runtime behavior:

| Category | Observed values / chooser |
|---|---|
| 0 | Class names; chooser draws from existing JIDs and writes their **bare names** |
| 2 | Mount-related numeric strings in mount-named tables; preserved as raw text |
| 4–8 | Item names; chooser draws from existing IIDs and writes their **bare names** |
| 1, 3, 9 and other codes | Meanings unverified; observed raw values remain available |

For example, the stored class cell is `闘士`, **not** `JID_闘士`. The chooser searches English names and Japanese raw values and returns the bare value. English previews use the category's class/item namespace when an exact catalog match exists. Unmatched values use the offline glossary. Manual text is preserved exactly; entering an arbitrary new name does not create a class or item.

Each category row has its own editable code, constrained to 0–255. This first release does not guess the roles or priority of the separate item-category rows. A blank cell stays empty rather than becoming an assumed inherited value. The schema's last column is `80～`, displayed as **80+**; the editor does not create separate level-81-and-up columns.

### Editing and usage

- **Apply edits**, selecting another level/category/table, or switching modules commits valid form values to the in-memory project. Invalid input blocks navigation.
- **Copy row / Paste row** copies the category and all 80 level values into an existing row. It preserves the target's collection ID, row index and native header fields. The clipboard survives table changes, making it possible to copy one character's class-progression row to another.
- **Clear level** empties the selected cell. **Reset level** restores it from the original source. **Reset table** restores only the selected GLID, leaving other GLIDs and LID edits intact.
- **Used by** scans the current Person.bin progression reference (`0x128`), including unsaved character edits. Double-click or choose **Open selected entry** to navigate to a character. Scripts, difficulty adjustments and runtime selection rules are not evaluated, so this is not a complete gameplay usage map.

GLID IDs, ordering and category-row counts are fixed. This module does not create/rename tables or add/delete rows. Shared GLIDs affect every character referencing them. The supplied Dietrich GLID has one category row; Majide has nine, so copying a row intentionally does not replace an entire table or change its structure.

### Projects and export

LID and GLID are **two views of one Growth.bin document**. Both sets of edits, including added LID rows, save in one source-fingerprinted project entry and build into **one** Growth.bin export, alongside Person.bin and Job.bin when loaded. Experience, automatic skill experience, class-selection rules and grant tables are editable through **Progression & Difficulty**, sharing the same Growth owner. Growth_P0.bin remains a separate source owned by that module.

Older character/class projects and **0.5/0.5.1 learning projects** remain loadable. Loading any project replaces current workspace edits, including edits from modules absent from the loaded project. Version 0.6 writes the new combined `fw-growth-edits-v1` entry for Growth.bin; older editor versions cannot read that entry. Use 0.6 or newer for projects saved with this module. **Open last project** restores the GLID module too.

Validation covers all **152,200 LID+GLID field values** after joint edits, unchanged identifiers/counts/native headers, unrelated bytes and pointer targets, string sharing, Unicode, the 80+ column, empty cells, old projects and rollback on invalid projects. The actual GUI regression also exercises English choosers, row copy/paste, combined export and reopening. Exports still need an **in-game test**; structural preservation cannot prove the meaning or gameplay validity of every edited value.

## SID skill editor and usage browser — new in 0.7

Choose **Module → Skills**. The **Source** selector switches between the loaded **Skill.bin**, **Skill_P0.bin** and **Skill_P1.bin**. Their records remain separate, including duplicate SIDs; no runtime overlay order is assumed. The heading identifies the selected file and notes when a SID is also defined in another loaded file.

The supplied 1.00 files contain **2,854 + 28 + 3 = 2,885 records**, representing **2,876 distinct SIDs**. Every record has **157 editable fields**. SIDs and record ordering remain fixed; this release does not create, delete or rename skills. A folder containing only a supported Skill file works, including a standalone side file. **English names…** accepts a folder containing only Skill messages as well as the full USen folder.

Search by English/glossary name or raw SID within the selected source. **Copy SID** copies the exact selected identifier, including brackets, fullwidth plus signs and reserved-name characters.

| Tab | Contents |
|---|---|
| Overview | Name/description/message keys, text arguments, variables, command/warning/notification references and selection/learning/equip/timing codes |
| Effects | Effect code and numeric value list, costs, range, count, experience, period list, duration/change values and attack/action parameters |
| Conditions | Two distinct required/blocking skill-group pairs, enhancement-invalidation reference, flags, targets/comparisons and continuation/placement conditions |
| Stats | Signed 16-bit combat block and float combat block; four raw stat blocks with their original offsets and data types |
| Links | Co-learned/granted-effect/resistance/burst/upgrade skills, equipment, transformation, range, placement, summon and material references |
| Presentation | Effects, motion, voice, sound, icons and used/consumed flags |
| Used by | Current structured field references, with source, owner name, field/offset and list/group location; navigate to editable owners |
| File references | Original string-pool occurrences plus indexing coverage/errors; this includes definitions and is not a confirmed-usage list |

### Field editing

All references retain their raw IDs beside live English/game-text or approximate glossary previews. The `…`/`+` choosers search observed values and the appropriate available SID/IID/JID/PID/message/range catalog where supported. Unknown IDs can be typed manually. This editor changes message **keys**, without rewriting the message tables themselves.

Grouped `data[,]` skill references have a **16-byte leaf entry**, unlike the class condition lists' 8-byte string entries. The editor writes the correct layout and clears new reference-cache slots. The main form uses one JSON list of raw SIDs per line; the group editor preserves the grouping and live previews. Exact boolean semantics and the roles of the two required/blocking pairs are not yet verified.

**Effect values** (`s16[]`, range −32768…32767) and **Period values** (`u8[]`, range 0…255) use a JSON integer list, for example `[1, 2, 3]`. Blank text or `[]` clears the list. List lengths can change; replacing a list allocates separate data so other records sharing the original array remain unaffected.

Float fields accept finite decimal numbers and store IEEE 754 **32-bit floats**. The UI shows a short decimal that roundtrips to the same stored value, avoiding long binary-rounding artifacts. Their scaling, stacking and unit meanings are not verified; they are not presented as percentage bonuses. Raw enum codes/bitmasks remain numeric, with their original names/types/offsets available for inspection.

Apply or navigate to commit valid form edits. Invalid input blocks navigation, including source-file changes. **Reset entry** restores only the selected skill in the selected source file. Edits in the other files/modules remain intact.

### What “Used by” means

This tab scans the **current in-memory** Person.bin, Job.bin, LID entries and all loaded primary Skill files, including unsaved edits. It also includes live primary Item.bin/Item_P0.bin/Item_P1.bin references when those files are loaded, plus **read-only** auxiliary Skill groups. In 0.8, item skill links update from unsaved item edits and navigate to the item editor; the original item snapshots are excluded from the live list to prevent duplicate/stale references.

References include assignments, prerequisites, exclusions, co-learned skills and granted-effect links. The field and nested-list location distinguish them. A listed reference does **not** mean the owner equips or activates the skill, and counts are field occurrences rather than unique characters. The browser does not recursively resolve granted-skill chains or evaluate conditions, load order, scripts or runtime inheritance.

Double-click a reference or choose **Open selected entry** to navigate to its character, class, skill/item (in its own source file), or exact learning-table row. Auxiliary rows remain read-only. **Refresh references** reapplies valid form edits and rescans. Owner names reflect current editable name keys when translated text is available.

**File references** retains original on-disk string matches across readable GameData files. These are counted per source/string target and may include the SID's own definition. They remain original evidence after unsaved edits; they are deliberately separate from current structured references. Coverage lists indexed files, scanned read-only link groups and parse issues. Compressed scripts and other unsupported formats are not decoded.

### Projects and export

All loaded editable files save in one suite project, with a separate source fingerprint and filename for each Skill document. All loaded editable files export together, even when another module is visible. Duplicate SIDs in different files can hold different edits. **Open last project** restores the Skills module and selected source file as well as the saved paths.

Older character, class, LID and GLID projects remain loadable; replacing the workspace clears edits in Skill files absent from an older project. Projects containing the new `fw-skill-edits-v1` entries require **0.7**. Skill IDs/counts/native headers, untouched records and auxiliary groups are preserved. Original sources are never overwritten; unrelated output files are refused.

Validation includes all **452,945 skill-field values** after mixed edits across the three files, opaque bytes and pointer targets, shared arrays, empty/nested groups, finite float bounds and decimal roundtrips, reopening/re-exporting, file-specific project rollback and joint exports. The actual Tk check exercises all field widgets, English choices/previews, invalid-input blocking, side-file separation, current-owner and LID navigation, reset, clipboard and reopening. Edited skills still need an **in-game test**.

## IID/item editor — new in 0.8

Choose **Module → Items**. The **Source** selector switches between **Item.bin**, **Item_P0.bin** and **Item_P1.bin**, with **1,356 + 16 + 16 = 1,388 distinct item records** in the supplied 1.00 files. All **80 primary fields per record** are editable. Original IIDs and their record indexes remain fixed. New items can be created or duplicated in 0.19; original items cannot be deleted or renamed. A standalone folder/file containing only one of these item tables works too.

Search by English/glossary name or raw IID within the selected source. Load **USen** via **English names…** if needed; a folder containing only Item message files is accepted. **Copy IID** copies the exact ID, including special suffixes.

Some prototype IDs in Item_P1.bin end with **literal pipe characters**: `IID_試作品１号`, `IID_試作品１号|`, `IID_試作品１号||` and `IID_試作品１号|||` identify different slots. Search, copy, project/export and reference matching preserve those characters. The editor does not split them as logical operators or merge a longer ID with its prefix.

| Tab | Contents |
|---|---|
| Overview | Name/description keys, text arguments, type/use/target codes, buy/sell prices, value/experience/category/rarity codes |
| Stats & use | Durability, power, weight, contamination/support, ranges, material/taste/grade and recovery values; eight raw weapon values, combat modifiers and eleven signed stat modifiers |
| Skills | Separate equipped, held, use, granted, removed, required and forbidden SID references |
| Crafting | Repair material/count/cost, forge target/material/count/cost, condition, flags, conversion target/count, lottery group and classification links |
| Presentation | Activation/launch/impact/hit effects, asset flag and icon identifier |
| Used by | Current references from loaded editable tables, observed GLID item-name cells and read-only shop/lottery entries |
| File references | Original IID string-pool occurrences and source/collection coverage, separate from current unsaved references |

### Creating items — experimental in 0.19

1. Select **Module → Items**, choose the destination **Source**, and open **Overview**. **New item…** appends a blank item; **Duplicate item…** appends an independent copy of all **80 current field values**, including valid pending edits. Items are created in the selected file, not automatically merged across files.
2. Give the new definition an unused **`IID_`** ID. Unicode and literal pipe suffixes are supported. Empty names, whitespace, nulls, quotes, `, ; ! &` and the reserved `::` separator are rejected. Creation and project/export validation reject new IDs that collide with another loaded item file. Unloaded files/mods cannot be checked.
3. Configure a blank item before using it. Numeric fields start at zero, text/references start empty, and arrays start empty. Duplication is a useful starting point for retaining an existing item's type, presentation and behavior. Reference fields retain their copied values; source/self references are not automatically rewritten to the new IID.
4. Name/help fields remain **message keys**. Choose an existing key from your Item messages to reuse its in-game text. English previews for new IIDs follow their current name key. Creating arbitrary new localization text, icons, models or effects is not included; references can reuse existing resources.
5. Assign the IID through character inventories, shops/lotteries, class equipment, skill effects, facilities/rewards, profiles/recruitment, deployment, legions or automatic item grants. Their supported choosers include new IIDs immediately. GLID item categories offer the corresponding **bare names**. Creating an item alone does not place it in the game. Shop-row price and the primary item's price remain separate values.
6. **Used by** finds current references and links to their source. **Remove new item** is disabled for original items and blocked while other loaded data references the new IID, including observed bare GLID item-name cells. A self-reference inside the item being removed does not block removal. Scripts/unloaded data and runtime rules are not evaluated. **Reset entry** keeps the new IID and restores its creation-time blank/copy values.
7. **Save project…**, **Open last project** and **Export mod…** retain new definitions, regular edits and shop/lottery changes together. Projects with new items use **`fw-item-edits-v3`**, tied to the original source filename/SHA, and require **0.19 or newer**. Without definitions the existing v1/v2 formats remain unchanged. Older project replacement clears omitted new items, and invalid/colliding projects roll back all loaded files.

The writer appends primary records in their group, adds indexed labels and UTF-8 IDs, and rebases every registered pointer location/target, schema pointer and label offset. Original IIDs/indexes/header tags and opaque auxiliary bytes stay intact. Copied arrays use the existing copy-on-write serializer. Each source remains a separate exported file. Source protection, ownership checks and backups remain in place.

**Item creation is experimental until tested in-game.** New records receive unused header tags, but the extra header word's runtime meaning, item-capacity limits, side-file load priority and save behavior remain unverified. Start with one duplicate of a known working item, change a small value, place it in a separate test mod, and retain source/save backups. Format validation does not establish valid item/skill/resource combinations.

### Editing values and links

Raw Japanese IDs remain editable beside live English/game-text or approximate glossary previews. Reference choosers search existing IDs by English name or raw text. Skill lists offer SIDs; repair/forge/conversion links offer IIDs; asset flags offer known AIDs. Lottery/classification links offer observed raw values across loaded item files rather than guessing a new ID prefix. Name/description fields edit message **keys**, without modifying message text.

Fields retain their declared binary types: buy/sell prices and flags are **unsigned 32-bit** values; the schema's `int` repair/forge counts and costs are **signed 32-bit**, including negative values; stat modifiers are signed 16-bit and most other codes are unsigned 8-bit. The UI validates those bounds. Raw weapon, category, use and flag meanings are not yet fully verified, so no speculative enum names or percentage units are applied.

Selecting another record/source/module or choosing **Apply edits** commits valid form changes to memory. Invalid inputs block the switch and keep the current source selected. **Reset entry** restores only this item in this source. Other items/files/modules retain their edits. Changed skill/argument/classification lists use separate array allocations, leaving shared original lists intact.

### References and navigation

**Used by** reads the current in-memory Person.bin, Job.bin, LID entries, Skill files and Item files, including unsaved edits. Examples include inventories/drops, class equipment/promotion items, skill equipment/materials, repair materials and forge/conversion targets. The field, offset and list position distinguish these relationships. Counts are reference occurrences rather than unique owners or proof that an item is equipped.

GLID categories **4–8** contain observed bare item names. The browser matches those exact names to the selected IID and shows the category and stored level, including **80+**. Double-clicking navigates to that exact progression table, category row and level. It does not fill blank cells, simulate inheritance, or treat other category codes as item references.

The main Item.bin also contains **114 shop collections / 1,152 rows** and **136 lottery collections / 785 rows**. In 0.13 these are editable through **Shop & Loot**, sharing the same Item.bin document. Used by scans their current item/exchange references, replacing the static snapshot when loaded, and opens the exact collection and entry. Changing a primary item price still does not automatically rewrite a stored shop-row price; edit each field explicitly.

Double-click or **Open selected entry** navigates to an editable character, class, source-specific skill/item, LID row or GLID cell. Loaded shop/lottery references open their editable entries. **Refresh references** applies valid form changes and rescans. Skill **Used by** now also reflects current item skill links and can navigate back to the item editor; loaded item rows replace the original static snapshots in that list.

**File references** retains original on-disk string occurrences across readable GameData files, including definitions. Those are file evidence, not confirmed assignments, and do not change with unsaved edits. Bare GLID names are resolved in Used by rather than presented as prefixed-IID string matches. Scripts, runtime flags, load order and indirect ownership through skill/grant chains are not evaluated.

### Saving, exporting and compatibility

Character, class, LID/GLID, skill and item edits save in one suite project, with a separate source fingerprint and filename for each primary binary. The full current dataset exports **191 files** (20 root files and 171 Dispos files). New item records do not create additional binary files. The source selector never merges files or assumes overlay priority. Growth.bin remains one shared LID/GLID document.

**Open last project** restores the Items module and saved source file along with the remembered game/message/project paths. Earlier projects remain loadable; replacing the workspace clears item edits absent from an older project. New `fw-item-edits-v1` entries require **0.8**. All original source protections, unrelated-output guards and dated export backups remain in place.

Validation covers all **111,040 item-field values** after mixed edits across three files, original IDs/counts/header metadata, untouched pointer targets and auxiliary bytes, signed/unsigned bounds, shared-array isolation, Unicode/pipe IDs, reopen/re-edit/export, project rollback and nine-file export/backups. The actual GUI test exercises all 80 widgets, English choosers/previews, side-file isolation, live item/SID/character/GLID navigation, reset, clipboard and reopening. Edited mods still require an **in-game test**; structural checks do not establish gameplay validity.

## Supports & Recruitment — new in 0.9

Open the original **Reliance.bin** with GameData, then choose **Module → Supports & Recruitment**. The **Section** selector exposes all seven supported Reliance sections. This is one shared editable document: changing sections never creates competing Reliance.bin exports.

| Section | Supplied rows | Editable contents |
|---|---:|---|
| Compatibility | 73 rows × 73 columns | Directed compatibility-code matrix, indexed by the original RID order |
| Pair bonuses | 314 | Character-pair references, nine signed combat modifiers and initial-level code |
| Support conditions | 515 | Partner references, rank/route/part/chapter codes, joined-character references, flags, support addition, dates/default codes and linked flag |
| Recruitment | 214 | Route, support/renown requirements, attribute bitmask, required/completion flags, type/difficulty codes, item/count, arguments and hint fields |
| Assist rates | 8 | Fixed-length stored rate vectors for successive occurrences |
| Linked voices | 165 | Speaker/target references, voice labels, alternate label and switch flags |
| Tobias items | 3 | Favorite, normal and disliked recruitment-item lists |

There are **1,292 fixed records and 20,033 stored fields** across these sections. Native names, IDs, row order and record counts stay fixed. Some names are empty and some support-conversation names are duplicated; every original row remains available by its own row number. This release does not add/delete rows or create new support events or recruitment entries.

### Compatibility matrix

Choose a row character in the sidebar, then a **column character** in the matrix-row tab. Edit the selected cell's raw code and choose Apply or navigate to commit it. **Reset cell** restores that one value. **Reset row** restores the selected matrix row while retaining edits elsewhere.

The source matrix is **asymmetric**: editing A→B does not edit B→A. Reverse cells must be selected separately. The stored values observed in the supplied file are 0–4, but their complete gameplay meaning is not verified, so the UI calls them **compatibility codes**, without labelling them as support ranks. Binary bounds are 0–255. All 73 row/column RIDs and vector lengths stay fixed; the editor does not reorder or resize the matrix.

**Connected characters** lists current Person.bin owners whose support-reference field (`0x108`) points to that RID, including unsaved character edits. Select an owner and open it in the character editor. Character names use current translated name keys when available.

### Pair bonuses and support conditions

Pair rows expose both PID references, the original signed 16-bit combat-modifier block, and the unsigned initial-level code. Support-condition rows expose every field from the source, including conditional joined-character references and flags. English-searchable PID choosers and live previews work beside the raw identifiers.

Repeated part/chapter fields are labelled **A/B** rather than asserting unverified lower/upper-bound semantics. Route/rank/default codes remain numeric. Editing the partner or rank fields does not rename the native conversation key, rewrite dialogue/scripts, or generate the matching content for a new pair. Duplicate native conversation names are preserved as distinct rows.

### Recruitment

Some scouting rows carry a native PID name and following rows have an empty native name. The sidebar shows the **previous named PID as a section hint**, plus the row's stored route code, so those route variants can be found by English character name. The native empty names remain empty. This grouping is a display aid; the editor does not insert PID fields or assume it has evaluated the recruitment engine.

You can edit the existing support/renown requirements, flags, item/count, negotiation/type/attribute codes, arguments and hint fields. Requirements retain their declared ranges, including unsigned 16-bit renown/item count and unsigned 8-bit codes. Item choosers include every loaded IID, preserving literal pipe suffixes.

Changing these requirements does not guarantee recruitment becomes available: route state, flags and other game logic are not evaluated. No automatic recruitment-unlock patch is generated. **Connected characters** identifies the section-anchor link explicitly as a hint and can open that character when Person.bin is loaded.

### Assist rates, linked voices and Tobias items

Assist-rate vectors use JSON integer lists. Their original lengths are fixed (five positions in the supplied file); position-to-rank mapping and percentage semantics are unverified. Values retain their unsigned-byte range.

Linked voices expose existing labels and switch flags; the editor does not modify or preview audio assets. Tobias's three named categories keep their identities while their IID lists can change length. No item-type validation is claimed for manually selected recruitment items.

### Workflow, links and project compatibility

The sidebar searches English names, raw native names/IDs, section hints and textual references within the chosen section. Lists retain their original order and show a stable row number. Selecting a row/section/module applies valid form edits; invalid values block navigation. **Reset row** restores only the selected record and preserves other sections' changes.

All seven sections save together in one **`fw-reliance-edits-v1`** entry, tied to the original Reliance.bin SHA-256. A complete dataset in 0.16 exports **191 files (20 primary files plus 171 deployment files)**, including one Reliance.bin, with existing source protections, unrelated-output guards and dated backups. Earlier projects still load; replacing the workspace clears Reliance edits if the older project has no Reliance entry. Projects containing the new entry require **0.9**.

**Open last project** remembers this module and its selected section. A standalone Reliance.bin file/folder also works. Loading Person.bin and USen provides the best English character names and owner navigation; without Person data, raw IDs/glossary explanations remain available.

SID/IID usage browsers now scan all seven live sections. For example, a required item assigned to an unnamed scouting row appears in the item's Used by list, and opening that reference selects the exact scouting row/section. Original file-string evidence remains separate. Job.bin's auxiliary support-effect templates are preserved and remain outside this module.

Validation compares all **20,033 field values**, including all **5,329 matrix cells**, after mixed edits across every section. It checks directional isolation, original native headers/names/counts/labels, untouched bytes/pointer targets, shared-list isolation, fixed vector lengths, numeric bounds, project rollback and repeated export. The actual Tk check covers all seven sections, input blocking, English choosers/previews, linked owners, exact item-to-scout navigation, reset, combined export, standalone loading and saved-section reopening. Edited exports still need an **in-game test**.

## Appearance-rule editor — new in 0.10

Choose **Module → Appearance rules**. **Source** keeps `AssetTable.bin`, `AssetTable_P0.bin` and `AssetTable_P1.bin` separate; no runtime override order is assumed. **Section** selects the sections actually present in that file. The supplied 1.00 data contains **7,328 rows / 315,123 editable field values** across the three files.

| Section | Main-file rows | Contents |
|---|---:|---|
| Appearance rules | 6,184 | 49 fields: grouped conditions, body/head/hair/mount models, equipment, animations, accessories, effects, materials, scale, raw colors, voice/portrait link and keywords |
| Asset information | 307 | Model/effect/bone references and effect size; multiline assignments remain single strings |
| Variations | 20 | Ten reference lists per row |
| Voice / portrait | 612 | Voice and portrait IDs, positioning floats and presentation flags |
| Condition sets | 182 | Grouped conditions and additional flags |

The supplied side files contain **13 and 10 appearance rules**, respectively. They have no other sections. Native row order, labels (including blanks and duplicates), IDs and counts stay fixed. This editor does not create/delete/reorder rows or rename native IDs.

Search by English/glossary name, native label or textual reference. Unnamed rules use an observed positive AID as a display hint where available; the row number remains visible. This does not infer which conditional outfit will win at runtime. Load USen for the best available character-name previews.

The rule form has **Conditions**, **Models & links** and **Scale & colors** tabs. Raw references remain editable beside English/glossary previews and searchable choosers. Conditions retain their nested groups; their AND/OR semantics and precedence are not simulated. Numeric codes retain their source types and bounds. Scale and coordinate fields store finite float32 values. Colors accept **eight hexadecimal digits**, optionally prefixed with `#`, in their original four-byte disk order. Channel order and alpha semantics have not been verified, so the editor does not label them RGBA or offer a misleading color swatch.

Some asset-information effect/bone assignments contain multiple lines. Their controls preserve a **single string**, including line endings and a trailing newline; they do not split it into an array. Other reference lists retain their original list structure.

**Copy settings / Paste settings** transfers values into an existing row, including across source files within the same section:

- For appearance rules, it copies the 48 presentation fields while **preserving the destination's conditions, native ID and position**.
- For voice/portrait rows, it copies all 11 editable fields while preserving the destination's native FID.
- It does not copy settings between unlike sections or automatically swap both characters. Copy each direction separately if that is your intended edit, keeping the original values available before overwriting either side.

**Open linked voice / portrait** opens the matching FID row, preferring the same source file. The rule stores a **bare name** in the supplied schema (for example `マジーデ` rather than `FID_マジーデ`); the chooser and English preview retain that stored format. Editing these references does not modify models, textures, portrait images or audio files. There is no asset preview.

The **AIDs** browser now reads current appearance values, including unsaved edits. In **Rules & flags** or **Linked data**, select a row and use **Edit selected row**, double-click or press Enter to open its exact file/section/row. Current item asset flags also appear as direct owners, with navigation to their correct main/side source file. Original string-pool evidence stays separate.

**Apply edits** and navigation commit valid form values; invalid input blocks a source/module change. **Reset row** restores only that row. **Save project…** includes all sections in one `fw-appearance-edits-v1` entry per source file, tied to its original SHA-256. **Export mod…** writes all loaded editable binaries; a full dataset in 0.16 has **191 files**, including 171 under `Dispos/`. Appearance-only folders and direct supported AssetTable file paths work too. Old projects remain loadable and clear appearance edits when replacing the workspace. Projects containing appearance entries need **0.10 or newer**. **Open last project** restores the selected source and section.

Validation checks every stored appearance value after mixed edits, exact color/float bytes, original labels/native headers/counts, untouched bytes/pointer targets, Unicode, shared-list isolation, scalar multiline preservation, project rollback and exports. The actual GUI check covers all five sections, settings copy, linked navigation, live browser updates, source switching, invalid input, combined-file export and remembered reopening. Edited mods still require an **in-game test**; structural checks do not establish runtime rule semantics.

## Profiles & Affiliations — new in 0.11

Choose **Module → Profiles & Affiliations** with the original **Profile.bin** loaded. This module exposes all **five sections**, sharing one project entry and one exported file. The supplied 1.00 data contains **915 native rows / 18,445 stored field values**.

| Section | Rows | Fields per row | Contents |
|---|---:|---:|---|
| Profiles | 313 | 46 | Activation/group references, date/height, biography and introduction keys, history, preferences, gifts, social/activity ratings and senior targets |
| Affiliations | 97 | 5 | Clan-name message key, route code, icon, grouped transition conditions and next affiliation |
| Conversation expressions | 325 | 6 | 3D/2D expression, motion, mouth-state/shape codes and sweat bitmask |
| Conversation restrictions | 1 | 1 | Condition list for an existing native conversation key |
| Roster order | 179 | 9 | Signed 16-bit display-order values for each language |

Use **Section** to switch layouts and search by English/glossary name, native ID or textual reference. Native PRFs, BIDs, conversation/expression names, roster keys, row counts and order stay fixed. This release edits existing records; it does not create/delete/rename them or change character slots.

### Profile fields and readable text

Profiles use **Bio & history**, **Preferences**, **Social & activities** and **Connected entries** tabs. Raw references remain editable beside English previews and searchable choosers. The suite now also loads **Clan.msbt**, **Roster.msbt**, **ScoutInfo.msbt** and **System_Facility.msbt**, including their `.zst` variants, from your own language folder. This reveals biography, hobby/likes/dislikes, scouting/travel introductions and clan text. For example, Dietrich's title key previews as **Foreign Swordsman**. Best character-name previews use the full GameData folder containing Person.bin plus USen.

The fields edit **message keys**, not the localized message text. Selecting another existing biography key reuses its text; it does not write a translation or create a new message. Unknown IDs still use the offline glossary or remain raw. Profile group, facility conversation code and senior-target references remain explicit editable links; they are not automatically synchronized with PIDs, assets or route events.

History is stored in **two parallel arrays**: signed 16-bit years and biography-message keys. Edit years as a JSON integer list and message keys one per line. Their lengths must match before applying/navigating/exporting; every supplied profile has matching lengths. Both empty arrays are allowed. Source record headers and other profiles sharing old arrays remain unchanged. Date fields retain unsigned year/month/day types and zero/sentinel values; the editor does not calculate age or infer a calendar.

Food-taste, emotion, activity and speech bytes remain **raw ratings**, without guessed like/neutral/dislike enum mappings. The theater field is a raw unsigned-byte vector; its index meanings are unverified. Liked/disliked dishes and categories retain their stored names. Gift item lists use IIDs with English item previews and choosers. **Items → Used by** now includes current profile gift references and opens the exact profile row, including unsaved edits.

The profile schema itself cautions that activation conditions are generally irreversible and should not use toggled flags or combined part/chapter thresholds. That note is shown in the form; the editor does not execute or simulate those conditions.

### Affiliations and connected entries

Affiliations expose all five fields. Clan keys preview using the supplied English clan table; the route stays a numeric code. Transition conditions retain their nested groups, and **Next affiliation** chooses an existing BID or accepts a manually entered reference. Changing these fields does not rewrite scripts or determine which conditional affiliation is active.

**Connected entries** shows current direct Person.bin profile/affiliation assignments, profile-group/senior links and incoming/outgoing affiliation transitions. It includes unsaved edits. Double-click, press Enter or use **Open selected entry** to navigate. **Refresh links** reapplies valid form edits and rebuilds the list. Native transition cycles remain representable; the browser does not traverse them recursively, simulate priority, or claim that every listed character currently belongs to the affiliation. Roster-order entries can navigate to matching current character name keys too.

Conversation expression/restriction fields preserve the native named keys without generating or editing dialogue, audio, face assets or scripts. Roster-order values are editable by locale, but records are not physically reordered. Negative/sentinel order meanings remain unverified.

### Projects, exports and validation

Apply/navigation commits valid changes. Invalid numbers, malformed lists or unpaired histories block navigation and leave in-memory edits unchanged. **Reset row** restores only the current row, keeping other Profile sections and modules. **Save project…** stores all five sections together in one source-fingerprinted **`fw-profile-edits-v1`** entry. **Export mod…** writes **one Profile.bin**, alongside all other loaded tables: **18 files** with the full supplied dataset. Existing source/output protections and dated backups apply.

Old projects remain supported and clear Profile edits when replacing the workspace if they have no Profile entry. New Profile entries require **0.11 or newer**. **Open last project** restores the module and section. Standalone Profile.bin folders/direct file paths work too. Windows and Linux expose the same fields and project format.

Tests compare all **18,445 stored values** after mixed edits across every section, preserving native labels/headers/counts, unrelated bytes/pointer targets and shared arrays. They cover paired-history validation, numeric bounds, old projects, transactional rollback, export guards and live references. The GUI regression covers English biography/clan previews and choosers, all five sections, invalid-input blocking, direct-link navigation, gift-to-profile navigation, combined export/reset, source preservation, standalone loading and saved-section reopening. Edited mods still need an **in-game test**.

## Facilities & Rewards — new in 0.12

Choose **Module → Facilities & Rewards**. **Source** selects `Facility.bin`, `Reward.bin`, `Reward_P0.bin` or `Reward_P1.bin`; main and side records remain separate, including repeated names. **Section** selects the sections actually present in the chosen file. Together the supplied 1.00 files contain **1,053 editable rows / 8,512 stored field values**.

### Facility gameplay sections

Facility.bin contains **493 rows / 3,832 fields** across all twenty sections:

| Section | Rows | Editable contents |
|---|---:|---|
| Cooking | 12 | Name/help keys, schedule bitmask, renown requirement, price, material/taste codes and model reference |
| Training | 10 | Conditions, schedule/cost, raw aptitude values, two weapon references and their class lists |
| Theater rewards | 8 | Money, renown, support value, item-lottery reference and raw float chance |
| Baths | 16 | Name/help, renown/flags/cost, normal/special bitmasks, learned skills, weights and map |
| Temples | 12 | Icon conditions, service/blessing/character links, paired location/spot/argument fields and battle/reward references |
| EX spots | 6 | Spot, bare skill name, warp destination and past-memory vector |
| Spectating | 12 | Name/detail/event references, route/activation conditions, date and raw reception times |
| Inns | 5 | Feature bitmask |
| Individual actions | 4 | Experience/money/material values and raw display codes |
| Perch answers | 23 | Answer-group code |
| Perch questions | 68 | Character, conditions and ten bare answer references |
| Divination | 64 | Conversation reference and stored value |
| Lessons | 9 | Name/content, type, teacher, renown, conversation/battlefield/subquest and item/class rewards |
| Challenges | 9 | Subquest, battlefield and conversation number |
| Opening hours | 21 | Facility definition, conditions and four time-band codes, in **20 native groups** |
| Facility statuses | 51 | Status names, in **8 native groups** |
| Reward multipliers | 3 | Five condition/renown/multiplier blocks per row |
| Facility banter | 158 | Facility code, character/conversation pairs, flags and raw support codes |
| Facility event triggers | 1 | Label/facility, part/chapter A/B, route and flags |
| Facility guidance | 1 | Existing conversation label |

**Opening hours** and **Facility statuses** are collections with separate group headers and leaf records. The **Group** dropdown uses English captions for the known facility groups and filters their native rows; it does not move or combine rows. Empty groups, original counts and native leaf ordinals are preserved. The heading identifies the source, section, row and group. Repeated fields in training, temples, multipliers and event triggers receive A/B or numbered labels without inferring priority or range semantics.

Bath skill references and their unsigned-byte weight list must have equal lengths; all supplied bath rows follow this layout. Edit both before applying if resizing. Weights are not labelled as percentages. Other flags/enums, raw multiplier units, chance scales, times and memory-vector indexes retain their stored types. Float chance values must be finite. The editor does not infer an engine formula from a field name.

EX-spot skill references store a **bare name**, not `SID_...`; perch answer references similarly omit `PCHA_`. Their choosers preserve those formats and reference navigation resolves the corresponding loaded entry. Editing a model/map/scene/dialogue reference does not rewrite its referenced assets or scripts.

### Reward sources

Reward.bin contains **553 rows / 4,589 fields**, across four sections:

| Section | Rows | Editable contents |
|---|---:|---|
| Achievements | 418 | Entry key, type/counter/aggregation codes, signed 32-bit required value, causality points and completion/display conditions |
| Causality rewards | 81 | Entry/reward/help keys, effect/operation/value/clear-count codes and point cost |
| Notifications & rewards | 33 | Condition bitmask, flags, type/message/arguments/icon/tutorial/sound, target and skill-code/experience vectors, item rewards and flag |
| Renown | 21 | Level, required part/experience, completion conditions/flags, icons/messages and item rewards |

Reward_P0.bin adds **3 notification rows**, and Reward_P1.bin adds **4**. These 91 side-file field values stay in their own source files. Names may be blank or repeated; stable row indexes distinguish them. No runtime override order is assumed. Skill-code vectors in notifications remain numeric bytes; they are not interpreted as SID strings.

### English previews and connected entries

The English loader now also reads **System_Notice, System_Hub, System_Gmap, System_Dungeon, System, BattleTitle, Spot and Divination** message tables, including `.msbt.zst` and `.msbt`, alongside the existing tables. The full supplied language folder provides **10,355 distinct English keys**, with no conflicting values across the supported files. Existing biography/clan text remains available. Message-key editing reuses those messages; it does not modify localization files. Conversation references with control/placeholder content may still show tags rather than full prose.

Facility name/help keys show English text in the list and form. Loaded recipe names also resolve current Profile liked/disliked-dish references to English. **Connected entries** resolves outgoing exact references to loaded editable characters/classes/skills/items/facility rows and other supported records. Incoming links scan current facility/reward/profile fields, including unsaved edits. Recipe links can therefore open the profiles that directly list the dish. **Skills/Items → Used by** also include current facility/reward references and navigate back to the precise file and row.

Use **Refresh links**, double-click/Enter or **Open selected entry** to navigate. Each link retains its source file. The list shows direct stored references, without traversing scripts, evaluating conditions or claiming complete runtime ownership. Scene choreography, cameras, placements and assets in **FacilityScene.bin** stay unchanged and are not exported by this module. The auxiliary shop/loot collections are editable in the separate **Shop & Loot** module, sharing Item.bin.

### Projects, exports and checks

Native names/IDs, record order and counts stay fixed; rows and groups cannot be added, deleted or renamed. **Apply edits** and navigation commit valid forms. Invalid input blocks navigation and restores source/section/group controls. **Reset row** restores only the current row. Source/section selections are remembered by **Open last project**; the group filter starts at All groups on reopening. Standalone Facility or Reward files, including side files, work too.

All sections in each binary share one **`fw-facility-edits-v1`** project entry with its own source filename and SHA-256. Earlier projects remain loadable and clear omitted facility/reward edits when replacing the workspace. New entries need **0.12 or newer**. Exports preserve other sections, group headers and shared data; the full supplied dataset now exports **18 files**. Source-file guards, unrelated-output protection and dated backups still apply.

Tests compare **all 8,512 field values** after mixed edits across all four files, including native collection headers/counts, opaque bytes, pointer targets, shared-list isolation, exact numeric/float bytes, empty groups, paired weights, transactional projects and export guards. The actual GUI check exercises all sections/sources, grouped filters, English previews/choosers, raw bounds, source restoration, SID/IID/profile/class links, eighteen-file export, reset/reload and standalone side-file opening. No edited mod has been tested in-game.

## Shop & Loot — new in 0.13

Choose **Module → Shop & Loot**. This module edits the existing auxiliary data inside **Item.bin**, rather than creating another binary or a second Item.bin document. **Source** lists loaded item files containing supported auxiliary tables; in the supplied 1.00 data only Item.bin has them. Item_P0.bin and Item_P1.bin retain their primary item editors and are not assigned invented shop/loot sections.

| Section | Collections | Entries | Fields per entry |
|---|---:|---:|---:|
| Shops | 114 | 1,152 | 9 |
| Loot lotteries | 136 | 785 | 3 |
| Value tiers | One display group | 11 native rows | 2 |

The new views expose **12,745 auxiliary field values**. Together with all three primary Item tables, the item regressions cover **123,785 values**. The full suite still exports **18 files**, because the existing Item.bin now includes both sets of edits.

### Browsing and editing

The sidebar selects a native shop/lottery collection and displays its entry count. Search matches collection labels, stored references and available English item names, including current edits. Native order is retained. English item names are shown in the entry grid beside the raw IID; readable shop captions supplement the native collection name in the heading. Some internal labels still require the offline glossary. Value tiers use one display group without creating a new native header.

Select an entry in the upper grid to edit its fields below. The vertical divider and scrollable form keep the controls compact. **Apply edits**, selecting another entry/collection or switching modules commits valid values. Invalid numbers or unpaired exchange lists block navigation and preserve the selected entry/form.

Shop entries expose all nine stored fields:

- **Shop name message key**, reusing existing localized text; blank entries remain blank rather than being automatically filled.
- **Item** IID, with English preview and chooser.
- **Sale conditions**, one stored reference per line.
- **Exchange items** and **Exchange quantities**, as parallel IID and unsigned-byte arrays. Quantities use a JSON integer list. Their lengths must match; all supplied shop rows satisfy that invariant. Both can be empty.
- **Price** as unsigned 16-bit, **discount** as signed 8-bit, **stock** and **chapter restock** as unsigned bytes.

Values remain raw. The editor does not guess whether zero price means a base-price fallback, zero stock means unlimited, or a particular discount/restock code has special behavior. Shop-row price and the primary item's buy/sell fields are separate values; no implicit synchronization is applied.

Loot entries expose **item**, **unsigned 16-bit weight** and **conditions**. The footer shows the sum of stored weights for the selected table, without turning it into an asserted drop probability. It does not evaluate conditional eligibility, repeated draws, nested table rules or scripts. A zero weight stays zero.

Value-tier entries expose the two unsigned 16-bit **required causality** and **discard causality** values. Original tier labels/order stay fixed; no engine conversion formula or link to a particular primary item is inferred.

### Entry tools and links

**Copy entry / Paste values** transfers every field into an existing entry in the same section, including across collections. It preserves destination collection/entry headers, identifiers, order and counts. Paste across unlike sections is refused. This is a value copy, not automatic insertion or a two-way swap. Shop copies include the row's name key, exchange values and raw price/stock fields.

**Reset entry** restores only the selected row. The main **Reset table** button restores the selected collection, leaving other collections, loot/value rows, primary item edits and other files intact. Empty existing collections remain viewable; the editor cannot add/delete rows or collections or rename native IDs.

**Open item** navigates to the selected IID's loaded main/side item record, preferring the same source file where available. This also preserves literal pipe-suffix IDs such as `IID_試作品１号|||`. **Items → Used by** reads current shop and exchange references; changing an IID removes its old live reference and adds the new one. Opening a usage selects the exact collection and entry in **Shop & Loot**.

For lotteries, **Connected entries** shows current direct character random-drop, primary item lottery-group and facility lottery references. **Refresh links**, double-click/Enter and **Open selected entry** navigate to their editors. Facility lottery references also open the matching loot table in the other direction. The list does not resolve shop placement, unedited script/deployment references, indirect ownership or runtime conditions.

The English loader additionally reads **Shop.msbt(.zst)**. The supplied supported language tables now contain **10,616 distinct keys**, without conflicting values. Text controls edit message keys, not the message files themselves. Native references are never rewritten to English.

### One owner, project compatibility and export

Primary items and their auxiliary tables share **one Item document and one change set**. Editing either module includes both sets of changes in the next project/save/export. Export writes **one Item.bin**, preserving all native headers/counts, labels, unrelated bytes and shared data. Side item files remain separate. Existing source guards, unrelated-output protections and dated backups apply.

Primary-only item projects continue to use **`fw-item-edits-v1`**. When an auxiliary row is changed, that file's project entry uses **`fw-item-edits-v2`**, which needs **0.13 or newer**. Earlier projects remain loadable. Loading an old item entry replaces that file's edits and clears its current shop/loot/value changes; suite replacement also clears omitted files as before. Invalid projects roll back the entire change set. The filename and original binary SHA-256 remain mandatory.

**Open last project** restores the Shop & Loot module, source and section; collection/entry selection starts from its default on reopening. Standalone Item.bin input works. No game data is bundled.

Validation compares all **123,785 primary plus auxiliary values** after joint edits across the three item files, including original label/header metadata, the 250 native collection headers, unchanged pointer targets/opaque bytes, numeric limits, shared arrays, empty groups, exchange pairs, pipe IDs, v1/v2 migration, rollback and a single Item.bin export. The actual GUI check covers all three sections, English item choosers, copied/reset values, invalid input, exact usage navigation, side-item opening, facility links, combined export, remembered section and an empty existing collection. Edited mods still need an **in-game test**.

## Planned module order

The user requested one module at a time, starting the next only after **continue**:

1. Supports & Recruitment — included in 0.9.
2. Appearance-rule editing — included in 0.10.
3. Profiles and affiliations — included in 0.11.
4. Facilities and rewards — included in 0.12.
5. Shop and loot — included in 0.13.
6. Battle deployment — included in 0.14.
7. Legion — included in 0.15.
8. Expanded progression and difficulty — included in 0.16.
9. Terrain — next, awaiting continue.

## Battle deployment — new in 0.14

Choose **Battle deployment**, select a **Deployment file**, then choose a native
**group** in the left list. The unit list above the form shows character names,
levels, signed spawn/deployment X/Z positions and the stored army value. Search
finds native IDs, English character/item names, group labels and AI text in that
file. English previews update when a reference changes; the native value stays
editable. Group labels can also use your local glossary.

The supplied 1.00 data contains **171 `Dispos/*.bin` files**, **1,415 groups**,
**6,715 unit slots** and **282,030 editable field values**. All 42 fields per
slot are exposed in three compact tabs:

- **Unit & position:** character PID, army, normal flags, spawn X/Z, deployment
  X/Z, size, facing, advance value, level, legion-soldier reference, vehicle/mount
  reference and trust level.
- **Inventory:** five IID slots with their corresponding raw drop flags.
- **AI:** condition, action, attack and movement names/arguments; evaluation,
  priority, two recovery values, squad number, fierce-attack handling/arguments,
  forbidden-turn value, movement restriction and AI flags.

X/Z and the forbidden-turn value are signed bytes (-128..127); levels/army and
other byte fields are unsigned (0..255). Raw flags retain their full 16- or
32-bit range. Bit meanings, coordinate origin, sentinels, facing enumeration,
army meanings and AI script semantics are unverified. The editor does not infer
terrain bounds or evaluate AI/event scripts. Readable field translations describe
the stored names; they do not prove gameplay behavior.

**Copy unit / Paste values** copies all editable values into an existing slot,
including across deployment files. It preserves destination group names, slot
headers, ordinal, count and order. **Reset unit** restores that unit only;
**Reset table** restores the currently selected group only. Empty native groups
remain selectable. Adding/deleting/reordering units or renaming groups is not
supported. Changing a deployment PID changes this placement's character
reference, not the Person.bin identity or a complete character swap.

**Open character** opens the currently assigned loaded character. **Connected
entries** lists direct references from the current group and opens matching
loaded characters/items/skills. **Items → Used by** and **Skills → Used by** also
include current unsaved deployment references and navigate to the exact file,
group and unit slot. Missing references remain raw.

**Battlefield links** shows exact main/revealed deployment links from the 138
primary BattleField.bin records, including English battle titles and native
terrain/script references. Some deployment files have no direct link. Script-
selected placements and chapter ownership are not inferred. BattleField.bin,
map geometry, terrain, legion definitions and scripts are not edited or exported
by this module.

Project, manifest, glossary and remembered-path JSON is explicitly read as UTF-8 on both platforms, including Windows systems using a legacy default code page.

Each file has one **`fw-deployment-edits-v1`** project entry, guarded by its full
`Dispos/filename.bin` path and original SHA-256. Earlier suite projects remain
loadable; replacing the workspace clears edits omitted by an old project.
Projects containing deployment entries require **0.14 or newer**. **Open last
project** restores the chosen deployment file. A deployment-only GameData folder
and direct `Dispos/*.bin` selection are supported.

**Export mod…** preserves paths beneath `romfs/GameData/Dispos/`. A full supplied
dataset now exports **191 files**, with 20 primary files plus 171 deployment
files (Legion.bin was added in 0.15; Growth_P0.bin in 0.16). Original-source protection, unrelated-output checks, preflight builds and
dated backups still apply. All loaded editable binaries are exported, including
unchanged ones. Use a separate output folder, and test edited mods in-game.

Validation covers all supplied deployment values after representative joint
edits in every file, numeric byte encodings/bounds, empty groups, exact native
headers/counts/labels, unrelated bytes and pointer targets, current IID/SID
references, nested-path exports, source fingerprints, project rollback and
re-editing. The actual GUI regression exercises all 42 controls, English pickers,
copy/reset, invalid-input blocking, exact-reference navigation, project reopening,
empty groups and read-only battlefield links. No edited deployment has been
tested in-game.

## Legion — new in 0.15

Choose **Legion** to browse the **109 definitions** in `Legion.bin`. The supplied
1.00 file has **28 fields per row / 3,052 values**. Names and descriptions use
the supplied **Legion** English message table; previews and reference pickers
keep the native text/ID editable beside the readable English. Searching also
matches equipment, skill, condition and appearance references.

The compact editor has three editable pages and a connections page:

- **Legion:** name/description message keys, level, troop count, command/value
  codes, reward value, gambit skill, equipment items, additional skills and
  battle ambient-sound reference.
- **Stored stats:** signed 16-bit HP, Strength, Magic, Dexterity, Speed, Luck,
  Defense, Resistance, Charm, Sight and Movement values. Their interpretation as
  bases/bonuses/modifiers is unverified.
- **Shop & appearance:** sale-permission flags, price, stock, rarity, appearance
  flags and variation reference. Conditions, code meanings, engine caps and
  equipment/gambit legality are not evaluated. IDs/message keys refer to existing
  game content; no message, asset or sound file is rewritten.
- **Connected entries:** current direct assignments in deployment legion-soldier
  fields, loaded gambit/skill/item records, appearance flags in the AID browser,
  and matching loaded variation entries. Links open the exact deployment file,
  group and slot. Scripts, indirect assignments and final runtime appearance are
  not inferred.

Legion identifiers use **`LID_`**, also used by learning tables in `Growth.bin`.
These are separate namespaces; **`LID_無し` occurs in both**. The deployment
legion chooser reads `Legion.bin` records specifically, and incoming usage only
matches the deployment legion-soldier field. It does not treat every learning
reference as a legion assignment. **Deployment → Connected entries** can now
open its assigned legion directly.

**Items → Used by**, **Skills → Used by** and **AIDs → Who uses it** include
current Legion values and open the matching Legion entry. Unsaved replacement
references immediately replace previous references in those views. Appearance
arrays support positive and negated flags; duplicate flags in one entry do not
inflate its direct-owner count. Related-character links are not inferred from
legion assignments.

**Copy values / Paste values** copies all editable values into another existing
Legion row, keeping the destination's native LID, index and row header fixed.
**Reset entry** restores only the selected legion. No definitions can be added,
deleted, renamed or reordered. Message-key changes affect which existing text
is referenced; this is not an English/Japanese message editor.

Each file saves in a **`fw-legion-edits-v1`** entry guarded by `Legion.bin` and its
original SHA-256. Earlier suite projects remain loadable and clear omitted
Legion edits when replacing the workspace. Projects with Legion entries require
**0.15 or newer**. Standalone `Legion.bin` selection works; **Open last project**
restores the module and its original data paths. A full supplied dataset now
loads/exports **191 files**, including one Legion.bin, one Growth_P0.bin and 171 deployment files.
Source protection, preflight validation, export ownership and dated backups
remain intact.

Validation checks all **3,052 stored values** after joint edits, exact signed and
unsigned numeric bytes/bounds, strings and shared arrays, original IDs/labels/
headers/opaque bytes/pointer targets, transactional source/project guards,
current direct usage, LID namespace isolation and repeated export. The actual
GUI check exercises every field, English choices, copy/reset, bounds, exact
bidirectional links, project reopen, standalone loading and combined export.
Edited legion data has not been tested in-game.

## Expanded progression and difficulty — new in 0.16

Choose **Progression & Difficulty**, then a **Source** and **Section**. These are
additional views of the existing Person/Growth owners, plus the newly supported
`Growth_P0.bin`. They share pending edits with Characters, Learning tables and
GLID progression; the same physical file is never exported twice.

The supplied 1.00 data exposes **13 source/section combinations**, **510 rows**
and **2,397 additional field values**:

| Source | Section | Native tables/records | Rows | Fields per row |
|---|---|---:|---:|---:|
| Growth.bin | Experience curves | 4 | 121 | 2 |
| Growth.bin | Experience modifiers | 9 | 145 | 4 |
| Growth.bin | Experience calculation links | 13 | 13 | 1 |
| Growth.bin | Automatic aptitude experience | 1 | 65 | 2 |
| Growth.bin | Automatic class decisions | 35 | 35 | 15 |
| Growth.bin | Automatic item grants | 7 | 7 | 6 |
| Growth.bin | Protagonist item grants | 8 | 8 | 3 |
| Growth.bin | Automatic legion grants | 1 | 1 | 6 |
| Growth.bin | Part 2 item supplies | 11 | 11 | 4 |
| Growth.bin | Part 2 legion supplies | 13 | 13 | 2 |
| Person.bin | Difficulty loadouts | 83 | 83 | 9 |
| Person.bin | Automatic personal equipment | 7 | 7 | 2 |
| Growth_P0.bin | Part 2 item supplies | 1 | 1 | 4 |

**Experience curves** contain stored level/required-experience pairs for unit,
aptitude, mount and support levels. **Modifiers** contain a signed lookup value
and explicitly named Normal/Hard/Lunatic columns; modifier units and calculation
formulas are unverified. **Calculation links** reference the native EID tables.
Automatic aptitude experience exposes the stored experience and increment.
The form gives simple numeric tables more space for the entry grid; its panes
remain resizable.

**Automatic class decisions** expose the JID, thirteen raw aptitude values and
an optional limited target. Separate form tabs show targets and aptitude values;
the engine's selection rules are not simulated. **Item/legion grants** expose
rank S/A/B/C/D/E references. Protagonist grants expose PID plus conditional and
unconditional lists. Equipment exposes PID and exclusive equipment references.
These do not establish the runtime legality or evaluation of conditional entries.

**Part 2 supplies** expose type, chapter byte list, item-reference list and
quantity byte list, or the reward value and legion list. These are separate raw
lists. Native rows contain several items with a single quantity, and the side
file has an empty quantity list. The editor deliberately does not force equal
lengths, infer alternative/broadcast behavior, or calculate grants. Chapter/type
codes and reward scales remain unverified.

**Difficulty loadouts** have three stored blocks. Each contains initial skills,
barrier items and nested latent-skill rows. They are labelled **Block 1/2/3**;
their mapping/execution order relative to named difficulty modes is unverified.
The nested editor describes stored skill rows, not boolean conditions. Empty
inner rows remain distinct from an empty outer list. Difficulty display names
may use the English name of a character with the identical native suffix; that
is a display alias, not evidence of an assignment.

**Connected entries** shows only current direct fields: explicit character DID
references, calculation-to-experience-table links, and loaded character/class/
item/skill/legion targets. An empty character DID field is not treated as an
implicit name-based assignment. Legion LIDs are resolved against Legion.bin,
independently of Growth learning LIDs. Items/Skills **Used by** includes current
expanded references and opens the exact source, section, table and row. Scripts,
implicit inheritance, formulas, conditional grant execution and final loadouts
are not evaluated. English references reuse the existing message tables;
identifiers and message text are not rewritten.

**Copy entry / Paste values** works within the same section, including the main
and side Part 2 item sections. Destination native IDs, collection/row headers,
counts and order stay fixed. **Reset entry** restores one leaf; **Reset table**
restores the selected native collection, or one record in a flat section. Both
preserve other primary/auxiliary edits sharing the file. No rows, tables or
native IDs can be added/deleted/renamed/reordered. Numeric ranges reflect the
binary types, not verified gameplay caps.

**Project compatibility:** primary-only Person changes retain
`fw-character-edits-v1`; auxiliary changes use **`fw-character-edits-v2`**, with
its source filename/hash and all changes in one Person.bin entry. Learning/GLID-
only changes retain `fw-growth-edits-v1` (old `fw-learning-edits-v1` also loads);
expanded changes use **`fw-growth-edits-v2`**, keeping LID/GLID changes and a
separate auxiliary change list in one Growth.bin entry. The side file uses
**`fw-expanded-side-edits-v1`**. New formats require **0.16 or newer**. A complete
0.16 suite project also contains the new Growth_P0.bin entry, so it needs 0.16
even if that file has no changes. Older projects remain loadable; replacement
clears omitted auxiliary/side edits and invalid loads roll back the whole suite.
The suite's outer format remains unchanged.

The full supplied dataset now exports **191 files**, with one Person.bin, one
Growth.bin, one Growth_P0.bin and all previously supported files. Source-path
protection, preflight builds, output ownership checks and dated backups remain.
**Open last project** restores the selected source and section. Standalone side
files and existing empty grouped tables are supported. Edited progression and
difficulty mods still require an in-game test.

## AID browser — new in 0.4

Choose **Module → AIDs**. This remains a reference browser; **Edit selected row** opens the new Appearance rules editor. The supplied files currently reveal **1,093 distinct AIDs** across **305 readable GameData files**, including AssetTable.bin, AssetTable_P0.bin and AssetTable_P1.bin. Counts depend on which files are available in the selected folder. One supplied file, Gmap/Data.bin, is not in the supported table format and is listed as skipped.

### Source-file sorting (0.5.1)

The AID sidebar groups entries under their discovery filenames by default. Files are sorted alphabetically, and AIDs inside each file are sorted by displayed English/glossary name with the raw ID as a tie-breaker. Expand/collapse file groups to browse them.

Use **Source** above the list to show a single file, such as AssetTable.bin, AssetTable_P0.bin, Person.bin or Job.bin. Text search combines with the selected file. Uncheck **Group by file** for one flat alphabetical list while retaining the source filter.

An AID can occur in several files, so it appears under each corresponding file group. This represents discovery/reference provenance, not a guessed single definition file or runtime loading priority. Live-only AIDs entered into character/class/item asset flags and appearance rules are included under their respective source files. Original non-asset string-pool evidence remains indexed separately. The footer counts unique AIDs even when an AID appears in several groups.

The selected discovery file is included in the detail heading, and Coverage lists every file in which that AID was found. Source filtering changes the sidebar; the detail tabs retain the complete cross-file references, rules and owners.

Search by raw AID or its English/glossary name. The sidebar **Users** count is the number of distinct direct character/class/item owners; **Rows** counts appearance-table rows mentioning the AID. Neither count means all runtime uses. **Copy AID** copies the exact identifier for pasting into an editable character/class/item asset flag.

| Tab | What it shows |
|---|---|
| Who uses it | Current Person/Job/Item asset-flag assignments, negated flags, and related-character links. Double-click a row or choose **Open selected entry** to navigate to its editor. Scenario records are revealed when necessary. |
| Rules & flags | Named condition-set definitions and appearance-table mentions, including unnamed rows, negated tests and mixed references. Select a row to inspect all its fields and nested condition groups. |
| Linked data | Named links from positive references, including body/head/hair settings and FID voice/portrait records. For example, Majide links to voice Maj0 and portrait 095; Dietrich has normal, later and other conditional records. |
| Other references | Exact on-disk string occurrences in readable GameData tables, with source file and string offset. These are evidence of text references, not confirmed assignments. |
| Coverage | Indexed files, per-table group counts, skipped files and interpretation limits. |

Appearance tables are structurally decoded, including 6,184 main rules, 307 asset-information rows, 20 variation rows, 612 voice/portrait rows and 182 condition-set rows in the supplied main table. Side-file rows remain separate; the browser does not assume an overlay order. Color values are displayed as raw byte strings rather than assuming a channel order.

An AID is a conditional flag, not necessarily one model or one character. The browser preserves complete IDs, parentheses in names, comma-separated flags and negation. It does not confuse `AID_example` with `AID_example_variant`, and it distinguishes `!AID_example` from a positive reference.

The owner list refreshes from your **current unsaved edits** when you enter/filter this module. Other references remain original on-disk evidence. Reuse-assets and original-character links are shown as relationships; neither is treated as proof of a final inherited appearance. Conditional rules are not evaluated, their precedence is not simulated, and alternative outfits may all be listed. Scripts, compressed files and runtime-generated flags are not evaluated.

AID browsing alone does not dirty your project. Appearance edits are included in suite projects and mod exports, even while the browser is open. With only appearance tables loaded, those files remain editable/exportable. There is no 3D model or portrait-image preview in this release.

## Class editor

The supplied Job.bin contains **137 class records and 134 fields per record**. All primary class fields are editable. Original class IDs and indexes stay fixed; 0.20 can append new classes without renaming or deleting the originals.

| Tab | Contents |
|---|---|
| Overview | Name and description keys, movement type, rank, gender, support-effect reference, dismounted class, mount reference, icon, appearance flag and class family |
| Stats | Five signed 16-bit stat blocks including class bases and class growth bonuses, signed 8-bit minimum stats, and both signed/unsigned aptitude columns |
| Skills & gear | Exclusive equipment, general class skills, ally/enemy skills, special-attack skills, combat arts, attribute skills and mastery skills |
| Promotion | Lower/upper class links, visible/hidden conditions, required item, barred characters, display weapon, failure coefficient and return-exam value |
| Advanced | AI/deployment values, adjustment rate, difficulty reference, experience, duration, size, battle ranges and shared numeric values |
| Used by | Current explicit JID references across loaded editable modules, plus observed GLID class-name cells; open a selected reference to navigate to its record |

Raw enum values stay numeric. Their option meanings are not yet verified, so the UI does not invent descriptive dropdown choices. Stat columns retain their original order and show their offsets. The identified blocks use the user-provided labels below. Remaining block meanings are not yet verified and keep their original numbers. The two aptitude columns preserve their distinct signedness.

### Creating classes — experimental in 0.20

1. Choose **Classes → Overview → Duplicate class…** to copy the selected class's **134 current field values**, including valid pending edits, stats, skills/equipment, asset keys, nested condition groups and lower/upper/dismount links. **New class…** creates zero-valued numeric fields and empty strings/lists instead. Starting from an existing class is recommended.
2. Enter a unique **`JID_`** ID. Original IDs and row indexes remain unchanged. Unicode and literal pipe suffixes are supported; whitespace, nulls, quotes, `, ; ! &` and `::` separators are rejected. New records are appended and receive unused ascending header tags. The meaning of those tags and engine record limits remain unverified.
3. Configure the new class before assigning it. Name/help fields remain **existing message keys**, such as `MJID_…`; this update does not create new localization text, models, animations or icons. Existing resource keys can be reused.
4. Direct class links use actual record pointers on export. New-to-new, native-to-new, self links and cycles round-trip through project loading and binary export. Copying retains the source's current links **literally**; it does not rewrite self references or add reciprocal promotion links automatically. Set those relationships deliberately.
5. New JIDs appear immediately in the character/class, skill, facility-training, appearance-condition and automatic-class-grant choosers. GLID category 0 stores the **bare class name**, without `JID_`; its chooser and English preview handle new classes too. Creating a class does not automatically unlock it, place it in a route, or make a character use it.
6. **Used by** finds current explicit JID references in supported loaded editable fields, including nested conditions, and observed category-0 GLID cells. Double-click or **Open selected entry** opens the target record; GLID links select the exact category row and level. **Refresh references** includes committed edits. Counts describe stored occurrences, not evaluated runtime assignments. Scripts, unsupported auxiliary groups, unloaded files and indirect runtime rules are not checked.
7. **Remove new class** works only for added classes and refuses while other loaded editable records or observed GLID cells reference that JID. Self references inside the removed record are excluded. Original classes cannot be removed. Reset entry keeps the new ID and restores its creation-time values.
8. **Save project**, **Open last project** and **Export mod** preserve new classes alongside ordinary changes, learning additions and new items. Class definitions use **`fw-class-edits-v2`**, tied to the original Job.bin filename/SHA and requiring **0.20+**. Without additions the original class v1 format is retained. Older projects can replace additions; failed loads restore the previous workspace transactionally.
9. Exports update the Job record array, relocation locations/targets, indexed labels, schema and pool offsets. Existing primary values, original headers/indexes and opaque auxiliary bytes are preserved, apart from deliberate edits and pointer rebasing. Original source files are never overwritten. Continue opening the original matching game folder when editing saved projects.

**In-game behavior is not yet verified.** Test one duplicated class assigned to one character in a separate mod first. Engine capacity, header-tag meaning, class availability, asset completeness and save compatibility cannot be established by file round-trip tests. Keep source and save backups. Character creation is available in 0.21 below. Terrain remains pending.

### Identified stat labels (0.4.1)

These labels were supplied by the user. Only display labels changed; offsets, values, data types and project compatibility are unchanged.

| Module | Original column | Display label | Starting offset |
|---|---|---|---|
| Classes | Block 2 | Class bases | `0x136` |
| Classes | Block 5 | Class growth bonuses | `0x178` |
| Classes | Extra | Minimum stats | `0x219` |
| Characters | Block 1 | Personal bases | `0x1C2` |
| Characters | Block 5 | Personal growths | `0x21C` |
| Character aptitudes | Block 1 | Starting value | `0x248` |
| Character aptitudes | Block 2 | Aptitude growth | `0x255` |

Class aptitude columns remain Signed/Unsigned; the new aptitude labels apply to the character editor. Remaining stat columns retain their block numbers. Headers wrap to keep the compact layout.

### Promotion conditions

The two condition fields contain nested lists. Click **…** beside either field to open the **condition-group editor**. Choose a group, edit one raw condition ID per line, or add/remove groups. English previews update beside the IDs. **Use groups** updates the main form; **Cancel** leaves it untouched.

The main form exposes the same structure as one JSON list per line for advanced editing:

```json
["condition_one", "condition_two"]
["another_group"]
```

The exact AND/OR semantics of these groups have not been verified. Original grouping is preserved. Empty text clears all groups; `[]` preserves one empty group. Replacing a condition list or skill list allocates separate data rather than changing a shared array in place.

Lower/upper/dismounted class links are actual pointers to class records. The chooser displays their IDs and English names, and export writes the correct direct record pointers. These links must refer to an existing class or be left empty. Other string-based references remain raw identifiers and may be typed manually.

**Used by** scans the current in-memory Person.bin, including character edits made during this session. It does not inspect GLID/LID progression, deployment files or scripts and is not a complete runtime usage map. Job.bin's auxiliary mount and support-effect tables are preserved, but their records are not separate editable modules in this release.

## Event editor — new in 0.22

Choose **Module → Events**, then its **Event source**. The full original folder now loads **204 physical documents**: the previous 191 plus 13 event files. This adds event data editing; it does not add dialogue-text writing.

| Sources | What can be edited |
|---|---|
| Variable.bin, Variable_P0.bin, Variable_P1.bin | Initial/minimum/maximum values, value labels, raw update/change codes, nested condition groups, dates and result codes |
| Timeline_Com.bin, Timeline_Part0_Ism.bin, Timeline_Part1_Dit/Kai/Led/Seo.bin, Timeline_Part2.bin, Timeline_Part3_Ism.bin | Ordered event type/argument rows, nested conditions, interval flags, dates, locations, destinations, locators and message-key references |
| Chapter.bin | Part/chapter/route codes, conditions and permission flags |
| Situation.bin | Condition groups, dates, location/placement and accompanying-group references |

These contain **4,631 native rows and 72,545 field values**. The sidebar selects a variable/rule or a native timeline collection. The Entries tab selects an existing row; the form shows raw values beside English/glossary explanations, with a separate date/schedule tab where applicable. Unknown event/enum values remain numeric rather than receiving invented names. Nested conditions retain their exact groups; this editor does not simulate evaluation or infer a full AND/OR grammar.

**Copy editable values**, **Paste editable values** and **Reset row** operate on the selected row. Paste requires the same schema and excludes the fixed variable name or timeline hash key. The main **Reset table** button resets the selected collection. Variable names, hash keys, native header labels, row counts and event order remain fixed. Event insertion, deletion, arbitrary reordering, compilation and new script generation are outside this first release.

**Connections** can refresh outgoing explicit variable and character/class/item/skill references and open their exact current source record. Current PID/JID/IID/SID references in loaded event fields also participate in the suite's existing usage views and new-entry removal guards. Stored references are not proof that a particular event executes; scripts, numeric/indirect references and runtime condition selection are not evaluated.

The **Majide cape** tab provides links to the cape AID, Majide/Dietrich equipped rules, received/lost-fight date rules, the `BD12_04` duel command and following Ink-Black Wen argument. Links resolve by expected native names/arguments, with original 1.00 row indexes shown as references. Its appearance shortcut opens the matching AssetTable cape rule. **No cape patch is applied automatically.** The included [research report](EVENT-RESEARCH.md) documents removing only the negated lost-fight token from Majide's equipped condition as an in-game test, while keeping the received-date condition.

**Compiled scripts** looks for an adjacent `Script` folder and can inspect all 183 supplied `.bin.zst` files. It displays the validated ASF wrapper, imported script paths and printable ASCII identifier runs. Those runs are **not** decompiled statements, function declarations or executed-call counts. This wrapper view remains read-only. **Open script editor…** (0.23) opens decoded instructions/constants with the editing and export capabilities documented in [SCRIPT-EDITOR.md](SCRIPT-EDITOR.md). Opening a data-only folder still works without Script. MSBT text remains untouched; changing an event's message-key argument changes its reference, not its dialogue text.

Event source/module selection is remembered with saved projects. Each source uses **fw-event-edits-v1**, tied to its original filename and SHA. Suite loading is transactional; older projects clear omitted event edits, and failed imports preserve the active workspace. Export writes one binary per source with validated relocations and copy-on-write arrays, retaining original/opaque data and making backups of prior owned exports. Keep the original source folder unchanged and choose a separate mod folder.

**Test event changes in game with a backup.** The cape chain is verified in stored data and exported binaries; execution timing, condition-refresh behavior and existing-save recomputation have not been traced. Raw mode/type codes and sentinel dates must be used deliberately. The editor does not claim a complete script compiler or event simulator. Terrain and dialogue-text editing remain pending.

## Character editor

The existing compact editor is retained, including its identity, class/learning/progression references, six raw stat blocks, aptitudes, skills, items, appearance and advanced fields. **Scenario / test records** shows all 2,923 supplied records rather than the 73 with a character serial. The selected tab is remembered when changing entries and modules.

Original character PIDs, indexes and serials stay fixed. New characters can be appended in 0.21; each new serial is chosen once at creation and then locked. Forced skills and role flags can affect convoy access, Blaze eligibility and route behavior. Asset fields reuse existing appearance rules; they do not provide model/portrait previews or automatic full-character swaps.

### Creating characters — experimental in 0.21

1. Choose **Characters → Character tab → Duplicate character…**. This copies all current editable values, including valid pending edits, stats, aptitudes, class/LID/GLID references, skills, items, name/internal identifier, appearance and support/profile links. **New character…** starts with numeric zeros and empty strings/lists. Original PIDs and row indexes remain unchanged; new records append after the 2,923 native records.
2. Enter a unique **`PID_`** ID. Unicode and literal pipe suffixes are accepted. Whitespace, nulls, quotes, `, ; ! &` and `::` separators are rejected. IDs cannot rename or replace an existing source entry.
3. Choose the **creation-time serial**. **Zero is the default**, as used by 2,850 native unnumbered variants/NPCs. A positive serial must be an unused integer from **1 through 255** in the loaded Person.bin; the prompt shows examples. A duplicate **never inherits its source's occupied nonzero serial**. For example, 42 is unused in the supplied file, but that does **not** establish that the engine supports a new playable slot there. The 73 existing nonzero serials remain unchanged. All serials stay read-only after creation; to choose a different one, remove an unreferenced new entry and recreate it.
4. New entries with serial zero remain visible in the normal character sidebar. **Scenario / test records** still controls the original unnumbered variants. Serial zero does not promise recruitability or playable-roster/save support.
5. Duplicated links and keys are copied **literally**. Asset reuse, original-character references, internal identifier, profile/support affiliation and progression links can still point to the source's resources. Copies do not get independent support rows, recruitment conditions, profiles, named appearance rules, save slots or story events automatically. No reciprocal links or self references are rewritten. Configure these fields deliberately; this is a data-definition editor.
6. Reuse existing name/message keys, appearance flags and resource references, then configure placement or other references explicitly. This update does not write new localization text, portraits, models, voice files or event scripts, nor does it expand fixed support/recruitment tables. Creating a PID alone does **not** recruit or deploy it. The battle deployment editor can point an existing unit entry to a new PID; it does not create new battle rows.
7. New PIDs appear immediately in character asset/original references, class barred-character lists, skill references, support/voice conditions, facility references, appearance conditions, automatic grants/equipment and battle-deployment pickers. English names resolve through the new character's current name key without altering its raw ID.
8. **Used by** scans current explicit `PID_` tokens in supported loaded editable fields, including nested conditions. It scans when that tab opens or when **Refresh references** is clicked. **Open selected entry** navigates to the referencing record, including the exact battle unit or expanded progression row. It does not evaluate conditions, scripts, header names, bare identifiers, indirect references or numeric serial references. Original source-string evidence elsewhere in the suite remains a separate original-data view.
9. **Remove new character** refuses while other loaded editable fields explicitly reference its PID. Self references within the removed entry are excluded. Only new characters may be removed. **Reset entry** restores creation-time field values while keeping its PID and chosen serial. Removing an entry releases its positive serial for reuse by another new entry; original serials cannot be reassigned.
10. **Save project**, **Open last project** and **Export mod** retain character additions together with ordinary character edits, Person.bin difficulty/equipment views and other module edits. New definitions use **`fw-character-edits-v3`**, tied to the original Person.bin filename/SHA, and require **0.21+**. The existing character v1/v2 formats remain supported. Older projects replace additions; invalid loads restore the previous workspace transactionally.
11. Export updates the primary record array, relocation locations/targets, indexed labels, string pool and schema offsets. Existing headers, original slots and opaque auxiliary data are preserved apart from deliberate edits and pointer rebasing. Source files are never overwritten. Keep opening the original matching data folder with saved projects, and export to a separate mod folder.

**Test one duplicate in a separate mod first.** This release verifies file integrity and reference editing, not in-game viability. Runtime character-count limits, header-tag meaning, unused serial semantics, roster indexing, support/recruitment integration, asset resolution and save compatibility remain unverified. A readable exported file does not prove a new character is playable. Keep source and save backups.

## English previews and glossary

Raw Japanese references stay editable beside live English previews, updating 120 ms after typing, pasting or choosing a value. Lists show one preview per line. Reference choosers search English names and raw IDs.

- **English** is an exact name/description from the user's game message tables.
- **≈ glossary** is an approximate local explanation of an internal identifier, using known names and editorial vocabulary.
- **≈ partial** retains unrecognized Japanese in a partially translated identifier.
- **Unknown** means no translation was found; the raw ID remains visible.
- **Custom** means an exact translation supplied by the user.

Double-click a preview or use **Tools → Translation glossary** to add an exact ID or Japanese word translation. Words also apply inside longer identifiers. Custom exact IDs override game text; custom words supplement identifier explanations. Changes refresh previews immediately. Translations persist separately from edit projects at `~/.config/fw-character-editor/translations.json` (or the equivalent XDG configuration directory), retaining compatibility with 0.2.

All translations work offline. Arbitrary unknown Japanese prose is not machine-translated. Translation previews never rewrite exported identifiers.

## Scope and validation

Supported data layout: the supplied **1.00** files. Edited exports have **not yet been tested in-game**. Structural verification does not prove every manually entered reference exists or that every field combination is valid for gameplay.

Validation includes:

- Byte-identical output with no edits; exact numeric-byte checks.
- All 417,989 character field values and all 18,358 class field values compared after mixed edits.
- Direct class-pointer changes, nested condition groups including empty groups, shared-array isolation, null references, Unicode and reopen/re-edit/export.
- Preservation of auxiliary mount/support data, labels and unrelated records.
- Numeric bounds, immutable character serials, project compatibility and transactional project loading.
- Combined-table export preflight, source/unrelated-file protection and output backups.
- Last-used-path persistence, fresh-start project reopening, remembered dialogs and failure preflight that preserves the active workspace.
- All 123,785 primary/auxiliary item values checked after joint edits, including shop and lottery collection headers, empty collections, exchange pairs, signed discounts, live usages, v1/v2 project migration and a single shared Item.bin export.
- All 8,512 facility/reward values checked across four files, including 28 native collection headers, source-specific side files, paired skill weights, exact floats, original counts/pointers/opaque bytes and live links; all facility/reward layouts and eighteen-file exports verified through the GUI.
- All 18,445 Profile field values checked across five sections, with paired history validation, native headers/names/counts and unrelated bytes/pointers preserved; English biography/clan previews, current character/affiliation links, profile gift usages and combined export verified.
- All 20,033 Reliance field values and all 5,329 directed compatibility cells checked after joint edits across seven sections; native names (including empty/duplicate names), record counts, original pointers/opaque bytes, fixed vector lengths, project rollback and shared-file export preserved.
- Supports GUI validates every section, directional cell edits, raw scouting fields, English character/item choices, item-to-scout navigation, connected-character owners, saved section restoration and standalone loading.
- All 111,040 item-field values compared after mixed edits across three files; signed 32-bit costs/counts, unsigned prices/flags, shared skill lists, literal pipe-suffix IDs, original pointer targets, opaque auxiliary bytes, side-file isolation, nine-file exports and backups checked.
- Item reference coverage includes live SID↔IID links, observed GLID category/level cells and 1,937 shop/lottery rows, with navigation to the precise source/row/level.
- All 452,945 skill-field values across three separate files compared after mixed edits, with nested data references, numeric arrays, finite float32 normalization, shared-array isolation, file-specific projects, original pointer targets and unrelated bytes preserved.
- SID token identity (brackets, reserved names, negation and fullwidth plus signs), live character/class/LID/skill references, item links, original-file evidence, side-file navigation and copied IDs.
- All 132,030 GLID field values and 20,170 learning-entry field values compared after joint edits; collection/leaf headers, labels, untouched pointer targets and unrelated Growth.bin bytes preserved.
- All 20,170 learning-entry field values compared after mixed edits; original collection/entry counts, labels, non-learning pointer targets and unrelated Growth.bin bytes preserved.
- Learning-list expansion: Dietrich 56→64 rows, all 153,832 original Growth values preserved; multi-list additions, first entries in empty groups, original header tags/opaque bytes/pointer targets, unique new tags, condition-list isolation, v3 projects, cross-file rollback, reset/undo, usage links and repeated export/re-edit checked. These are file/GUI checks, not game compatibility tests.
- New learning lists: blank and full-list copies, indexed Unicode IDs, independent current values, original source indexes/opaque bytes/relocations/labels, multi-boundary header+row insertion, empty groups, capacity errors, v4 transactional projects, character assignments, guarded removal and re-editing exported files checked. Original list deletion remains blocked.
- AID source-file membership across multiple files, live-only flags, source filtering, alphabetical grouping and flat-list navigation.
- AID token identity/negation, unnamed rules, side files, condition definitions, FID lookup, source evidence, live owners, character-link cycles, skipped-file reporting and source immutability.
- Actual Tk GUI checks for the editing modules and the AID browser, minimum 1000 × 680 stat layout, live translations, nested-group editing, reference selection, module/tab retention, legacy project loading, reset, combined export and class-usage navigation.

New characters, classes, items and learning lists can be created as described above; original IDs stay fixed. Appearance rules and existing shop/lottery/value rows are editable in their respective modules. Existing primary fields and references remain editable in their respective modules.

## Tests

Version 0.14 passed **103 data tests** with the supplied inputs on Linux and Windows CPython, plus **all fourteen actual Tk GUI regressions** under Windows CPython through Wine. Only the Linux-specific ImageMagick screenshot commands are omitted in that Windows GUI run. The final executable also passes its own frozen startup/decompression check. No edited mod has been tested in-game.

Synthetic tests contain no game data:

```sh
python3 -m unittest discover -s tests -v
```

Run the optional real-data regressions using your own files:

```sh
FW_GAME_DATA=/path/to/romfs/GameData \
FW_MESSAGES=/path/to/romfs/Msg/USen \
python3 -m unittest discover -s tests -v
```

With a graphical session, the same environment variables support `python3 tests/gui_smoke.py`, `python3 tests/gui_classes.py`, `python3 tests/gui_assets.py`, `python3 tests/gui_recent.py`, `python3 tests/gui_learning.py`, `python3 tests/gui_progression.py`, `python3 tests/gui_skills.py`, `python3 tests/gui_items.py` `python3 tests/gui_supports.py`, `python3 tests/gui_appearance.py`, `python3 tests/gui_profiles.py`, `python3 tests/gui_facilities.py` and `python3 tests/gui_shops.py`, `python3 tests/gui_deployment.py`, `python3 tests/gui_legion.py`, `python3 tests/gui_expanded.py` and `python3 tests/gui_learning_entries.py` and `python3 tests/gui_learning_lists.py` and `python3 tests/gui_item_creation.py` and `python3 tests/gui_class_creation.py` and `python3 tests/gui_person_creation.py` and `python3 tests/gui_events.py` and `python3 tests/gui_script_editor.py`. The GUI checks additionally use ImageMagick's `import` utility for screenshots. All test exports go to temporary directories.

## Building the Windows executable

Use official **64-bit Python 3.12** on Windows, with Tcl/Tk, pip and the Python launcher. From the complete source package, double-click **build-windows.bat**. It creates `.venv-windows`, installs the pinned build requirements, runs format tests, packages a windowed single executable and runs its health check before writing the Windows ZIP into `dist/`. The ZIP includes third-party license notices. Building requires an internet connection for the initial dependencies; running the editor works offline.

For an existing Windows Python environment:

```powershell
python -m pip install -r requirements-windows-build.txt
python build_windows.py
```

PyInstaller builds for its host OS: Linux PyInstaller cannot produce the Windows binary. The included `.github/workflows/windows.yml` builds on a Windows runner when manually dispatched or when a version tag is pushed. This file does not create or publish a GitHub repository automatically. Optional real-data tests run only if `FW_GAME_DATA` and `FW_MESSAGES` are explicitly supplied; game files are never added to the application archive.

The packaged health check can be repeated without touching a project:

```powershell
.\Crednas-Creation-Kit.exe --self-test .\windows-self-test.json
```

It checks frozen UI-module imports, native Zstandard decoding (including Japanese UTF-8), and creation of the actual editor window with all sixteen modules. It uses temporary preferences and writes the JSON report after success. Full data-editing regressions remain in `tests/` in the source archive.


Version 0.15 passed **112 data tests** on Linux and Windows CPython, **all fifteen Linux Tk GUI regressions**, and **eight focused Windows Tk regressions** covering Legion, deployment, AIDs, items, skills, learning, GLID progression and saved-path reopening. Windows GUI checks use CPython/Tk through Wine; only Linux screenshot commands are omitted. Its final frozen executable passes startup/import/native-decompression checks with all fourteen modules. No edited mod has been tested in-game.


Version 0.16 passed **122 data tests** on Linux and Windows CPython, **all sixteen Linux Tk GUI regressions**, and **eight focused Windows Tk regressions** covering expanded progression/difficulty, Characters, learning, GLID progression, items, skills, Legion and saved-path reopening. The new GUI check also exercises shared v1/v2 projects, nested skill rows, source/section restoration, exact links and 191-file exports. Windows UI checks use Wine; the frozen executable verifies startup/import/native Zstandard with all fifteen modules. No edited mod has been tested in-game.

Version 0.17 passed **132 data tests** on Linux and Windows CPython, **all seventeen Linux Tk GUI regressions**, and focused Windows Tk GUI checks, including the actual Add/Duplicate/Undo controls, empty lists, live skill-to-added-row links, shared GLID/auxiliary exports, v3 projects, resets and reopening. Windows checks run CPython/Tk through Wine. The frozen executable passes startup/import/native-Zstandard checks with all fifteen modules. Synthetic-only tests run without game inputs (34 private-data tests skip). Learning-row additions remain **experimental until tested in-game**, including the unused header-tag allocation and runtime/save limits.

Version 0.18 passed **142 data tests** on Linux and Windows CPython, **all eighteen Linux Tk GUI regressions**, and focused Windows Tk GUI checks, including blank/new Unicode LID definitions, whole-list copies, the live character learning chooser and assignments, guarded removal, SID navigation, v4 project/legacy replacement, reopening and 191-file exports. Windows checks use Wine; the frozen executable passes startup/import/native-Zstandard checks with all fifteen modules. Synthetic-only runs skip 36 private-data tests. No new list has been tested in-game, and header-tag meaning/runtime/save limits remain unverified.

Version 0.19 passes **154 data tests** on Linux and Windows CPython, **all nineteen Linux Tk GUI regressions**, and focused Windows Tk GUI checks. New coverage includes all 80 fields of created items, main/side-source separation, original 123,785 item/auxiliary values and opaque bytes, independent duplicates, live names/types and IID choosers across supported modules, inventory/shop placement, guarded removal, cross-file collision rollback, v3 project/legacy replacement/reopening, and 191-file exports. Windows checks use Wine; the frozen executable passes startup/import/native-Zstandard checks with all fifteen modules. Synthetic-only runs skip 39 private-data tests. Item creation remains experimental until tested in-game; header-tag meaning, engine/side-file limits and save compatibility are unverified.

Version 0.20 passes **165 data tests** on Linux and Windows CPython, **all twenty Linux Tk GUI regressions**, and focused Windows Tk GUI checks. New coverage includes all 134 new class fields, direct-pointer relationships/cycles, nested-copy independence, all 18,358 original primary values, opaque auxiliary bytes and indexed labels, transactional v2/legacy projects, combined class/item/learning edits, live JID choosers, incoming references, guarded removal, exact GLID navigation, compact layout and 191-file exports. The frozen executable passes startup, new-module import and native-Zstandard checks with all fifteen modules. Synthetic-only runs skip 42 private-data tests. Windows checks use Windows CPython/Tk and PyInstaller through Wine; physical Windows and in-game validation remain pending.

Version 0.21 passes **178 data tests** on Linux and Windows CPython, **all twenty-one Linux Tk GUI regressions**, and focused Windows Tk GUI checks. New coverage includes all 143 new field values (142 editable plus the fixed creation serial), all 418,750 original primary/auxiliary values and opaque bytes, zero/unique positive serials, immutable original slots, literal links, independent copies, v3/legacy/suite rollback, new-character/class/item/LID integration, live PID pickers and deployment assignments, guarded removal, exact reference navigation, compact layout and 191-file exports. The frozen executable passes startup, new-module import and native-Zstandard checks with all fifteen modules. Synthetic-only runs skip 46 private-data tests. Windows checks use Windows CPython/Tk and PyInstaller through Wine; physical Windows and in-game validation remain pending.

Version 0.22 passes **191 data tests** on Linux and Windows CPython, **all twenty-two Linux Tk GUI regressions**, and focused Windows Tk GUI checks. New coverage includes all 13 sources/four schemas, all 72,545 native event values, opaque bytes/relocations, immutable identities, nested condition copy-on-write, the exact Majide cape chain, ordered arguments/dates, project/source rollback, current event PID references, all 183 read-only compiled wrappers and 204-file exports. Compiled-bytecode and in-game validation remain separate from binary round-trip checks. The frozen executable passes new-module imports, native-Zstandard decoding and startup with all sixteen modules. Synthetic-only runs skip 50 private-data tests. Windows tests use Windows CPython/Tk through Wine; physical Windows validation remains pending.


## Compiled script editing (0.23)

Tools → Script editor… opens the new function/instruction and string-constant editor. See [SCRIPT-EDITOR.md](SCRIPT-EDITOR.md) for the workflow, precise limits, script-aware suite v2 projects and compressed `romfs/Script` exports. GameData-only loading still has 204 files; each selected script adds one workspace/project/export source. Existing GameData-only projects remain supported. Structural round-trip checks are separate from in-game validation.

Version 0.23 passes **202 data tests** on Linux and Windows CPython, including all **183 compiled scripts / 10,554 function bodies / 490,221 instructions / 11,536 runtime constants**, complete parse/rebuild and representative constant/literal mutations. The new tests cover string-cache aliases without metadata changes, integer-encoding boundaries, constrained instructions/call signatures, compressed Script exports, source protection, transactional project replay and live PID/JID/IID/SID reference guards. Eight focused Linux Tk GUI regressions pass, along with a separate script-editor check through the real Linux command-line entry point. Synthetic-only runs skip 51 private-data tests. The frozen Windows x64 executable passes startup, all sixteen modules, script-component imports and native Zstandard checks. Windows checks use Windows CPython/Tk through Wine; physical Windows and edited-event in-game validation remain pending.


## Renamed in 0.24

The official name is **Credna's Creation Kit**. Release archives and the Windows executable use `Crednas-Creation-Kit` as the filename stem. The Linux entry point remains `fw_editor.py`, the existing desktop-file ID is reused, and the legacy `fw-character-editor` preferences location and `FW_EDITOR_CONFIG` override remain valid. Project format identifiers (`fw-…`) stay unchanged for compatibility. Save your project before upgrading, extract the entire new package, and rerun `bash install.sh` on Linux to update the shortcut name/path. The software license and third-party notices are unchanged.

Version 0.24's branding update passes the synthetic suite on Linux and Windows CPython (202 tests run, 51 private-data tests skipped), Linux startup/name/decompression checks, three focused real-data GUI regressions (editing, remembered-project reopening, script editing/export), isolated desktop/menu launcher generation, and the renamed Windows x64 executable's frozen startup/name/native-Zstandard health check with all sixteen modules. Data formats and editing behavior are unchanged from 0.23.
