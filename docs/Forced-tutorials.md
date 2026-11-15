# Forced tutorials and progression checks

Open your original game data and choose **Tools → Forced tutorials…**. The catalog contains **28 sequence groups with 39 route-specific entries**. Filter by route or search by name/list number, then select an entry to see its behavior and dependencies.

The goal is to remove compulsory guidance while keeping the normal timeline and access to the systems it introduces. **All 39 entries currently have experimental recipes; none are gameplay-verified.** They can be selected for testing. The lure/capture option deliberately omits the tutorial animal reward.

**A guidance bypass does not necessarily complete the underlying quest or battle.** The hair-clip and first dread-warrior options shorten their introductions and reporting scenes; their challenges remain required. The field and village-performance options let you do the activities voluntarily, with their quests and rewards remaining pending. Each option describes its scope before you apply it.

## Use and status

Select **Bypass forced guidance**, then press **Apply**. Save a project or export a separate mod. Original extracted files remain untouched.

- **Off · testable / On · experimental:** a reviewed recipe is available or enabled.
- **Not implemented:** no executable bypass exists yet; the detail panel explains the missing work.
- **Source / edit conflict:** required originals are missing, differ from supported version 1.00, or have overlapping custom edits.
- **Migration needed / Recipe needs repair:** apply to complete or repair the recipe, or uncheck to restore its original scene and commands.

## Available sequences

| Sequence | Routes | Preserved behavior |
| --- | --- | --- |
| Arena guidance | All four | Training access; normal voluntary training remains available. The tutorial stipend and matching compulsory fee are both omitted. |
| Certification exams | All four | Original entry-level permit once; certification feature unlocked and class-change prohibition lifted. No compulsory class selection or exam purchase. |
| Vandahl Trading Company visit | All four | Company unlock, trade-information flag and read-gated access; no forced purchase. Subsequent exploration remains a separate sequence. |
| World-map exploration introduction | Cai, Dietrich, Leda | Omit the compulsory first Explore roll. Keep native unlock notifications, route-reveal cues, dialogue/read history and scheduled progression. No random loot or action cost is simulated. |
| Quest-board and inn orientation | Cai | Quest journal, notice-board access and the original 1,500 gold grant once; the two scheduled stages retain separate completion markers. |
| Hair clip / first delivery — guidance only | Cai | Native quest acceptance/report dialogs and renown journal; actual battles, mine, pickup and travel remain required. Separate stage markers protect return read checks. |
| Guzran recruitment lesson | Cai | Original food gift once; normal next-stage request; no forced negotiation or automatic recruitment. |
| Initial stable visit | Cai | Stable access; the later capture sequence retains its native behavior. |
| Lure / capture lesson — no animal reward | Cai | Two sample bait, lure unlock, route reveals, dialogue, travel and native dates. No tutorial animal is created. The following feeding skip is enabled with it. |
| Feeding visit after capture | Cai | Stable access and any existing animals; no forced feeding transaction. Required by the no-animal capture skip. |
| Field lesson — optional activity | Cai | Original vegetable quest and sample seeds, farming unlock, travel and scheduled next-day boundary. Planting and accelerated tutorial progress are omitted; no field or crops are invented. Complete the delivery voluntarily for its rewards. |
| Answerer's Cry — keep encounter | Dietrich | Renown journal and detection unlock notice; original enemy group placed at the same bridge. Detection interaction is omitted; actual encounter, travel and rewards remain native. |
| Yang Jie recruitment lesson | Dietrich | Original food gift once; normal next-stage request; no forced negotiation or automatic recruitment. |
| Follow-cat / combat-art strengthening guidance | Dietrich | Strengthening access and the original 40 magic echo shards once; no forced upgrade or material spending. |
| Teaching-secrets guidance | Dietrich | Teaching access and the original 50 magic echo shards once; normal prerequisites and costs remain. |
| First dread warrior — guidance only | Dietrich | Native acceptance/report dialogs and arranger introduction; actual mine, battle and return remain required. Native quest reporting retains its skill, money and renown rewards. |
| First battalion assignment / wolf practice | Theodora | Barracks access and the original novice mercenary battalion. The original first-visit flag prevents duplicate battalion grants. No forced assignment or practice battle. |
| Battalion dispatch lesson | Theodora | Original novice-priest battalion gift and fixed five hishibana supplies; exploration/dispatch unlock notices, route reveals, dialogue and schedule fields. The supply quest still uses native delivery/reporting. |
| First battalion recruitment | Theodora | Fixed basic-warrior battalion through the native grant command; recruitment unlock notice, town/route reveals, dialogue and schedule fields. No compulsory recruitment operation or assignment. |
| Catania recruitment introduction | Leda | Original rose gift once; normal next-stage request; no automatic recruitment. |
| Battalion-transfer introduction | Theodora | Introduction completion checks; the ordinary tournament/free-action objective stays active. |
| Centurio introduction | Cai | Practice access and read-gated NPC placements; the qualifier/free-action objective stays active. |
| Supplies/remittance introduction | Theodora | Original native quest acceptance dialog, remittance access and quest journal; subsequent supply gameplay stays native. |
| Quest/scouting introduction | Theodora | Original quest/report and next-quest dialogs in order, renown journal, and Salamis food once; the second qualifier remains active. |
| First tavern lesson | Leda | Original native quest acceptance, completion, report/reward and next-quest calls; tavern/hub performance access and journal unlocks; no compulsory walk or instructed performance. |
| First village performance — optional activity | Leda | Village/route reveals, native dialogue and exploration unlock. Performance is voluntary; its quest and native income/rewards are not auto-completed or granted. |
| Prologue inspection | Prologue, chapter 2 | Original Salamander +3 and sandworm-meat grants once, the native conditional equip request for Kouka, and the inspection-completion flag. Subsequent preparation unlock and warp/story events stay native. |
| Drinks introduction | Leda | Drink facility access and the normal vendor placement; its original quest prerequisite remains. No timeline advance or forced purchase. |

