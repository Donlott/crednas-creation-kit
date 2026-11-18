# Buyable battalions

**Experimental. Supports the verified, unmodified v1.00 executable; in-game testing is still required.**

Choose **Tools → Buyable battalions…** to add direct battalion purchases to **Dagsion’s item shop on Theodora’s Part I route**, from chapter 4 after the normal barracks unlock. Buying sends the battalion to the barracks. It does not create a usable voucher or require a quest.

The original supported tables provide **99 combat battalions**. The catalog reads their English names, gambits, troop counts, command requirements and stored prices from your loaded tables. Civilian crowds, the empty battalion and event-only placeholders without combat definitions are excluded. Rare and story-associated combat battalions are included; use availability and prices to choose your mod’s balance.

## Configure and export

1. Choose **Open data…** and select your extracted game folder or its **GameData** folder. The tool automatically loads missing `Item.bin`, `Legion.bin` and `Skill.bin` tables, preserving existing edits.
2. Open **Tools → Buyable battalions…** and select **Enable direct battalion sales**.
3. Select the original `exefs/main` and English `Item` message bank. Keep the English `Legion` and `Skill` banks beside `Item`. The same verified executable used for Buyable mounts is required.
4. Search by battalion, gambit or stored identifier. Select an offer, set **Sell this battalion**, its gold price and **Per chapter** limit, then choose **Set offer**. **Apply** also commits the selected row’s pending settings.
5. Save the project and export the complete mod to a separate folder. Enable the exported RomFS files and ExeFS patch together, then restart the game.

Prices default to the battalion’s stored price in your current Legion table. Each offer accepts **1–65,535 gold**. **Reset prices** retains availability and stock settings.

## Availability and stock

- Clear **Sell this battalion** to hide an offer. Already-owned battalions remain owned.
- **Per chapter = 0** means unlimited purchases. **1–127** sets that battalion’s stock cap and normal chapter replenishment amount. Unused stock does not accumulate above the cap.
- Limits apply separately to each battalion definition. Multiple copies are allowed when there is room in the barracks.
- A full barracks refuses delivery without replacing another battalion. Failed delivery reports failure to the normal shop accounting path, so the purchase does not charge gold or consume stock.

The patch preserves the normal barracks unlock, assignment rules, command requirements, recruitment activities and battalion definitions. It does not advance time, assign a battalion automatically or unlock the barracks early. The command value shown in the catalog is the table’s stored requirement.

Settings persist in the project. Re-export and restart after changing them. Existing campaigns retain their saved shop purchase counters; changing a limit does not erase those counters or force an immediate refill. Check replenishment at the next normal chapter transition.

## Together with Buyable mounts

Both tools can be enabled in the same project. Select the **same original executable and Item message bank** for both. CCK composes their additions into one item table, one English Item bank and one compatible IPS32 patch. Do not combine separate independently exported vendor patches by overwriting their shared files.

Each option can be disabled independently. Re-exporting removes that option’s generated offers and code while retaining the other option and your ordinary edits. Original extracted files are never rewritten and no automatic backup files are created.

## Implementation and verification

The native helper uses the game’s existing battalion-grant function and its 300-slot barracks pool. It checks for a free slot before calling the native function, because the native full-pool path can replace an existing entry. It verifies the returned slot and delivered battalion before reporting success to shop accounting. Purchases initialize the same battalion record shape used by the native recruitment result; they do not invent a separate ownership system.

The CCK-authored helper occupies verified executable padding after the existing mount helper. The lookup table is generated from exported item indexes and the loaded Legion indexes. When both options are enabled, unmatched purchases chain through the mount helper, and ordinary items retain their native delivery path. Both maximum-size tables fit without overlapping each other or the read-only segment.

Regression checks cover catalog filtering, settings validation, project reopening, source preservation, combined exports, independent disabling, stock fields, full-pool refusal and the helper’s calling convention. No game binaries, item tables, battalion tables or message banks are distributed with CCK. These checks do not replace a gameplay test of buying, assigning, saving/reloading and chapter replenishment.
