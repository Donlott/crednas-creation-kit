# Shop & Loot

Choose **Shop & Loot**, then select the source and section. Browse supported shop, lottery, loot and value rows using their readable labels and references.

Edit item assignments, quantities, stock, prices, conditions or weights where those fields are exposed by the selected schema. Copy/paste and reset controls apply to compatible rows.

## Add items to a shop

In the **Shops** section, choose an existing shop and click **Add entry** for a blank inventory row, or **Duplicate entry** to copy the selected row’s current values. You can add rows to an empty shop too. Choose the item and set its price, stock, conditions and any exchange requirements. Exchange item and quantity lists must have matching lengths. Items created in CCK appear in the item picker.

New rows append after the original inventory, preserving its existing order. **Undo last addition** removes the most recently added row from the selected shop. **Reset entry** restores a row’s values; **Reset table** also discards that shop’s additions. Other shops and item definitions remain separate.

Save a project to retain your new rows, then export the mod normally. Projects with added shop rows require a CCK build supporting shop expansion. Older projects still open. This adds inventory entries to existing shops; it does not create new shop locations, lottery rows or value tiers. Availability and restocking still follow the game’s rules.

Shop-related rows share their source owner with the corresponding [Items](Items.md) data. Saving and exporting keep those edits together rather than producing competing versions of the same source.

Reference links open supported item definitions or other connected entries. The editor does not simulate availability, restocking, drop rolls or the final probability implied by every weight/default code. Treat unknown numeric codes and special values literally.

A newly defined item becomes obtainable only after the appropriate assignments and game rules are set up. Adding an item definition alone does not add it to a shop or loot list.

[Guide home](Home.md)
