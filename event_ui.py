"""Event conditions/timelines with live links and a read-only compiled-script inspector."""
from dataclasses import replace
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from skill_ui import scroll_body
from skill_index import strings,document_views
from item_index import reference_ids
from localization import Translation

MODULE='Events'
CAPE='AID_マジーデマント有り'
EQUIPPED='進行_容姿変化_同期_マジーデが漆黒のグウエンを装着'
DIT_EQUIPPED='進行_容姿変化_同期_ディートリヒが漆黒のグウエンを装着'
RECEIVED='同期_日付_マジーデが漆黒のグウェンを受け取った'
LOST='同期_日付_マジーデが野良試合で負けた'
EXPLANATIONS={CAPE:'Majide: cape appearance flag',EQUIPPED:'Majide: wearing the black cape',
 DIT_EQUIPPED:'Dietrich: wearing the black cape',RECEIVED:'Date reached: Majide received the black cape',
 LOST:'Date reached: Majide lost the duel', '漆黒のグウェン':'Ink-Black Wen (event argument)',
 'ディートリヒ篇':'Dietrich route','BD12_04':'Dietrich vs Majide duel'}
LABELS={
 'variables':{0x20:'Variable / flag name (fixed)',0x28:'Initial value',0x2c:'Minimum value',0x30:'Maximum value',
  0x38:'Stored value labels',0x48:'Update mode (raw)',0x49:'Change mode (raw)',0x50:'Condition groups',
  0x60:'Year',0x62:'Month',0x63:'Day',0x64:'Time (raw)',0x66:'Result (raw)'},
 'timeline':{0x20:'Fabrication flag (raw)',0x21:'Event type code',0x28:'Ordered command arguments',0x38:'Condition groups',
  0x48:'Interval flags',0x58:'Part (signed)',0x59:'Chapter (signed)',0x5a:'Year (signed)',0x5c:'Month (signed)',
  0x5d:'Day (signed)',0x5e:'Time (signed)',0x60:'Same-time reference',0x68:'Display code (raw)',0x70:'Location',
  0x80:'Battlefield',0x90:'Objective message key',0x98:'Objective type (raw)',0xa0:'Destination',
  0xb0:'Locator names',0xc0:'Displayed destination',0xd0:'Hash key (fixed)'},
 'chapter':{0x20:'Fabrication flag (raw)',0x21:'Part code',0x22:'Chapter code',0x23:'Route code',
  0x28:'Condition flags',0x38:'Usage-permission flags',0x48:'Other permission flags'},
 'situations':{0x20:'Condition groups',0x30:'Year',0x32:'Month',0x33:'Day',0x34:'Category (raw)',
  0x38:'Location',0x48:'Placement locator',0x50:'Companion / group reference'},
}


def translate(app,raw):
    if raw in app.custom_translations:return app.translator.resolve(raw)
    if raw.startswith('!') and raw[1:] in EXPLANATIONS:return Translation('NOT: '+EXPLANATIONS[raw[1:]],'Glossary')
    if raw in EXPLANATIONS:return Translation(EXPLANATIONS[raw],'Glossary')
    return app.translator.resolve(raw)


def collection_name(app,record,view=None):
    view=view or app.doc;native=view.names[record.pid]
    result=translate(app,native)
    return (native if result.source in ('Untranslated','Empty') else result.text) if native else f'{view.title} · row {record.index}'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for row in view.rows_by_table[record.pid]:
        for field in view.fields:values.extend(text for _,text in strings(view.value(row,field)))
    return ' '.join(values+[translate(app,v).text for v in values])


def suggestions(app,field):
    view=app.doc;values=set()
    condition=field.kind=='string[,]' or view.key=='chapter' or view.key=='timeline' and field.offset==0x48
    for owner in app.documents.values():
        for peer in getattr(owner,'views',{}).values():
            if peer.prefix!='EVENT_':continue
            for row in peer.records:
                if condition and peer.key=='variables':values.add(peer.value(row,peer.by_offset[0x20]))
                if peer.key==view.key and field.offset in peer.by_offset:
                    values.update(text for _,text in strings(peer.value(row,peer.by_offset[field.offset])))
    if condition or view.key=='timeline' and field.offset==0x28:
        for prefix in ('PID_','JID_','IID_','SID_','AID_'):values.update(reference_ids(app,prefix))
    if view.key=='timeline' and field.offset==0x90:values.update(key for key in app.names if key.startswith('MID_'))
    return sorted(values-{''})


