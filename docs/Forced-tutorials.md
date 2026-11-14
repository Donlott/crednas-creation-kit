# Forced tutorials and progression checks

Open your original game data and choose **Tools → Forced tutorials…**. The catalog contains **28 sequence groups with 39 route-specific entries**. Filter by route or search by name/list number, then select an entry to see its behavior and dependencies.

The goal is to remove compulsory guidance while keeping the normal timeline and access to the systems it introduces. **20 entries currently have experimental recipes; none are gameplay-verified.** Entries whose quest, reward or native world-map effects remain unresolved cannot be enabled.

## Use and status

Select **Bypass forced guidance**, then press **Apply**. Save a project or export a separate mod. Original extracted files remain untouched.

- **Off · testable / On · experimental:** a reviewed recipe is available or enabled.
- **Needs tracing:** unresolved effects are described; the option is unavailable.
- **Source / edit conflict:** required originals are missing, differ from supported version 1.00, or have overlapping custom edits.
- **Migration needed / Unlock checks needed:** apply to repair an older project, or uncheck to restore its original scene.

## Available sequences

| Sequence | Routes | Preserved behavior |
| --- | --- | --- |
| Arena guidance | All four | Training access; normal voluntary training remains available. The tutorial stipend and matching compulsory fee are both omitted. |
| Vandahl Trading Company visit | All four | Company unlock, trade-information flag and read-gated access; no forced purchase. Subsequent exploration remains a separate sequence. |
| Quest-board and inn orientation | Cai | Quest journal and the original 1,500 gold grant once; the two scheduled stages retain separate completion markers. |
| Guzran recruitment lesson | Cai | Normal next-stage request; no forced negotiation or automatic recruitment. |
| Initial stable visit | Cai | Stable access; the later capture sequence retains its native behavior. |
| Feeding visit after capture | Cai | Stable access and the captured animal; no forced feeding transaction. |
| Yang Jie recruitment lesson | Dietrich | Normal next-stage request; no forced negotiation or automatic recruitment. |
| Follow-cat / combat-art strengthening guidance | Dietrich | Strengthening access; no forced upgrade or material spending. |
| Teaching-secrets guidance | Dietrich | Teaching access with normal prerequisites and costs. |
| First battalion assignment / wolf practice | Theodora | Barracks access and the original novice mercenary battalion. The original first-visit flag prevents duplicate battalion grants. No forced assignment or practice battle. |
| Catania recruitment introduction | Leda | Normal next-stage request; no automatic recruitment. |
| Battalion-transfer introduction | Theodora | Introduction completion checks; the ordinary tournament/free-action objective stays active. |
| Centurio introduction | Cai | Practice access and read-gated NPC placements; the qualifier/free-action objective stays active. |
| Drinks introduction | Leda | Drink facility access and the normal vendor placement; its original quest prerequisite remains. No timeline advance or forced purchase. |

The recipes preserve the identified system unlocks. They do not invent class changes, recruitment, affinity, training results or paid activity outcomes. Normal costs and prerequisites still apply to voluntary activities. Recruitment-lesson gifts and strengthening/teaching consumable gifts are not granted by these bypasses; they are separate from the system unlocks. These distinctions are visible in the sequence descriptions.

## Keeping unlocks available

Some normal vendors and NPCs appear only after a specific introductory conversation is recorded as read. Simply removing that conversation can hide them. The editor adds narrow compatibility checks that accept either the game's original read state or a persistent completion marker written by that sequence's bypass. Unrelated conversations retain their original behavior, and two-conversation conditions still require both conditions.

**Turning a bypass off restores its scene, but keeps these access checks in the project and export.** That lets saves which skipped the introduction retain access. Keep exporting from that project while using those saves. Removing the mod entirely or exporting a separate clean project removes the compatibility checks; this tool does not rewrite the game's original read-history records in a save.

Markers are written only when the selected sequence is reached. Enabling an option does not unlock its facility at the start of the campaign. The two city-orientation stages have separate markers so the first cannot prematurely complete the inn stage. Transfer advice, Centurio and the area-triggered drinks introduction do not skip their surrounding free-action objectives.

## Remaining native sequences

Certification remains unavailable because its permit grant and class-result path need to be retained correctly. Hair-clip and dread-warrior quest chains, animal capture, farming, world-map exploration, battalion dispatch/recruitment, performance quests, prologue investigation and quest/reporting introductions also retain their original behavior. Their unresolved dependencies are listed in the menu. No blanket route-completion flags or guessed quest results are used.

## Scheduling, migration and limits

All timeline table bytes remain unchanged by the current recipes. Native event types, dates, conditions, objectives and interval definitions remain in place. Scheduled lessons request the game's normal next-stage handling; ordinary free-action introductions do not. This preserves the scheduling data but does not prove implicit activity-time behavior inside native facility code.

Earlier shortcuts replaced scheduled visits with party-join or flag events. Export rejects those shortcuts until they are migrated through this menu or restored. Migration retains unrelated edits such as custom clock fields. Older script recipes missing access checks also need **Apply** before export. This updates the mod for subsequent runs of the sequence; it cannot reconstruct markers in a save that already passed an older bypass.

The script writer uses existing native APIs, rebuilds string references, removes obsolete cleanup metadata and checks the result by parsing it again. Tests exercise stack use, branches, ownership cleanup, read-condition truth tables, reward guards, source checks, project round-trips and exports. They do not run the game's scheduler or establish that no softlock is possible.

When gameplay testing becomes possible, start before a selected sequence and check the clock, next objective, movement restrictions, later events and facility access. This is a data mod, not a save editor: changing an option cannot undo effects already stored in a save.

Sources with active completion programs are protected from ordinary script editing. Scene programs can be turned off here. The shared compatibility helper deliberately remains installed; inspect/edit its original version only in a separate clean project.

[Guide home](Home.md)
