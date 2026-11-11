# Compiled scripts

Open **Tools → Script editor…**, or use the corresponding button in **Events**. Select a script from your own data. The editor decodes supported compiled-script functions, instructions and constants; it does not recover the original source code.

## Supported edits

- **String constants:** edit stored text with a live English/glossary preview. A constant can be shared by several instructions; its use list shows direct references within the selected script. Double-click a use to navigate to its instruction, or a string-referencing instruction to open its constant.
- **Numeric literals:** edit supported 32/64-bit immediate values. Choose unsigned bits, signed integer or floating point. The original high-level numeric type cannot always be recovered, so select the interpretation appropriate to the command.
- **Conditions:** invert supported paired conditional branches while retaining their destination.
- **Calls:** choose another existing reference with a matching function signature. This preserves the supported call shape, not its gameplay meaning.

Other instructions remain read-only. Adding/removing instructions or functions, arbitrary jump destinations, new imports, signatures and stack-slot changes are unsupported. This is not a full source compiler.

## Save and verify

Apply the selected value or navigate with a valid pending value. Invalid input blocks the action. **Restore source value** resets the selection. Selected scripts join the normal project and export actions; their original compression and relative output paths are retained.

The writer rebuilds serialized strings and reparses edited payloads before export, checking the intended string/instruction changes. Unsupported layouts are rejected. Structural checks do not establish in-game correctness or show which commands will execute in a scene.

[Projects and export](Projects-and-export.md) · [Guide home](Home.md)