def summary(view,row):
    if view.key=='timeline':return str(view.value(row,view.by_offset[0x21])),' | '.join(view.value(row,view.by_offset[0x28]))
    if view.key=='variables':return f'{view.value(row,view.by_offset[0x48])}/{view.value(row,view.by_offset[0x49])}',view.value(row,view.by_offset[0x20])
    field=view.by_offset[0x20];return view.key,json.dumps(view.value(row,field),ensure_ascii=False)


def refresh_entries(app):
    if not getattr(app,'event_tree',None) or not app.event_tree.winfo_exists() or not app.current:return
    view=app.doc
    for row in view.rows_by_table[app.current.pid]:
        code,raw=summary(view,row);vals=(row.index,code,translate(app,raw).text,raw)
        if app.event_tree.exists(row.pid):app.event_tree.item(row.pid,values=vals)
        else:app.event_tree.insert('','end',iid=row.pid,values=vals)


def show_entry(app,row):
    app.clear_previews();app.learning_row=row;app.widgets={};form=app.event_form
    for tab in form.tabs():app.nametowidget(tab).destroy()
    view=app.doc
    date={0x60,0x62,0x63,0x64} if view.key=='variables' else set(range(0x58,0x69)) if view.key=='timeline' else set()
    groups=[('Event / conditions',[f for f in view.fields if f.offset not in date])]
    if date:groups.append(('Date / schedule',[f for f in view.fields if f.offset in date]))
    for title,fields in groups:
        frame=ttk.Frame(form,padding=4);form.add(frame,text=title);body,bind=scroll_body(frame)
        for i,original in enumerate(fields):
            field=replace(original,name=LABELS[view.key][original.offset])
            if field.offset in view.locked_offsets:
                ttk.Label(body,text=field.name,width=24).grid(row=i,column=0,sticky='w')
                value=ttk.Entry(body);value.insert(0,view.value(row,field));value.configure(state='readonly');value.grid(row=i,column=1,sticky='ew')
                ttk.Label(body,text=translate(app,view.value(row,field)).text,style='English.TLabel',wraplength=220).grid(row=i,column=2,sticky='ew',padx=4)
            elif field.kind in ('string','data','string[]','data[]','string[,]'):app.reference_row(body,i,field,row)
            else:app.numeric_row(body,i,field,row)
        body.columnconfigure(1,weight=1,uniform='event');body.columnconfigure(2,weight=1,uniform='event');bind()
    if app.event_tree.exists(row.pid):app.event_tree.selection_set(row.pid);app.event_tree.see(row.pid)


def select_entry(app,event=None):
    selection=app.event_tree.selection()
    if not selection:return
    row=app.doc.by_pid[selection[0]]
    if app.learning_row and row.pid==app.learning_row.pid:return
    if not app.apply(True):
        if app.learning_row:app.event_tree.selection_set(app.learning_row.pid)
        return
    show_entry(app,row)


