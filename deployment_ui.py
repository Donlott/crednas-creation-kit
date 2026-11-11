"""Deployment files, fixed groups and compact unit/loadout/AI forms."""
from dataclasses import replace
from pathlib import PurePosixPath
import re
from tkinter import ttk
from item_index import reference_ids
from skill_ui import scroll_body

LABELS={0x20:'Character',0x30:'Army (raw)',0x32:'Normal flags (raw)',0x34:'Spawn X',0x35:'Spawn Z',
 0x36:'Deployment X',0x37:'Deployment Z',0x38:'Size (raw)',0x39:'Facing (raw)',0x3a:'Advance (raw)',
 0x3b:'Level',0x40:'Legion soldier',0x50:'Vehicle / mount',0x60:'Trust level',
 0xe0:'AI condition',0xe8:'Condition arguments',0xf0:'AI action',0xf8:'Action arguments',
 0x100:'AI attack',0x108:'Attack arguments',0x110:'AI movement',0x118:'Movement arguments',
 0x120:'Battle evaluation (raw)',0x121:'Action priority',0x122:'Recovery rate A (raw)',
 0x123:'Recovery rate B (raw)',0x124:'Squad number',0x125:'Fierce-attack handling (raw)',
 0x128:'Fierce-attack arguments',0x130:'Fierce-attack forbidden turns (signed raw)',
 0x138:'Movement restriction',0x140:'AI flags (raw)'}
for i,offset in enumerate((0x68,0x80,0x98,0xb0,0xc8),1):
    LABELS[offset]=f'Item {i}';LABELS[offset+0x10]=f'Drop flags {i} (raw)'


def display_field(view,field):return replace(field,name=LABELS[field.offset])


def collection_name(app,record,view=None):
    view=view or app.doc;native=view.names[record.pid]
    if native in app.custom_translations:return app.translator.resolve(native).text
    text=native
    for a,b in [('Reinforcement','Reinforcement'),('Enemy','Enemy'),('Player','Player'),('Ally','Ally'),('Animal','Animal'),('Mummy','Mummy'),('増援','Reinforcement')]:text=text.replace(a,b)
    text=re.sub(r'(?<=[A-Za-z])(?=\d)', ' ', text).replace('_',' / ')
    result=app.translator.resolve(text)
    return text if result.source=='Untranslated' else result.text


def translated(app,raw):
    from supports_ui import translated as resolve
    return resolve(app,raw) if raw else '—'


def row_name(app,row,view):
    table,ordinal=view.row_location[row.pid]
    return f'{collection_name(app,view.tables_by_id[table],view)} · unit {ordinal} · {translated(app,view.value(row,view.by_offset[0x20]))}'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for row in view.rows_by_table[record.pid]:
        values.extend(view.value(row,f) for f in view.fields if f.kind in ('data','string'))
    return ' '.join(values+[translated(app,value) for value in values if value])


def suggestions(app,field):
    view=app.doc;values={view.value(row,field) for row in view.records}
    prefix='PID_' if field.offset==0x20 else 'IID_' if field.offset in (0x68,0x80,0x98,0xb0,0xc8) else None
    if prefix:values.update(reference_ids(app,prefix))
    if field.offset==0x40 and 'Legion' in app.documents:values.update(app.documents['Legion'].by_pid)
    return sorted(values-{''})


def refresh_entries(app):
    if not getattr(app,'deployment_tree',None) or not app.deployment_tree.winfo_exists() or app.current is None:return
    view=app.doc
    for row in view.rows_by_table[app.current.pid]:
        v=lambda offset:view.value(row,view.by_offset[offset])
        values=(row.index,translated(app,v(0x20)),v(0x3b),f'{v(0x34)}, {v(0x35)}',f'{v(0x36)}, {v(0x37)}',v(0x30),v(0x20))
        if app.deployment_tree.exists(row.pid):app.deployment_tree.item(row.pid,values=values)
        else:app.deployment_tree.insert('','end',iid=row.pid,values=values)


def show_entry(app,row):
    app.clear_previews();app.learning_row=row;app.widgets={}
    form=app.deployment_form;selected=form.index('current') if form.tabs() else 0
    for tab in form.tabs():app.nametowidget(tab).destroy()
    for title,fields in [('Unit & position',[f for f in app.doc.fields if f.offset<0x68]),
                         ('Inventory',[f for f in app.doc.fields if 0x68<=f.offset<0xe0]),
                         ('AI',[f for f in app.doc.fields if f.offset>=0xe0])]:
        frame=ttk.Frame(form,padding=6);form.add(frame,text=title);body,bind=scroll_body(frame)
        for i,original in enumerate(fields):
            field=display_field(app.doc,original)
            if field.kind in ('data','string'):app.reference_row(body,i,field,row)
            else:app.numeric_row(body,i,field,row)
        body.columnconfigure(1,weight=1,uniform='deploy');body.columnconfigure(2,weight=1,uniform='deploy');bind()
    form.select(min(selected,2))
    if app.deployment_tree.exists(row.pid):app.deployment_tree.selection_set(row.pid);app.deployment_tree.see(row.pid)


def select_entry(app,event=None):
    selection=app.deployment_tree.selection()
    if not selection:return
    row=app.doc.by_pid[selection[0]]
    if app.learning_row and row.pid==app.learning_row.pid:return
    if not app.apply(True):
        if app.learning_row:app.deployment_tree.selection_set(app.learning_row.pid)
        return
    show_entry(app,row)


