"""Legion definitions and field-specific deployment/skill/item/appearance links."""
from dataclasses import replace
from tkinter import ttk
from item_index import reference_ids
from skill_ui import scroll_body
from skill_index import strings

LABELS={0x20:'Name message key',0x28:'Description message key',0x30:'Level',0x31:'Troop count',0x32:'Command (raw)',
 0x33:'Value tier (raw)',0x34:'Reward (raw)',0x38:'Gambit skill',0x48:'Equipment',0x58:'Additional skills',
 0x68:'Battle ambient sound',0x88:'Sale permission flags',0x98:'Price',0x9a:'Stock (raw)',0x9b:'Rarity (raw)',
 0xa0:'Appearance flags',0xb0:'Variation reference'}
for offset,label in zip(range(0x70,0x86,2),('HP','Strength','Magic','Dexterity','Speed','Luck','Defense','Resistance','Charm','Sight','Movement')):LABELS[offset]=label


def display_field(field):return replace(field,name=LABELS[field.offset])


def row_name(app,row,doc=None):
    doc=doc or app.doc;key=doc.value(row,doc.by_offset[0x20])
    if row.pid in app.custom_translations:return app.translator.resolve(row.pid).text
    if app.names.get(key):return app.names[key]
    # Avoid the generic LID -> Learning explanation when English names are unavailable.
    result=app.translator.resolve(row.pid.removeprefix('LID_'))
    return result.text if result.source!='Untranslated' else row.pid


def search_text(app,row):
    from supports_ui import translated
    values=[text for f in app.doc.fields for _,text in strings(app.doc.value(row,f))]
    return ' '.join(values+[translated(app,text) for text in values if text])


def suggestions(app,field):
    values={text for row in app.doc.records for _,text in strings(app.doc.value(row,field))}
    prefix='SID_' if field.offset in (0x38,0x58) else 'IID_' if field.offset==0x48 else 'AID_' if field.offset==0xa0 else 'VID_' if field.offset==0xb0 else 'MLID_' if field.offset in (0x20,0x28) else None
    if prefix:values.update(reference_ids(app,prefix));values.update(k for k in app.names if k.startswith(prefix))
    return sorted(values-{''})


def uses(lid,documents):
    """Exact legion-soldier fields; the LID_ namespace alone is insufficient."""
    found=[]
    for doc in documents.values():
        if doc.prefix!='DEPLOY_':continue
        view=doc.views['units'];field=view.by_offset[0x40]
        for row in view.records:
            if view.value(row,field)==lid:found.append((doc.filename,row.pid,view,row))
    return sorted(found,key=lambda x:(x[0].casefold(),x[2].row_location[x[1]]))