The recipes preserve the identified system unlocks. They do not invent class changes, recruitment, affinity, training results or paid activity outcomes. Normal costs and prerequisites still apply to voluntary activities. Original recruitment-lesson food, Catania’s rose and strengthening/teaching shard gifts are retained once through the existing item-grant helpers. These grants do not automatically recruit a character, learn a skill or spend the materials. The prologue equipment request follows the original ownership check; its success remains subject to the game’s inventory rules.

## Keeping unlocks available

Some normal vendors and NPCs appear only after a specific introductory conversation is recorded as read. Simply removing that conversation can hide them. The editor adds narrow compatibility checks that accept either the game's original read state or a persistent completion marker written by that sequence's bypass. Unrelated conversations retain their original behavior, and two-conversation conditions still require both conditions.

**Turning a bypass off restores its scene, but keeps these access checks in the project and export.** That lets saves which skipped the introduction retain access. Keep exporting from that project while using those saves. Removing the mod entirely or exporting a separate clean project removes the compatibility checks; this tool does not rewrite the game's original read-history records in a save.

Markers are written only when the selected sequence is reached. Enabling an option does not unlock its facility at the start of the campaign. The two city-orientation stages have separate markers so the first cannot prematurely complete the inn stage. Transfer advice, Centurio and the area-triggered drinks introduction do not skip their surrounding free-action objectives.

## Quest dialogs in the new introductions

The remittance, quest/scouting and tavern bypasses keep the original native quest calls and their arguments. **Quest confirmation and reward screens still appear.** They are needed to retain acceptance, reporting, rewards and deadlines through the game's own quest system. The bypasses omit the staged explanations, camera scenes and guided walks.

The tavern recipe runs the original first-quest acceptance, quest-completion request, report/reward dialog and village-quest acceptance in order. It opens tavern/hub performance access and the journals without unlocking the later theatre. Its later, reused tavern callback remains unchanged. Optional performance gains are not invented. The native schedule is retained, but time normally consumed inside the instructed activity still needs in-game checking.

The hair-clip and first dread-warrior options retain their native acceptance and return-report calls as separate stages. They do not call a quest-completion API, grant quest items or mark a battle won. Their original world-map/dungeon/quest-result events remain. The return conversation's access marker is written only on reaching that return stage. These options do not remove the whole journey or make the challenges optional.

Each quest step and lesson gift has a separate one-time marker. Completed steps are retained if a later step is resumed; repeated entry does not re-run already completed reward/report calls. These markers do not backfill old saves which already passed a prior bypass.

## Exploration command skips

The three exploration options remove exactly the original compulsory Explore command. They retain every other world-map cue, including dialogue, route reveals, unlock notifications and native tutorial/read-state handling. Leda’s exploration unlock is introduced in the preceding village-performance event, which this option leaves unchanged.

These options skip the first roll itself. They do not simulate random materials, extra discoveries, command travel or an activity-time charge. Short dialogue/tutorial screens still appear, and ordinary exploration remains available. Native event dates, conditions, interval flags and subsequent stages are unchanged. This avoids replacing a world-map event with a different event type or inventing an exploration result.

The edits are stored as normal timeline argument changes and work without loading compiled scripts. Unchecking restores the original commands. Conflicting manual edits are shown as a source/edit conflict rather than overwritten; unrelated event editing remains available.

## Fixed battalion tutorial results

Theodora's dispatch bypass replaces the compulsory dispatch command with the existing native item-grant command for its fixed five hishibana supplies. The original novice-priest battalion gift remains once in the same event. The supply quest is not marked complete: normal delivery, reporting and rewards remain under the game's quest system.

Her recruitment bypass replaces the compulsory recruitment command with the existing native battalion-grant command for its fixed basic-warrior battalion. It remains available for voluntary assignment. Both options remove the associated command-progress cue because there is no longer an active tutorial operation to advance.