def connected(app,parent,record):
    from aid_ui import tree
    view=app.doc
    ttk.Label(parent,text='Direct references from the selected group. Missing records remain raw; event scripts and AI behavior are not evaluated.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    listing=tree(parent,[('unit','Unit',50),('field','Field',190),('name','English / reference',240),('raw','Native ID',210)],height=11);targets=[]
    def refresh():
        if not app.apply(True):return
        targets.clear();listing.delete(*listing.get_children())
        for row in view.rows_by_table[record.pid]:
            for field in view.fields:
                if field.kind not in ('data','string'):continue
                raw=view.value(row,field)
                if not raw:continue
                module='Characters' if raw.startswith('PID_') else 'Items' if raw.startswith('IID_') else 'Skills' if raw.startswith('SID_') else 'Legion' if field.offset==0x40 and raw.startswith('LID_') else None
                owner=next((d for d in app.documents.values() if raw in d.by_pid and d.prefix=={'Characters':'PID_','Items':'IID_','Skills':'SID_','Legion':'LID_'}.get(module)),None)
                listing.insert('','end',iid=str(len(targets)),values=(row.index,LABELS[field.offset],translated(app,raw),raw))
                targets.append((module,owner.filename if owner else None,raw,owner is not None))
    def navigate(event=None):
        if not listing.selection():return
        module,filename,pid,loaded=targets[int(listing.selection()[0])]
        if loaded:app.switch_module(module,pid,source_file=filename)
        else:app.status.set('No editable record is loaded for '+pid)
    tools=ttk.Frame(parent);tools.pack(fill='x',pady=5)
    ttk.Button(tools,text='Refresh references',command=refresh).pack(side='left')
    ttk.Button(tools,text='Open selected record',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    app.deployment_links_tree=listing;app.deployment_links=targets;app.deployment_links_open=navigate;app.deployment_links_refresh=refresh
    refresh()


def show_table(app,record):
    from aid_ui import tree
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.learning_row=None;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(collection_name(app,record));app.details.set(f'{view.filename} · {view.names[record.pid]} · {len(view.rows_by_table[record.pid])} fixed unit slots')
    units=ttk.Frame(app.notebook,padding=6);app.notebook.add(units,text='Units')
    ttk.Label(units,text='X/Z positions are signed bytes. Army, facing, flags and AI codes remain raw; their engine meaning is unverified.',style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=(0,4))
    panes=ttk.Panedwindow(units,orient='vertical');panes.pack(fill='both',expand=True)
    upper=ttk.Frame(panes);lower=ttk.Frame(panes);panes.add(upper,weight=1);panes.add(lower,weight=3)
    app.deployment_tree=tree(upper,[('slot','Slot',45),('name','Character / English',175),('level','Level',45),('spawn','Spawn X,Z',90),('pos','Deploy X,Z',90),('army','Army',45),('pid','Native character ID',230)],height=5)
    app.deployment_tree.bind('<<TreeviewSelect>>',lambda e:select_entry(app,e))
    tools=ttk.Frame(lower);tools.pack(fill='x',pady=4);app.deployment_tools=tools
    form=ttk.Notebook(lower);form.pack(fill='both',expand=True);app.deployment_form=form
    def copy_unit():
        if app.learning_row and app.apply(True):
            app.deployment_clipboard={f.offset:view.value(app.learning_row,f) for f in view.fields}
            app.status.set('Copied unit values; destination group and unit slot stay fixed.')
    def paste_unit():
        if not app.learning_row or app.deployment_clipboard is None or not app.apply(True):return
        before=dict(view.changes)
        try:
            for offset,value in app.deployment_clipboard.items():view.set(app.learning_row,view.by_offset[offset],value)
        except Exception as exc:view.changes=before;app.error(exc);return
        show_entry(app,app.learning_row);app.apply()
    def reset_unit():
        if app.learning_row:
            pid=app.learning_row.pid;view.changes={k:v for k,v in view.changes.items() if k[0]!=pid}
            show_entry(app,app.learning_row);app.apply()
    def open_character():
        if not app.learning_row or not app.apply(True):return
        pid=view.value(app.learning_row,view.by_offset[0x20]);owner=app.documents.get('Characters')
        if owner and pid in owner.by_pid:app.switch_module('Characters',pid)
        else:app.status.set('No loaded character record matches '+pid)
    for text,action in [('Copy unit',copy_unit),('Paste values',paste_unit),('Reset unit',reset_unit),('Open character',open_character)]:ttk.Button(tools,text=text,command=action).pack(side='left',padx=(0,5))
    refresh_entries(app);rows=view.rows_by_table[record.pid]
    if rows:show_entry(app,rows[0])
    else:ttk.Label(lower,text='Empty native group. Unit counts are fixed.').pack(anchor='w')
    references=ttk.Frame(app.notebook,padding=8);app.notebook.add(references,text='Connected entries');connected(app,references,record)
    maps=ttk.Frame(app.notebook,padding=8);app.notebook.add(maps,text='Battlefield links')
    ttk.Label(maps,text='Read-only exact deployment/revealed-deployment links from BattleField.bin. A file may also be selected by scripts; no chapter ownership is inferred.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    listing=tree(maps,[('battle','Battlefield',130),('title','English title',230),('role','Deployment role',160),('terrain','Terrain reference',130),('script','Script reference',160)],height=11)
    stem=PurePosixPath(view.filename).stem;count=0
    for link in app.battle_links:
        roles=[role for key,role in [('deployment','Main'),('revealed','Revealed')] if link[key]==stem]
        if roles:
            listing.insert('','end',values=(link['id'],translated(app,link['title']),', '.join(roles),link['terrain'],link['script']));count+=1
    ttk.Label(maps,text=f'{count} directly linked battlefield records. BattleField.bin is not edited or exported by this module.',style='Hint.TLabel').pack(anchor='w',pady=5)
    app.deployment_maps_tree=listing;app.notebook.select(min(active,2))