def connections(app,parent,record):
    from aid_ui import tree
    from supports_ui import translated
    doc=app.doc
    ttk.Label(parent,text='Current direct deployment assignments, gambit/equipment/skill targets and appearance flags. Learning-table LIDs are a separate namespace; scripts and indirect effects are not evaluated.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    listing=tree(parent,[('relation','Connection',145),('source','Source',170),('name','English / record',240),('raw','Native ID',210)],height=15);targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets.clear()
        from deployment_ui import row_name as deployment_name
        for source,pid,view,row in uses(record.pid,app.documents):
            listing.insert('','end',iid=str(len(targets)),values=('Assigned deployment',source,deployment_name(app,row,view),pid))
            targets.append(('Battle deployment',source,pid))
        for offset,module,prefix in [(0x38,'Skills','SID_'),(0x48,'Items','IID_'),(0x58,'Skills','SID_')]:
            for _,raw in strings(doc.value(record,doc.by_offset[offset])):
                if not raw:continue
                owner=next((d for d in app.documents.values() if d.prefix==prefix and raw in d.by_pid),None)
                listing.insert('','end',iid=str(len(targets)),values=(LABELS[offset],owner.filename if owner else '(not loaded)',translated(app,raw),raw))
                targets.append((module,owner.filename if owner else None,raw))
        for _,raw in strings(doc.value(record,doc.by_offset[0xa0])):
            if not raw:continue
            aid=raw[1:] if raw.startswith('!') else raw
            listing.insert('','end',iid=str(len(targets)),values=('Appearance flag','AIDs',translated(app,aid),raw))
            targets.append(('AIDs',None,aid))
        variation=doc.value(record,doc.by_offset[0xb0])
        if variation:
            for owner in app.documents.values():
                if owner.prefix!='APPEARANCE_' or 'variations' not in owner.views:continue
                view=owner.views['variations']
                for row in view.records:
                    if view.names[row.pid]==variation:
                        listing.insert('','end',iid=str(len(targets)),values=('Variation',owner.filename,translated(app,variation),variation))
                        targets.append(('Appearance rules',owner.filename,row.pid))
    def navigate(event=None):
        if not listing.selection():return
        module,source,pid=targets[int(listing.selection()[0])]
        if module=='AIDs':app.switch_module(module,pid)
        elif source:app.switch_module(module,pid,source_file=source)
        else:app.status.set('No loaded editable record matches '+pid)
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=5)
    ttk.Button(bar,text='Refresh links',command=refresh).pack(side='left');ttk.Button(bar,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    app.legion_links_tree=listing;app.legion_links=targets;app.legion_links_open=navigate;app.legion_links_refresh=refresh;refresh()


def show_legion(app,record):
    doc=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(row_name(app,record));app.details.set(record.pid+' · Legion.bin · native legion slot fixed')
    for title,fields in [('Legion',[f for f in doc.fields if f.offset<0x70]),('Stored stats',[f for f in doc.fields if 0x70<=f.offset<=0x84]),('Shop & appearance',[f for f in doc.fields if f.offset>=0x88])]:
        frame=ttk.Frame(app.notebook,padding=7);app.notebook.add(frame,text=title)
        body,bind=scroll_body(frame)
        if title=='Stored stats':note='Signed stored stat values. Whether the engine treats these as bases, bonuses or another modifier is unverified.'
        elif title=='Shop & appearance':note='Sale conditions, stock/rarity and appearance flags stay raw. Assets, scripts and message text are not rewritten.'
        else:note='Legion definitions use LID_ identifiers independently of Growth.bin learning tables. Troop/command/value limits are raw format ranges.'
        ttk.Label(body,text=note,style='Hint.TLabel',wraplength=710).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,6))
        for i,original in enumerate(fields,1):
            field=display_field(original)
            if field.kind in ('string','data','string[]','data[]'):app.reference_row(body,i,field,record)
            else:app.numeric_row(body,i,field,record)
        body.columnconfigure(1,weight=1,uniform='legion');body.columnconfigure(2,weight=1,uniform='legion');bind()
    links=ttk.Frame(app.notebook,padding=8);app.notebook.add(links,text='Connected entries');connections(app,links,record)
    page=app.nametowidget(app.notebook.tabs()[0]);tools=ttk.Frame(page)
    tools.pack(fill='x',side='bottom',before=page.pack_slaves()[0]);app.legion_tools=tools
    def copy_values():
        if app.apply(True):app.legion_clipboard={f.offset:doc.value(record,f) for f in doc.fields};app.status.set('Copied legion values; destination native LID stays fixed.')
    def paste_values():
        if app.legion_clipboard is None or not app.apply(True):return
        before=dict(doc.changes)
        try:
            for offset,value in app.legion_clipboard.items():doc.set(record,doc.by_offset[offset],value)
        except Exception as exc:doc.changes=before;app.error(exc);return
        show_legion(app,record);app.apply()
    ttk.Button(tools,text='Copy values',command=copy_values).pack(side='left',padx=5,pady=4)
    ttk.Button(tools,text='Paste values',command=paste_values).pack(side='left',pady=4)
    app.notebook.select(min(active,3))
