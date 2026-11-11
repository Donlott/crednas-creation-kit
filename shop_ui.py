"""Compact shop/lottery collections, fixed entry slots and shared item exports."""
from dataclasses import replace
from tkinter import ttk
from item_index import reference_ids
from skill_ui import scroll_body,numeric_list
from skill_index import document_views,strings

LABELS={
 'shops':{0x20:'Shop name message key',0x28:'Item',0x38:'Sale conditions',0x48:'Exchange items',0x58:'Exchange quantities',0x68:'Price',0x6a:'Discount (signed raw)',0x6b:'Stock (raw)',0x6c:'Chapter restock (raw)'},
 'loot':{0x20:'Item',0x30:'Weight',0x38:'Conditions'},
 'values':{0x20:'Required causality',0x22:'Discard causality'},
}
WORDS={'帝都ダグシオン':'Dagsion','王都メガエラ':'Megaira','リベイラ村':'Ribeira Village','ヴァンダル商会':'Vandahl Trading Company',
 '武器屋':'Weapon shop','道具屋':'Item shop','鍛冶屋':'Forge','市場':'Market','手形屋':'Permit counter','酒場':'Tavern','飲み物係':'Drink attendant','アンナの店':"Anna's shop",'商会':'Trading company'}


def display_field(view,field):return replace(field,name=LABELS[view.key][field.offset])


def collection_name(app,record,view=None):
    view=view or app.doc;native=view.names[record.pid]
    if view.key=='values':return 'Value tiers'
    if native in app.custom_translations:return app.translator.resolve(native).text
    if view.key=='loot' and 'IID_'+native in app.catalog:
        result=app.translator.resolve('IID_'+native)
        if result.source!='Untranslated':return result.text.removeprefix('Item: ')
    text=native
    for word,value in sorted(WORDS.items(),key=lambda pair:len(pair[0]),reverse=True):text=text.replace(word,value)
    result=app.translator.resolve(text)
    return (text if result.source=='Untranslated' else result.text).replace('_',' / ')


def item_name(app,raw):
    from supports_ui import translated
    return translated(app,raw) if raw else '—'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for row in view.rows_by_table[record.pid]:
        for field in view.fields:
            if field.kind in ('string','data','string[]','data[]'):
                values.extend(text for _,text in strings(view.value(row,field)))
    return ' '.join(values+[item_name(app,value) for value in values if value])


def suggestions(app,field):
    view=app.doc;values={text for row in view.records for _,text in strings(view.value(row,field))}
    if view.key=='shops' and field.offset in (0x28,0x48) or view.key=='loot' and field.offset==0x20:
        values.update(reference_ids(app,'IID_'))
    if view.key=='shops' and field.offset==0x20:values.update(k for k in app.names if k.startswith('MID_Shop_'))
    return sorted(values-{''})


def refresh_entries(app):
    if not getattr(app,'shop_tree',None) or not app.shop_tree.winfo_exists() or app.current is None:return
    view=app.doc;rows=view.rows_by_table[app.current.pid]
    for row in rows:
        v=lambda offset:view.value(row,view.by_offset[offset])
        if view.key=='shops':values=(row.index,item_name(app,v(0x28)),v(0x68),v(0x6b),v(0x6a),v(0x28))
        elif view.key=='loot':values=(row.index,item_name(app,v(0x20)),v(0x30),len(v(0x38)),v(0x20))
        else:values=(row.index,v(0x20),v(0x22),view.names[row.pid])
        if app.shop_tree.exists(row.pid):app.shop_tree.item(row.pid,values=values)
        else:app.shop_tree.insert('','end',iid=row.pid,values=values)
    note=f'{len(rows)} existing entries. '
    if view.key=='loot':note+=f'Stored weight sum: {sum(view.value(row,view.by_offset[0x30]) for row in rows)}. Conditions are not evaluated.'
    else:note+='Native entry headers and counts stay fixed.'
    app.shop_summary.set(note)


def show_entry(app,row):
    app.clear_previews();app.learning_row=row;app.widgets={}
    for child in app.shop_form.winfo_children():child.destroy()
    body,bind=scroll_body(app.shop_form)
    ttk.Label(body,text=f'Entry {row.index} · '+(app.doc.names[row.pid] or '(unnamed native entry)'),style='Hint.TLabel',wraplength=720).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,5))
    for i,original in enumerate(app.doc.fields,1):
        field=display_field(app.doc,original)
        if field.kind=='u8[]':numeric_list(app,body,i,field,row)
        elif field.kind in ('string','data','string[]','data[]'):app.reference_row(body,i,field,row)
        else:app.numeric_row(body,i,field,row)
    body.columnconfigure(1,weight=1,uniform='shop');body.columnconfigure(2,weight=1,uniform='shop');bind()
    if app.shop_tree.exists(row.pid):app.shop_tree.selection_set(row.pid);app.shop_tree.see(row.pid)


def select_entry(app,event=None):
    selected=app.shop_tree.selection()
    if not selected:return
    row=app.doc.by_pid[selected[0]]
    if app.learning_row and app.learning_row.pid==row.pid:return
    if not app.apply(True):
        if app.learning_row:app.shop_tree.selection_set(app.learning_row.pid)
        return
    show_entry(app,row)


def collection_links(view,collection,documents):
    """Current direct lottery-table references; no scripts or indirect ownership."""
    name=view.names[collection.pid];found=[]
    if view.key!='loot':return found
    for module,peer in document_views(documents):
        if peer.prefix=='PID_':offsets=(0x188,)
        elif peer.prefix=='IID_':offsets=(0x170,)
        elif peer.prefix=='FACILITY_':offsets=(0x28,) if peer.key=='theater' else (0x38,) if peer.key=='actions' else ()
        else:continue
        for offset in offsets:
            field=peer.by_offset.get(offset)
            if field is None:continue
            for row in peer.records:
                if peer.value(row,field)==name:
                    target='Items' if peer.prefix=='IID_' else 'Facilities & Rewards' if peer.prefix=='FACILITY_' else module
                    found.append((target,peer.filename,row.pid,field,peer,row))
    return found


