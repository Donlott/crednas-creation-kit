"""Fixed-order appearance editing, with explicit preservation of rule conditions."""
import tkinter as tk
from tkinter import ttk
from dataclasses import replace
from asset_index import field_label,aid_tokens,flatten
from skill_ui import scroll_body
from item_index import reference_ids


def display_field(field):return replace(field,name=field_label(field.name))


def row_name(app,record,view=None):
    view=view or app.doc;name=view.names[record.pid]
    if name:
        result=app.translator.resolve(name)
        return name if result.source=='Untranslated' else result.text.removeprefix('Appearance: ').removeprefix('Variation: ')
    if view.key=='rules':
        values=list(flatten(view.value(record,view.by_offset[0x20])))
        aids=[aid for text in values for aid,negative in aid_tokens(text) if not negative]
        if aids:
            result=app.translator.resolve(aids[0]);return result.text.removeprefix('Appearance: ') if result.source!='Untranslated' else aids[0]
    return f'Unnamed row {record.index}'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for field in view.fields:
        if field.kind in ('string','data','string[]','string[,]'):
            values.extend(flatten(view.value(record,field)))
    return ' '.join(values+[app.translator.resolve(v).text for v in values if v])


def suggestions(app,field):
    view=app.doc;values=set()
    for owner in app.documents.values():
        if owner.prefix!='APPEARANCE_' or view.key not in owner.views:continue
        peer=owner.views[view.key]
        for row in peer.records:values.update(flatten(peer.value(row,peer.by_offset[field.offset])))
    if view.key=='rules' and field.offset==0x158:
        values.update(key.removeprefix('FID_') for key in app.catalog if key.startswith('FID_'))
    elif field.kind=='string[,]':
        values.update(key for key in app.catalog if key.startswith(('AID_','PID_','JID_')))
        values.update(reference_ids(app,'JID_'));values.update(reference_ids(app,'PID_'))
    return sorted(values-{''})


def color_row(app,body,row,field,record):
    ttk.Label(body,text=field.label,width=24).grid(row=row,column=0,sticky='w',pady=3)
    entry=ttk.Entry(body,width=12);entry.insert(0,app.doc.value(record,field));entry.grid(row=row,column=1,sticky='w',pady=3)
    ttk.Label(body,text=f'4 raw bytes · 0x{field.offset:X} · #XXXXXXXX',style='Hint.TLabel').grid(row=row,column=2,columnspan=2,sticky='w',padx=6)
    app.widgets[field.offset]=(field,entry)


def tools(app,parent,record):
    view=app.doc;bar=ttk.Frame(parent);bar.pack(fill='x',pady=5);app.appearance_tools=bar
    if view.key in ('rules','voices'):
        def copy():
            if not app.apply(True):return
            fields=[f for f in view.fields if view.key!='rules' or f.offset!=0x20]
            app.appearance_clipboard=(view.key,{f.offset:view.value(record,f) for f in fields})
            app.status.set('Copied '+('appearance settings; conditions and native IDs are excluded.' if view.key=='rules' else 'voice/portrait settings; native FID is excluded.'))
        def paste():
            if not app.appearance_clipboard or not app.apply(True):return
            key,values=app.appearance_clipboard
            if key!=view.key:app.error('Copy settings from the same appearance section first.');return
            before=dict(view.changes)
            try:
                for offset,value in values.items():view.set(record,view.by_offset[offset],value)
            except Exception as exc:view.changes=before;app.error(exc);return
            show_row(app,record);app.apply()
        ttk.Button(bar,text='Copy settings',command=copy).pack(side='left',padx=(0,5))
        ttk.Button(bar,text='Paste settings',command=paste).pack(side='left',padx=(0,5))
    if view.key=='rules':
        def open_link():
            if not app.apply(True):return
            value=view.value(record,view.by_offset[0x158]);label=value if value.startswith('FID_') else 'FID_'+value
            owners=[d for d in app.documents.values() if d.prefix=='APPEARANCE_']
            owners.sort(key=lambda d:d.filename!=view.filename)
            for owner in owners:
                voices=owner.views.get('voices')
                if voices:
                    target=next((r for r in voices.records if voices.names[r.pid]==label),None)
                    if target:return app.switch_module('Appearance rules',target.pid,source_file=owner.filename)
            app.status.set('No loaded voice/portrait row matches '+label)
        ttk.Button(bar,text='Open linked voice / portrait',command=open_link).pack(side='left')
        ttk.Label(bar,text='Paste keeps the destination conditions and native ID.',style='Hint.TLabel').pack(side='right')


def show_row(app,record):
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(row_name(app,record));app.details.set(f'{view.filename} · {view.title} · row {record.index} · native ID/order fixed')
    groups={'Conditions':[],'Models & links':[],'Scale & colors':[]} if view.key=='rules' else {'Fields':[]}
    for field in view.fields:
        group=('Conditions' if field.offset==0x20 else 'Scale & colors' if field.kind in ('color','f32') or field.offset==0x114 else 'Models & links') if view.key=='rules' else 'Fields'
        groups[group].append(field)
    for title,fields in groups.items():
        tab=ttk.Frame(app.notebook);app.notebook.add(tab,text=title)
        top=ttk.Frame(tab,padding=(8,5));top.pack(fill='x')
        ttk.Label(top,text='Native label: '+(view.names[record.pid] or '(unnamed)'),style='Hint.TLabel',wraplength=720).pack(anchor='w')
        tools(app,top,record)
        content=ttk.Frame(tab);content.pack(fill='both',expand=True);body,bind=scroll_body(content)
        tip=('One JSON list per condition group; … opens the group editor. Group/priority semantics are not evaluated.' if title=='Conditions' else
             'Finite float32 values and four raw color bytes. Color channel order/alpha semantics are unverified.' if title=='Scale & colors' else
             'References are preserved exactly. Appearance links store bare FID names in this data. Models/portraits/audio are not previewed.' if view.key=='rules' else
             'Edit existing references and raw values. This does not modify the referenced asset files or simulate appearance selection.')
        ttk.Label(body,text=tip,style='Hint.TLabel',wraplength=720).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,7))
        for row,original in enumerate(fields,1):
            field=display_field(original)
            if field.kind=='color':color_row(app,body,row,field,record)
            elif field.kind in ('string','data','string[]','string[,]'):app.reference_row(body,row,field,record)
            else:app.numeric_row(body,row,field,record)
        body.columnconfigure(1,weight=1,uniform='appearance');body.columnconfigure(2,weight=1,uniform='appearance');bind()
    app.notebook.select(min(active,len(groups)-1))