These options retain every other cue, including unlock notices, location/route reveals, dialogue and read history. Native event types, dates, conditions and subsequent stages are unchanged, including the later world-map exit and region-restriction reset. They do not simulate operation fees, experience, active commands, assignment state or activity duration. This preserves scheduling data, but the skipped operation's effect on the clock still needs gameplay testing. Normal dispatch and recruitment remain available.

## Optional activities and retained encounters

The field option omits compulsory planting and the later tutorial command-progress cue. Original quest acceptance and sample-seed grants stay in place; seeds are not spent on a forced operation. Farming remains unlocked. No persistent field, mature crop or harvest is created automatically. The vegetable quest remains pending until you grow and deliver its requirements normally. Native next-day dates, travel cues and the free-action boundary stay in place.

The village-performance option removes only its compulsory performance interaction. Village/route reveals, dialogue and the exploration unlock notice remain. The accepted village-performance quest remains available for voluntary completion and reporting. No performance income, item, renown or activity-time outcome is invented. The next Explore lesson has its own checkbox.

The Answerer's Cry option shortens the weapon introduction and replaces forced detection with the game's existing faction-placement command for the exact original tutorial enemy group at the same bridge. It keeps that encounter's native definition and rewards. It does not auto-win a fight or fabricate a detection charge/use record. Route travel and subsequent events remain native.

Multi-stage command edits are limited to named, fingerprinted rows. If only part of a recipe is present, the menu offers repair or restoration. A mixed script/command recipe cannot export with its script completion part missing. Conflicting custom edits are not overwritten.

## Lure/capture without the tutorial animal

This option removes the forced lure, its later command-progress cue and forced capture. **You do not receive the tutorial Ornius.** No animal or pending lure operation is created. The original two sample bait, lure unlock notice, route reveals, dialogue, travel, March 15 noon event and later schedule definitions remain. Unused bait is retained rather than consumed by a forced operation. Capture outcomes, experience and operation-time costs are not simulated.

The option automatically enables **Feeding the captured animal**, so the subsequent lesson cannot demand an animal you did not capture. Its script advances that scheduled stage without opening the instructed stable menu. Stable access and normal voluntary luring, capture and feeding remain available. Existing animals are untouched; ordinary capture probabilities and escape rules are not changed, and animal-related quests are not auto-completed.

Turning the feeding skip off in the menu also turns the dependent capture skip off; press **Apply** to restore both. Turning only the capture skip off leaves the feeding skip selected, so review it separately if you want the original feeding lesson too. Saved projects retain the required script and read-access guard. An incomplete capture edit, missing feeding recipe or missing access guard must be repaired or restored before export. The capture option needs the original feeding script alongside the timeline data.

Apply before the capture sequence and keep the feeding skip enabled through the return to the stable. Restoring original commands after a save has already skipped capture cannot retroactively give that save an animal.

The retained dialogue can still refer to luring or capturing an animal. This option removes the operations and animal reward; it does not rewrite story text or eliminate every travel/camera cue. A variant that automatically grants the original animal would require further investigation of the native capture-result handler.

## Remaining native work

Full quest/battle auto-completion for the hair-clip and dread-warrior chains, automatic field creation/harvesting, and automatic village-performance results are outside the implemented guidance-only options. No blanket route-completion flags or guessed quest results are used.

## Scheduling, migration and limits

Native event types, dates, conditions, objectives and interval definitions remain in place. Certification adds an automatic completion hook to its existing spawn initializer. Exploration removes only the compulsory command from its native world-map argument list; the two fixed-result battalion lessons replace the compulsory operation with its reviewed native grant and remove its progress cue. Turning these options off restores the original arguments. Other timeline fields remain unchanged. Scheduled lessons request the game's normal next-stage handling; ordinary free-action introductions do not. This preserves the scheduling data but does not prove implicit activity-time behavior inside native facility code.

Earlier shortcuts replaced scheduled visits with party-join or flag events. Export rejects those shortcuts until they are migrated through this menu or restored. Migration retains unrelated edits such as custom clock fields. Older script recipes missing access checks also need **Apply** before export. This updates the mod for subsequent runs of the sequence; it cannot reconstruct markers or backfill omitted gifts in a save that already passed an older bypass.

The script writer uses existing native APIs, rebuilds string references, removes obsolete cleanup metadata and checks the result by parsing it again. Tests exercise stack use, branches, ownership cleanup, read-condition truth tables, reward guards, source checks, project round-trips and exports. Synthetic grant and read-guard programs have also been loaded and executed in AngelScript 2.35.1, including repeated grants, fallback flag helpers, two-argument read conditions and native quest-call suspension/resumption inside event context. These checks do not run the game's scheduler or establish that no softlock is possible.

When gameplay testing becomes possible, start before a selected sequence and check the clock, next objective, movement restrictions, later events and facility access. This is a data mod, not a save editor: changing an option cannot undo effects already stored in a save.

Sources with active completion programs are protected from ordinary script editing. Scene programs can be turned off here. The shared compatibility helper deliberately remains installed; inspect/edit its original version only in a separate clean project.

[Guide home](Home.md)
