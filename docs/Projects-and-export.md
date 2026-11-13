# Projects and export

## Save a project

**Save project…** writes your edits to a JSON project. It does not package the original game data. Projects identify their original sources using fingerprints: keep those sources unchanged and available when reopening a project.

**Open last project** restores the last saved/opened project and its remembered source paths. When moving to another computer, open the matching original data, load the project, then save it again to remember the new paths.

## Export a mod

Choose **Export mod…** and select a separate output folder. The exporter validates supported edits and writes the edited files in the output layout required by the mod, while protecting the loaded originals. Replacing files owned by an earlier editor export does not create backups; unrelated files are refused. Keep any backups you want yourself. Existing backup files are left alone.

Keep the source data, project and mod output separate. A project is the editable record of your work; an exported mod is the result you test with your own game setup. Exporting does not test gameplay, events or save compatibility.

## New records and references

Creation controls are available for characters, classes, items and learning lists/entries. Other modules edit their existing supported records. Original identities and slots stay fixed.

Removal controls apply to supported newly created records. Explicit references in loaded data can block removal. Indirect references and unopened scripts may not be detected, so reference checks do not establish complete integration.

**Reset entry** or module-specific reset controls restore the selected values from the loaded source. Saving or exporting never rewrites the application’s source-code files.

[Guide home](Home.md)
