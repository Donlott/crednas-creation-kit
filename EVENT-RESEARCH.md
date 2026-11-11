# Fortune's Weave 1.00: Majide's Ink-Black Wen and event editing

These findings come from the user's original extracted data. File and row references below are zero-based native rows. They are stored-data evidence, not an emulator execution trace. No game data is bundled with the editor and no cape edit is applied automatically.

## What controls the cape

The appearance condition is explicit in **AssetTable.bin**, appearance rule **2097**:

- Conditions: `AID_マジーデ` together with `AID_マジーデマント有り`.
- Body model: `CD_095` (the caped variant).
- The nearby default-clothing rule **2096** uses `CD_095(-A)` (the variant without the cape).

The main Majide character record uses `AID_マジーデ`. His duel variant, `PID_BD12_04_マジーデ`, reuses the main `PID_マジーデ` resources. The cape does not require a different base character PID.

`MIID_BlackGwen` in the supplied English Item message table is **Ink-Black Wen**. The native timeline argument is `漆黒のグウェン`. Some flag identifiers spell the name `グウエン`; retain their exact spelling.

## The condition chain in Variable.bin

| Native row | Variable name | Stored condition / date |
|---|---|---|
| 871 | `AID_マジーデマント有り` | `進行_容姿変化_同期_マジーデが漆黒のグウエンを装着` |
| 1216 | `進行_容姿変化_同期_マジーデが漆黒のグウエンを装着` | Received-date flag plus **negated lost-duel flag**, in one stored condition group |
| 1217 | `進行_容姿変化_同期_ディートリヒが漆黒のグウエンを装着` | Lost-duel flag |
| 1485 | `同期_日付_マジーデが漆黒のグウェンを受け取った` | Year 1449, March 1, raw time `2359` |
| 1486 | `同期_日付_マジーデが野良試合で負けた` | Year 1449, March 8, raw time `1459` |

Row **1216** stores this exact condition group:

```json
["同期_日付_マジーデが漆黒のグウェンを受け取った", "!同期_日付_マジーデが野良試合で負けた"]
```

There is also a paired Dietrich rule: Variable row **870**, `AID_ディートリヒマント無し`, depends on the **negation** of the Dietrich-equipped flag from row 1217. AssetTable rule **1667** uses this no-cape flag and body `CD_019 (-A)`.

This is consistent with Majide losing the cape and Dietrich gaining it after the duel. The immediate configurable link is a condition chain, rather than a literal “replace Majide's AID” instruction found in the supplied compiled scripts.

The cape-related condition-driven variables have raw update/change codes `2/2`; the two date variables have `3/2`. Those values are preserved and remain raw in the editor. Their complete engine enum meanings and evaluation timing have not been reverse engineered.

## The duel and following event

In **Timeline_Part1_Dit.bin**, route collection 0:

| Native entry | Type code | Arguments / context |
|---|---|---|
| 77 | 7 | `NR11_00`; March 8, raw time `1200`, Dagsion |
| 81 | 6 | `MID_EV12_015_m01`; raw time `1400` |
| 82 | 15 | `BD12_04` |
| 85 | 29 | `漆黒のグウェン` |
| 87 | 6 | `MID_EV12_016_m01`; raw time `1500` |

**CmdBtl.bin**, party-settings row **8**, independently links script `BD12_04`, forced participant `PID_ディートリヒ`, enemy party `Member_BD12_04_E`, and the native comment `ディートリヒ篇４章　BD12_04_マジーデとの戦い` (Dietrich route chapter 4, fight with Majide).

The compiled script is **Script/cmdbtl/BD12_04.bin.zst**. These references identify the requested encounter. The exact runtime point at which the clock/variables are refreshed has not been traced.

## A focused test for keeping Majide's cape

1. Open the full original GameData folder in **Credna's Creation Kit** (or FW Hacking Suite 0.22/0.23).
2. Choose **Events**, then **Variable.bin**.
3. Open the **Majide cape** tab and use **Majide wearing cape rule**. Links resolve by their expected native identifiers/arguments, with the original row numbers shown as references.
4. In that row's **Condition groups**, remove **only** the negated lost-duel token. Retain the received-date requirement. The resulting group is:

```json
["同期_日付_マジーデが漆黒のグウェンを受け取った"]
```

5. Save the project and export to a **separate** mod folder. This changes the rule in Variable.bin; it does not require rewriting dialogue or the compiled duel script.
6. Test before and after the encounter with a source/save backup. Existing saves may retain cached or one-shot state; immediate recomputation is not established.

This is a proposed in-game test supported by the stored conditions. It has passed binary round-trip/preservation checks, not an in-game execution test. Leaving Dietrich's paired rule unchanged can permit both characters to retain their caped appearances; that choice is deliberate and is not silently changed by the editor.

## What the first event editor can edit

The **Events** module supports 13 version-1.00 files:

- `Variable.bin`, `Variable_P0.bin`, `Variable_P1.bin`: initial/minimum/maximum values, stored labels, update/change codes, nested condition groups, date/time values and result codes.
- `Timeline_Com.bin`, `Timeline_Part0_Ism.bin`, `Timeline_Part1_Dit.bin`, `Timeline_Part1_Kai.bin`, `Timeline_Part1_Led.bin`, `Timeline_Part1_Seo.bin`, `Timeline_Part2.bin`, `Timeline_Part3_Ism.bin`: ordered event rows with type codes, command arguments, conditions, interval flags, dates, destinations, locators and message-key references.
- `Chapter.bin`: chapter/route codes and flag permissions.
- `Situation.bin`: condition groups, dates, locations and accompanying-group references.

These contain **4,631 native rows and 72,545 field values**. Existing variable names, timeline hash keys, collection/row headers, row counts and native order stay fixed. Copy/paste affects editable values only; reset can restore one row or the selected table. The editor does not insert/delete/reorder native events in this first version. Type codes and condition grouping are preserved without inventing an engine simulator or complete command enum.

Projects retain edits across all sources and other suite modules. Exports rebuild registered relocations/string pointers and preserve original/opaque data. Original source files are never overwritten. English explanations are display-only; raw Japanese identifiers stay intact. Editing a message-key argument chooses a reference, not the contents of a dialogue message.

## Compiled scripts: inspection is separate

All **183 supplied Script/*.bin.zst files** have a validated `ASF\0` wrapper. Its header contains a payload offset, payload length and fixed-size import-path slots. In the supplied files the payload starts at **0x2010**; that value is an offset, **not a script version or string-pool location**.

The compiled payload appears consistent with serialized AngelScript data. It is not plaintext script source, and older Fire Emblem CMB tools do not directly accept this ASF wrapper. The editor shows wrapper metadata, imported scripts and printable ASCII identifier runs **read-only**. Runs may include serialization markers; they are not a disassembly, function declarations or proof that particular calls execute.

There is no compiled-bytecode assembler, instruction insertion/deletion, unsafe byte patcher, script export or dialogue-text writer in this release. A later compiled-script editor will need verified instruction/constant/function decoding and rebuild validation. The current event editor edits the verified data-driven rules and timelines directly, including the cape behavior described above.


## Update for version 0.23

The compiled-script limitations above describe 0.22. Version 0.23 now parses the complete supplied ASF payloads and provides a limited instruction editor with validated string/literal edits, conditional inversion, compatible call replacement and compressed script export. See [SCRIPT-EDITOR.md](SCRIPT-EDITOR.md). It still does not recover original source or insert/delete instructions/functions. The cape chain findings and their runtime-verification limits are unchanged.