def cape_links(app,parent):
    from aid_ui import tree
    ttk.Label(parent,text='Verified stored-data chain, not a traced runtime execution. Original 1.00 row indexes shown; no cape edits are applied automatically.',style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=5)
    targets=[('Majide cape AID','Variable.bin','variables:871:0'),('Majide wearing cape rule','Variable.bin','variables:1216:0'),
      ('Dietrich wearing cape rule','Variable.bin','variables:1217:0'),('Received date: 1449-03-01 23:59','Variable.bin','variables:1485:0'),
      ('Lost duel date: 1449-03-08 14:59','Variable.bin','variables:1486:0'),('Launch duel BD12_04','Timeline_Part1_Dit.bin','timeline:0:82'),
      ('Following cape argument (type 29)','Timeline_Part1_Dit.bin','timeline:0:85')]
    listing=tree(parent,[('meaning','Link / English',285),('file','Source',215),('row','Native row',140)],height=9)
    for i,(meaning,file,pid) in enumerate(targets):listing.insert('','end',iid=str(i),values=(meaning,file,pid))
    def navigate():
        if listing.selection():
            index=int(listing.selection()[0]);_,file,pid=targets[index]
            owner=next((d for d in app.documents.values() if d.filename==file),None)
            if not owner:app.error('Load '+file+' to open this investigation link.');return
            view=next(iter(owner.views.values()))
            if index<5:
                expected=(CAPE,EQUIPPED,DIT_EQUIPPED,RECEIVED,LOST)[index]
                row=next((r for r in view.records if view.value(r,view.by_offset[0x20])==expected),None)
            else:
                expected=['BD12_04'] if index==5 else ['漆黒のグウェン']
                row=next((r for r in view.records if view.value(r,view.by_offset[0x28])==expected),None)
            if row:app.switch_module(MODULE,row.pid,source_file=file)
            else:app.error('The expected native investigation record was not found; no edits were made.')
    def asset():
        from asset_index import flatten
        owner=next((d for d in app.documents.values() if d.filename=='AssetTable.bin'),None)
        view=owner.views.get('rules') if owner else None
        row=next((r for r in view.records if CAPE in flatten(view.value(r,view.by_offset[0x20]))),None) if view else None
        if row:app.switch_module('Appearance rules',row.pid,source_file='AssetTable.bin',section='rules')
        else:app.error('Load the matching AssetTable.bin cape rule to open this link.')
    ttk.Button(parent,text='Open selected event rule',command=navigate).pack(anchor='e',pady=4)
    ttk.Button(parent,text='Open Majide cape appearance rule',command=asset).pack(anchor='e',pady=4)
    ttk.Label(parent,text='Majide equipped condition: received-date flag, plus !lost-duel flag. To test keeping his cape, remove only the negated lost-duel token from that condition group. Keep the received-date requirement. Existing-save recomputation is unverified; use a separate mod and backup. The Dietrich rule is independent.',style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=8)
    app.event_cape_tree=listing;app.event_cape_open=navigate


def compiled_scripts(app,parent):
    from script_inspector import inspect
    from script_ui import open_editor
    from fw_editor import decompress
    from aid_ui import readonly_text
    ttk.Label(parent,text='ASF wrapper/import inspection only. Identifier runs are evidence, not decoded commands or executed-call counts. Use Open script editor to edit parsed constants and supported instructions.',style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=4)
    root=Path(app.data_directory).parent/'Script';paths=sorted(root.rglob('*.bin.zst')) if root.is_dir() else []
    choices={p.relative_to(root).as_posix():p for p in paths};choice=ttk.Combobox(parent,values=list(choices),state='readonly');choice.pack(fill='x')
    ttk.Button(parent,text='Open script editor…',command=lambda:open_editor(app,choice.get())).pack(anchor='e',pady=4)
    output=readonly_text(parent,'No adjacent Script folder found.' if not paths else 'Select a compiled script.')
    def show(event=None):
        path=choices.get(choice.get())
        if not path:return
        try:
            info=inspect(decompress(path.read_bytes()));text=f'{choice.get()}\nPayload offset: 0x{info.payload_offset:X}\nPayload size: {info.payload_size}\n\nImports:\n'+'\n'.join(info.imports)+'\n\nASCII identifier runs (not declarations):\n'+'\n'.join(info.identifiers)
        except Exception as exc:text=str(exc)
        output.configure(state='normal');output.delete('1.0','end');output.insert('1.0',text);output.configure(state='disabled')
    choice.bind('<<ComboboxSelected>>',show)
    app.event_script_choice=choice;app.event_script_show=show;app.event_script_output=output


