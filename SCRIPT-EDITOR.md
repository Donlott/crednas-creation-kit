# Credna's Creation Kit · compiled script editor

Available since 0.23; the program was renamed from FW Hacking Suite in 0.24.

Open **Tools → Script editor…**, or **Events → Compiled scripts → Open script editor…**. Keep your original `Script` folder beside `GameData`. Select the matching game 1.00 data first. This editor works offline on Linux and in the Windows executable.

This is a **limited instruction-level editor** for the supplied ASF/AngelScript scripts. It can change compiled behavior and rebuild script files. It does not recover the original source code or compile newly written AngelScript.

## Editing

1. Select a source such as `cmdbtl/BD12_04.bin.zst`. Paths show the originating folder. Scripts load when selected; simply viewing one leaves its original bytes unchanged.
2. In **Functions / instructions**, search for a function. Named functions appear before global initializers. The list shows instruction indexes, opcode names, serialized operands and resolved function/string references. Branch annotations show their destination instruction.
3. Select a supported instruction and edit **Selected value**, then press **Apply value**. Selecting another value, saving, exporting or closing applies a valid pending value; invalid input blocks the action. **Restore source value** resets the selected value only.
4. Use **String constants** to edit runtime strings, with a live English/glossary preview. These can include event identifiers, variable names or asset references. Translation is a display aid and never replaces the stored value automatically. Untranslated text remains visible.
5. The **Used by function** list shows every direct `PGA`/`PshGPtr` use of the selected constant in this script. Double-click a use to open its instruction. Double-click a string-referencing instruction to open its constant. A constant may have several uses: editing it affects all of them.

Supported instruction changes:

- **Numeric literals:** `PshC4`, `PshC8`, `SetV4`, `SetV8`. Choose **Unsigned bits**, **Signed integer**, or **Floating point**. The original high-level numeric type cannot always be recovered; select the interpretation appropriate to the command. Switching interpretation changes the display of the applied bits. Apply a typed edit before switching modes. Integers accept decimal and `0x` hexadecimal.
- **Conditional inversion:** `JZ ↔ JNZ`, `JS ↔ JNS`, `JP ↔ JNP`, `JLowZ ↔ JLowNZ`. The original destination is retained. These changes reverse existing conditions; they do not add new event branches.
- **Call replacement:** select another existing reference with an identical function kind, return/parameter types, argument directions, receiver, traits and template types. Calls cannot be replaced with an arbitrary command name, and this does not add a new engine API. Matching signatures protect stack shape, not gameplay semantics.

Other instructions remain visible and read-only. Instruction/function insertion or deletion, arbitrary jump destinations, signatures, stack slots and import definitions are not editable. Those operations require a compiler or additional control-flow and cleanup reconstruction.

## Saving and exporting

**Save project…** and **Export mod…** use the normal suite actions. Opening a script adds that selected script to the suite workspace, alongside the existing GameData tables. Project files containing scripts use **suite v2** with SHA-bound **script v1** entries and require **0.23 or newer**. Older GameData-only projects still load.

**Open last project** restores selected scripts and their edits from the original files. Keep the original compressed files unchanged: a different source fingerprint is rejected. The script editor reopens from Tools; the main workspace's module remains selected.

Exports write selected scripts to **`romfs/Script/<original relative path>`**, keeping `.bin.zst` files compressed. GameData stays under `romfs/GameData`. Unedited selected scripts are byte-identical to their sources. Re-exported files owned by the editor receive backups. Originals and unrelated output files are protected. No game files are distributed with this program.

Loaded script constants participate in explicit PID/JID/IID/SID usage searches and new-record removal guards. A usage link opens its script constant. Unopened scripts and indirect runtime references are not scanned; these searches do not prove that a new character/class/item is fully integrated.

## Rebuild checks and limits

The reader parses the module's declarations, functions, instructions and reference tables, and requires complete payload consumption. It supports the stripped-debug layout verified in the supplied game 1.00 scripts. Unsupported/damaged layouts are rejected; the old wrapper inspector remains available.

Rebuilding updates the ASF payload size and reindexes serialized string caches. This matters when a runtime constant originally refers to the same cached text as a function name: changing that constant must leave the function's name intact. Every edited payload is reparsed and its string and instruction sequences compared with the intended result before compression/export.

All **183 supplied scripts**, containing **10,554 function bodies**, **490,221 instructions** and **11,536 runtime string constants**, pass structural parse/rebuild tests and representative constant/literal mutations. Tests also cover malformed files, encoding boundaries, shared-string aliases, signatures, project rollback, paths/compression, live references and the real Tk interface. **These checks do not establish in-game correctness.** Test edited events in a separate mod with a save backup.

Majide's cape findings in **EVENT-RESEARCH.md** still point to the stored variable/appearance condition chain. The compiled duel is `Script/cmdbtl/BD12_04.bin.zst`; it delegates much of its work through imported/common commands. This release does not apply a cape patch or claim an exact runtime trace of the cape change.

## Format reference

Serializer rules and opcode layouts were checked against AngelScript's 2021 implementation, mirrored at `codecat/angelscript-mirror` commit `522a5fe8efbb8b4f964801e5515eafd8c018d46c`, and verified against the supplied files. The Python reader/writer is an altered implementation, not the AngelScript engine. See **licenses/AngelScript-LICENSE.txt**. The original library is by Andreas Jonsson at <https://www.angelcode.com/angelscript/>.