def connected(app,parent,record):
    from aid_ui import tree,name_for
    listing=tree(parent,[('source','Source',135),('name','Record / English',220),('field','Lottery field',240),('raw','Raw ID',200)],height=14);targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets[:]=collection_links(app.doc,record,app.documents)
        for i,(module,source,pid,field,peer,row) in enumerate(targets):
            if peer.prefix=='FACILITY_':
                from facility_ui import row_name,display_field as facility_field
                name=row_name(app,row,peer);label=facility_field(peer,field).label
            else:
                key=next(k for k,d in app.documents.items() if d.filename==source);name=name_for(app,key,pid);label=field.label
            listing.insert('','end',iid=str(i),values=(source,name,label,pid))
    def navigate(event=None):
        if listing.selection():
            module,source,pid,*_=targets[int(listing.selection()[0])];app.switch_module(module,pid,source_file=source)
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=6)
    ttk.Button(bar,text='Refresh links',command=refresh).pack(side='left');ttk.Button(bar,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Label(parent,text='Direct current character random-drop, item lottery-group and facility lottery references. Shop locations, scripts, conditional selection and indirect sources are not evaluated.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    app.shop_links_tree=listing;app.shop_links=targets;app.shop_links_open=navigate;app.shop_links_refresh=refresh;refresh()


def show_table(app,record):
    import tkinter as tk
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.learning_row=None;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(collection_name(app,record));app.details.set(f'{view.filename} · {view.title} · '+view.names[record.pid]+' · IDs/counts fixed')
    entries=ttk.Frame(app.notebook,padding=7);app.notebook.add(entries,text='Entries')
    note='Shop exchange items and quantities must stay paired. Price, signed discount, stock and restock values are raw; zero/sentinel behavior is unverified.' if view.key=='shops' else 'Lottery weights are unsigned 16-bit values. Conditions and engine probability rules are not evaluated.' if view.key=='loot' else 'Stored causality values for each native tier; no engine conversion formula is inferred.'
    ttk.Label(entries,text=note,style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=(0,6))
    pane=ttk.Panedwindow(entries,orient='vertical');pane.pack(fill='both',expand=True)
    upper=ttk.Frame(pane);lower=ttk.Frame(pane);pane.add(upper,weight=1);pane.add(lower,weight=3)
    from aid_ui import tree
    columns=[('row','#',32),('item','Item / English',180),('price','Price',60),('stock','Stock',55),('discount','Discount',65),('iid','Raw IID',230)] if view.key=='shops' else [('row','#',32),('item','Item / English',210),('weight','Weight',70),('conditions','Conditions',80),('iid','Raw IID',230)] if view.key=='loot' else [('row','#',35),('required','Required causality',150),('discard','Discard causality',150),('native','Native tier name',250)]
    app.shop_tree=tree(upper,columns,height=6);app.shop_form=lower
    app.shop_summary=tk.StringVar();ttk.Label(entries,textvariable=app.shop_summary,style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=4)
    app.shop_tree.bind('<<TreeviewSelect>>',lambda event:select_entry(app,event))
    tools=ttk.Frame(entries);tools.pack(fill='x',pady=4);app.shop_tools=tools
    def copy_entry():
        if not app.learning_row or not app.apply(True):return
        app.shop_clipboard=(view.key,{f.offset:view.value(app.learning_row,f) for f in view.fields})
        app.status.set('Copied entry values. Destination IDs, native headers and counts are preserved on paste.')
    def paste_entry():
        if not app.learning_row or not app.shop_clipboard or not app.apply(True):return
        key,values=app.shop_clipboard
        if key!=view.key:app.error('Copy an entry from the same Shop & Loot section first.');return
        before=dict(view.changes)
        try:
            for offset,value in values.items():view.set(app.learning_row,view.by_offset[offset],value)
            view.validate_record(app.learning_row)
        except Exception as exc:view.changes=before;app.error(exc);return
        show_entry(app,app.learning_row);app.apply()
    def reset_entry():
        if app.learning_row:
            pid=app.learning_row.pid;view.changes={key:value for key,value in view.changes.items() if key[0]!=pid}
            show_entry(app,app.learning_row);app.apply()
    def open_item():
        if not app.learning_row or not app.apply(True) or view.key=='values':return
        offset=0x28 if view.key=='shops' else 0x20;iid=view.value(app.learning_row,view.by_offset[offset])
        candidates=[doc for doc in app.documents.values() if doc.prefix=='IID_' and iid in doc.by_pid]
        candidates.sort(key=lambda doc:doc.filename!=view.filename)
        if candidates:app.switch_module('Items',iid,source_file=candidates[0].filename)
        else:app.status.set('No loaded item record matches '+iid)
    for label,action in [('Copy entry',copy_entry),('Paste values',paste_entry),('Reset entry',reset_entry),('Open item',open_item)]:ttk.Button(tools,text=label,command=action).pack(side='left',padx=(0,5))
    refresh_entries(app);rows=view.rows_by_table[record.pid]
    if rows:show_entry(app,rows[0])
    else:ttk.Label(lower,text='Empty collection. Entry counts stay fixed in this release.').pack(anchor='w')
    links=ttk.Frame(app.notebook,padding=8);app.notebook.add(links,text='Connected entries');connected(app,links,record)
    app.notebook.select(min(active,1))