def connections(app,parent,record):
    from aid_ui import tree
    listing=tree(parent,[('name','Reference / English',265),('file','Source file',180),('record','Target record',230)],height=13);targets=[]
    def refresh():
        if not app.apply(True):return
        targets.clear();listing.delete(*listing.get_children());view=app.doc
        texts={s.lstrip('!') for row in view.rows_by_table[record.pid] for f in view.fields for _,s in strings(view.value(row,f)) if s}
        for module,peer in document_views(app.documents):
            if peer.prefix=='EVENT_':
                for row in peer.records:
                    if peer.key=='variables' and peer.value(row,peer.by_offset[0x20]) in texts:targets.append((MODULE,peer.filename,row.pid,peer.value(row,peer.by_offset[0x20])))
            elif peer.prefix in ('PID_','JID_','IID_','SID_'):
                for value in sorted(texts & set(peer.by_pid)):targets.append((module,peer.filename,value,value))
        for i,(module,file,pid,name) in enumerate(targets):listing.insert('','end',iid=str(i),values=(translate(app,name).text,file,pid))
    def open_target():
        if listing.selection():
            module,file,pid,_=targets[int(listing.selection()[0])];app.switch_module(module,pid,source_file=file)
    ttk.Button(parent,text='Refresh outgoing references',command=refresh).pack(anchor='w',pady=4)
    ttk.Button(parent,text='Open selected reference',command=open_target).pack(anchor='e')
    app.event_connections_tree=listing;app.event_connections_refresh=refresh;app.event_connections_open=open_target


def show_table(app,record):
    from aid_ui import tree
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.widgets={};app.current=record;app.learning_row=None
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(collection_name(app,record));rows=app.doc.rows_by_table[record.pid]
    app.details.set(f'{app.doc.filename} · {len(rows)} native '+('entry' if len(rows)==1 else 'entries')+' · names, hash keys, row count and order fixed')
    entries=ttk.Frame(app.notebook,padding=6);app.notebook.add(entries,text='Entries')
    ttk.Label(entries,text='Edit stored event types/arguments, condition groups, flags and dates. Codes remain raw; execution and condition semantics are not simulated.',style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=4)
    panes=ttk.Panedwindow(entries,orient='vertical');panes.pack(fill='both',expand=True);top=ttk.Frame(panes);bottom=ttk.Frame(panes);panes.add(top,weight=1);panes.add(bottom,weight=4)
    app.event_tree=tree(top,[('row','Row',45),('type','Code',65),('english','English / explanation',290),('raw','Raw arguments / variable',320)],height=min(5,max(1,len(rows))))
    app.event_tree.bind('<<TreeviewSelect>>',lambda event:select_entry(app,event))
    tools=ttk.Frame(bottom);tools.pack(fill='x',pady=4)
    def copy():
        if app.learning_row and app.apply(True):app.event_clipboard=(app.doc.key,{f.offset:app.doc.value(app.learning_row,f) for f in app.doc.fields if f.offset not in app.doc.locked_offsets})
    def paste():
        if not app.learning_row or not app.event_clipboard or not app.apply(True):return
        key,values=app.event_clipboard
        if key!=app.doc.key:app.error('Copy an event of the same schema first.');return
        before=app.doc.snapshot_edits()
        try:
            for off,value in values.items():app.doc.set(app.learning_row,app.doc.by_offset[off],value)
        except Exception as exc:app.doc.restore_edits(before);app.error(exc);return
        show_entry(app,app.learning_row);refresh_entries(app)
    def reset():
        if app.learning_row:
            app.doc.changes={k:v for k,v in app.doc.changes.items() if k[0]!=app.learning_row.pid};show_entry(app,app.learning_row);refresh_entries(app)
    for text,command in [('Copy editable values',copy),('Paste editable values',paste),('Reset row',reset)]:ttk.Button(tools,text=text,command=command).pack(side='left',padx=(0,4))
    app.event_form=ttk.Notebook(bottom);app.event_form.pack(fill='both',expand=True)
    for title,builder in [('Connections',lambda parent:connections(app,parent,record)),('Majide cape',lambda parent:cape_links(app,parent)),('Compiled scripts',lambda parent:compiled_scripts(app,parent))]:
        tab=ttk.Frame(app.notebook,padding=7);app.notebook.add(tab,text=title);builder(tab)
    refresh_entries(app)
    if rows:show_entry(app,rows[0])
    app.notebook.select(min(active,3))
