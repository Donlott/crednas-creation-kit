# Buyable mounts

**Experimental: supports the specifically verified executable. Gameplay has not yet been verified.**

**Tools → Buyable mounts…** adds direct mount sales to Dagsion’s item shop for Cai’s Part I campaign, from chapter 5 after the stable unlock. The original supported data provides **22 mount types and 41 skill variants**: horses, Ornius types, flying mounts, war elephants, named unique mounts and their related forms. Engine default/no-mount placeholders with empty trait lists are excluded.

Every skill pair reachable by a saved mount seed receives its own shop entry. The catalog shows the mount, first skill, upgraded skill, price and whether the mount is unique. Skills become available at the normal bond milestones; purchasing does not grant bond levels or bypass riding/class requirements. Wild captures and existing mounts keep their normal behavior.

## Configure and export

1. Use **Open data…** to choose your extracted game folder or its **GameData** folder. You do not need to open individual tables: CCK finds the item, class and skill files automatically. If the session contains only some of them, opening this tool loads the missing tables without replacing existing edits. If a file is actually missing or unreadable, the error identifies its name and the folder checked.
2. Open **Tools → Buyable mounts…** and select **Enable direct mount sales**.
3. Select your original `exefs/main` and English `Item` message bank. Keep the English `Ride` and `Skill` message banks beside it. Only the specifically verified, unmodified executable is accepted.
4. Refresh the catalog if needed. Search for a mount or skill, select a row, enter its gold price and choose **Set price**. **Apply** also keeps the currently selected row’s pending price. **Reset prices** restores catalog defaults.
5. Apply, save the project and export to a separate mod folder. Enable the entire exported mod in your setup, including its ExeFS patch, and restart the game.

Defaults are editable starting prices for this mod. They use 1,000 gold times the mount’s stored value, with a 3× premium for the recognized Move/Dash skills and 4× for Canto/Flying Canto, capped at 65,535 gold. The ordinary horse therefore starts at **1,000 gold for Dodge** and **3,000 gold for Move**. Each variant’s price is independently editable.

The catalog reads names, skills and reachable variants from your current source tables and English banks. No mount tables, names banks or executable are distributed with CCK. During export CCK adds item definitions and shop rows, appends their English names/descriptions to your item bank and generates a small IPS32 patch. Existing table edits and message indexes are retained. These generated entries are export-time overlays, rather than manual item-table edits. Original files are never rewritten.

## Disable or reopen

Clear the checkbox, apply, and re-export to the same output folder. CCK restores the normal exported item table and removes its generated message/ExeFS outputs only if their fingerprints still match the previous export. Restart the game. Already-purchased mounts remain ordinary native mounts and are not removed.

Projects remember per-variant prices and source fingerprints. Older one/two-horse projects retain their horse prices when migrated to the full catalog. An old single-price project assigns that price to Dodge and starts Move at three times that price (at least 3,000 gold, capped at 65,535). If source paths move, update the project’s paths or reconfigure the option. If skill edits remove a priced variant, reset catalog prices or restore the matching source data before exporting.

## Storage, unique mounts and testing

- A free stable slot is required. The hook checks all 200 native storage records before granting a mount, preventing the game’s usual full-pool replacement behavior.
- A unique named mount is refused if the pool already contains that RID or the native unique-mount lookup reports it as present. Purchases explicitly disable the grant routine’s automatic conversion to a related form. Related non-unique forms have their own catalog entries. Failed delivery or a duplicate unique mount means no gold deduction.
- The shop retains its normal funds, quantity, stock and selection checks. Existing shop pricing modifiers may affect the displayed price. There is no custom “stable full / unique already owned” purchase message yet.
- Each offer uses a fixed saved seed, which determines the advertised skill pair and other properties derived from that seed. Editing a skill list changes the reachable pairs; the exporter does not rewrite those lists to invent combinations.
- Use all generated files together. Removing only the ExeFS patch leaves placeholder inventory items for sale. Do not combine another executable patch with overlapping hooks or code-cave addresses.

Validation and CPU emulation cover every catalog entry, funds checks, failed grants, storage limits, duplicate unique mounts, register preservation and the native skill selector. They do **not** establish runtime mount behavior or save compatibility. Test purchases from each family, their prices, normal bond skill unlocks, save/reload, repeated purchases, insufficient funds, full storage, unique duplicates and disabling the patch.

## Maintainer details

The supported main build ID is `db93b0125f4850601d61c3edde012f8eb2ecfe77000000000000000000000000`; SHA-256 is `616e7d906936ea4c2d908d0553cf69779e60242d769c40722267ee8bcb98e79a`. Both are checked before enabling/exporting. Other executables are refused. English bank fingerprints also guard project reuse and export.

All helper instructions are CCK-authored; assembly source is in `mount_native.py`. Keystone is only used for development, with no runtime assembler/decoder dependency. The hooks are at relative addresses `0x189ea38` (purchase destination load) and `0x189ec80` (inventory-delivery call). Destination code begins at `0x1a45300`, delivery at `0x1a45380`, and the lookup table at `0x1a45500`, within the verified text page’s zero padding. Each eight-byte table row contains the exported item index, RID index, saved seed and unique flag. The table supports up to 256 offers and is checked against the page boundary. The loader patches the decompressed page-aligned image with a `0x100` NSO header; IPS32 offsets account for that header and the build-ID filename uses uppercase for Eden’s case-sensitive lookup.

Both hooks search the generated table. Ordinary purchases replay the displaced load or tail-call the original inventory-add function at `0x8a25c0`. Mount purchases use the convoy delivery branch regardless of unit selection. Delivery checks free storage and unique ownership, initializes a native mount instance with an empty inline string and the selected RID/seed, then calls `0x9484a0` with conversion disabled. Only result 2 (new insertion) is accepted. Failure returns a negative delivery index, which causes the original shop loop to skip both the gold deduction and stock consumption. Callee-saved registers and stack alignment are preserved; the destination hook also preserves its scratch registers and NZCV.

`mount_skills.py` reproduces the deterministic selector roll from the saved byte at mount offset 1. The native selector at `0x9372c0` chooses `roll % list_length`. The builder at `0x938134..0x938240` maps first-stage skills to bond levels 3/4 and upgraded skills to level 5. Native reference tests cover all 256 seeds at all three levels for one-, two- and three-entry lists, plus the actual builder’s list copying. `mount_catalog.py` enumerates reachable first/upgrade pairs and generates stable offer IDs from the RID and skill references. Item indexes are read back from the final exported table, so earlier user-created records do not redirect purchases to the wrong mount.

Negative quest-gold rewards are deliberately not used: the supported build reads that field as unsigned 16-bit data. Serializing `-1000` would award 64,536 gold instead of charging 1,000.

Optional tests use private inputs through `FW_GAME_DATA`, `FW_MESSAGES`, `FW_MOUNTS_MAIN` and `FW_MOUNTS_MEMORY`. None of those inputs belong in the repository. CPU tests use optional Unicorn with grant APIs mocked; the optional native-callsite test runs the actual payment loop from a private decompressed image. These checks do not replace gameplay testing.

[Guide home](Home.md)
