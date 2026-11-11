"""Character creation-time identity controls and current PID reference navigation."""
from tkinter import ttk,simpledialog
from person_index import uses


def tools(app,body,record):
    bar=ttk.Frame(body);bar.grid(row=0,column=0,columnspan=4,sticky='ew',pady=(0,6))
    def create(duplicate=False,remove=False):
        if not app.apply(True):return
        doc=app.doc
        try:
            if remove:
                incoming=[u for u in uses(record.pid,app.documents) if not (u.source==doc.filename and u.record==record.pid)]
                if incoming:app.error(f'This character has {len(incoming)} current references in loaded editable fields. Clear or replace them first; see Used by.');return
                doc.remove_character(record.pid);target=next((r.pid for r in doc.records if doc.value(r,doc.by_offset[0x30])),doc.records[0].pid)
            else:
                stem=record.pid+'_Copy' if duplicate else 'PID_Custom';key=stem;number=2
                while key in doc.by_pid or key in doc.labels:key=f'{stem}_{number}';number+=1
                key=simpledialog.askstring('Duplicate character' if duplicate else 'New character',
                    'Enter a unique PID_ ID. Existing character IDs and serials stay unchanged.',initialvalue=key,parent=app)
                if key is None:return
                free=doc.available_serials()
                serial=simpledialog.askinteger('New character serial',
                    '0 = unnumbered variant/NPC entry (default).\nA nonzero serial must be unused in loaded Person.bin.\nUnused does not guarantee playable-roster support.\nExamples: '+', '.join(map(str,free[:12]))+'\nSerial is fixed after creation; duplicates never inherit an occupied serial.',
                    initialvalue=0,minvalue=0,maxvalue=255,parent=app)
                if serial is None:return
                target=doc.create_character(key,record.pid if duplicate else None,serial=serial).pid
        except Exception as exc:app.error(exc);return
        app.current=None;app.widgets={};app.suggestion_cache.clear();app.clear_previews();app.rebuild_translator()
        app.switch_module('Characters',target);app.notebook.select(0)
        app.status.set('New character removed.' if remove else 'Character created. Reuse existing names/assets and configure deployment or references explicitly, then save/export. Recruitment and roster behavior are unverified.')
    app.character_creation_actions={}
    for label,command in [('New character…',create),('Duplicate character…',lambda:create(True)),('Remove new character',lambda:create(remove=True))]:
        button=ttk.Button(bar,text=label,command=command);button.pack(side='left',padx=(0,5));app.character_creation_actions[label]=button
    if record.pid not in app.doc.new_characters:app.character_creation_actions['Remove new character'].configure(state='disabled')
    ttk.Label(body,text='Experimental. Duplicate copies all current values except the newly chosen serial. Names, assets and support/profile links are reused; no automatic recruitment or story edits.',
              style='Hint.TLabel',wraplength=700).grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,6))


def usage(app,body,record):
    from class_ui import usage as show_usage
    return show_usage(app,body,record,find_uses=uses,kind='character',auto_refresh=False)
