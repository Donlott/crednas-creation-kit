"""Shared-file progression tables and difficulty loadouts, with fixed native rows."""
from dataclasses import replace
from tkinter import ttk
from item_index import reference_ids
from skill_index import strings,document_views
from skill_ui import scroll_body,numeric_list

MODULE='Progression & Difficulty'
LABELS={
 'exp_curve':{0x20:'Level',0x22:'Required experience'},
 'exp_modifiers':{0x20:'Lookup value (signed)',0x22:'Normal modifier (raw)',0x24:'Hard modifier (raw)',0x26:'Lunatic modifier (raw)'},
 'exp_calculation':{0x20:'Referenced experience table'},
 'auto_exp':{0x20:'Experience',0x22:'Increment (raw)'},
 'auto_class':{0x20:'Class',0x40:'Limited target'},
 'auto_items':{o:f'Aptitude rank {rank}: item' for o,rank in zip(range(0x20,0x80,16),'SABCDE')},
 'hero_items':{0x20:'Character',0x30:'Conditional item grants',0x40:'Unconditional item grants'},
 'auto_legions':{o:f'Aptitude rank {rank}: legion' for o,rank in zip(range(0x20,0x80,16),'SABCDE')},
 'part2_items':{0x20:'Type (raw)',0x28:'Chapters (raw)',0x38:'Item references',0x48:'Quantities (raw)'},
 'part2_legions':{0x20:'Reward value (raw)',0x28:'Legion references'},
 'difficulty':{base+off:f'{label} · block {i+1}' for i,base in enumerate((0x20,0x50,0x80)) for off,label in [(0,'Initial skills'),(0x10,'Barrier items'),(0x20,'Latent skill rows')]},
 'auto_gear':{0x20:'Character',0x30:'Exclusive equipment'},
}
for o,name in zip(range(0x30,0x3d),('Sword','Lance','Axe','Bow','Brawling','Black magic','White magic','Special','Infantry','Mounted','Armor','Flying','Command')):
    LABELS['auto_class'][o]=name+' value (raw)'
WORDS={'ユニットレベル':'Unit levels','技能レベル':'Aptitude levels','乗り物レベル':'Mount levels','支援レベル':'Support levels',
 '補正無し':'No correction','レベル差補正':'Level difference','自レベル補正':'Own level','ターン減衰':'Turn decay',
 '通常攻撃':'Normal attack','とどめ':'Finishing blow','回復':'Healing','デフォルト':'Default','共通':'Common','持込禁止':'Carry-in restriction'}


def display_field(view,field):return replace(field,name=LABELS[view.key][field.offset])


def translated(app,raw):
    from supports_ui import translated as resolve
    return resolve(app,raw) if raw else '—'


def collection_name(app,record,view=None):
    view=view or app.doc;native=view.names[record.pid]
    if native in app.custom_translations:return app.translator.resolve(native).text
    if view.key in ('auto_class','hero_items','auto_gear'):
        row=view.rows_by_table[record.pid][0];raw=view.value(row,view.by_offset[0x20])
        if raw:return translated(app,raw)
    if view.key=='difficulty':
        # A matching character suffix supplies a display alias, never an ownership link.
        owner=view.owner;candidate=owner.by_pid.get('PID_'+native.removeprefix('DID_'))
        if candidate:
            key=owner.value(candidate,owner.by_offset[0x20]);name=app.names.get(key)
            if name:return name
    text=native
    for prefix in ('EID_','AGME_','AGJID_','AGIID_','AGHID_','AGLID_','P2SI_','P2SL_','DID_','PCHID_'):
        if text.startswith(prefix):text=text[len(prefix):];break
    for a,b in sorted(WORDS.items(),key=lambda pair:len(pair[0]),reverse=True):text=text.replace(a,b)
    result=app.translator.resolve(text)
    return (text if result.source=='Untranslated' else result.text).replace('_',' / ') if text else f'Row {record.index}'


def row_name(app,row,view):
    table,index=view.row_location[row.pid]
    return collection_name(app,view.tables_by_id[table],view)+f' · row {index}'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for row in view.rows_by_table[record.pid]:
        for field in view.fields:values.extend(text for _,text in strings(view.value(row,field)))
    return ' '.join(values+[translated(app,value) for value in values if value])


def suggestions(app,field):
    view=app.doc;values={text for row in view.records for _,text in strings(view.value(row,field))}
    prefix=None
    if view.key in ('auto_legions','part2_legions'):
        if 'Legion' in app.documents:values.update(app.documents['Legion'].by_pid)
    elif view.key=='auto_class':prefix='JID_' if field.offset==0x20 else 'PID_'
    elif view.key in ('hero_items','auto_gear'):prefix='PID_' if field.offset==0x20 else 'IID_'
    elif view.key in ('auto_items','part2_items'):prefix='IID_'
    elif view.key=='difficulty':prefix='IID_' if field.offset in (0x30,0x60,0x90) else 'SID_'
    elif view.key=='exp_calculation':
        for peer in view.owner.views.values():
            if peer.key in ('exp_curve','exp_modifiers'):values.update(peer.names[r.pid] for r in peer.collections)
    if prefix:values.update(reference_ids(app,prefix))
    return sorted(values-{''})


def refresh_entries(app):
    if not getattr(app,'expanded_tree',None) or not app.expanded_tree.winfo_exists() or app.current is None:return
    view=app.doc;fields=view.fields[:5]
    for row in view.rows_by_table[app.current.pid]:
        cells=[]
        for field in fields:
            value=view.value(row,field)
            cells.append(f'{len(value)} entries' if isinstance(value,list) else translated(app,value) if isinstance(value,str) else value)
        values=(row.index,*cells)
        if app.expanded_tree.exists(row.pid):app.expanded_tree.item(row.pid,values=values)
        else:app.expanded_tree.insert('','end',iid=row.pid,values=values)


def show_entry(app,row):
    app.clear_previews();app.learning_row=row;app.widgets={}
    form=app.expanded_form;selected=form.index('current') if form.tabs() else 0
    for tab in form.tabs():app.nametowidget(tab).destroy()
    if app.doc.key=='difficulty':groups=[(f'Block {i+1}',[f for f in app.doc.fields if base<=f.offset<base+0x30]) for i,base in enumerate((0x20,0x50,0x80))]
    elif app.doc.key=='auto_class':groups=[('Class & target',[f for f in app.doc.fields if f.kind=='data']),('Aptitude values',[f for f in app.doc.fields if f.kind=='u8'])]
    else:groups=[('Values',app.doc.fields)]
    for title,fields in groups:
        frame=ttk.Frame(form,padding=5);form.add(frame,text=title);body,bind=scroll_body(frame)
        for i,original in enumerate(fields):
            field=display_field(app.doc,original)
            if field.kind=='u8[]':numeric_list(app,body,i,field,row)
            elif field.kind in ('data','string','data[]','string[]','data[,]'):
                app.reference_row(body,i,field,row)
                if field.kind=='data[,]':
                    actions=next(w for w in body.grid_slaves(row=i,column=3) if isinstance(w,ttk.Frame))
                    button=next(w for w in actions.winfo_children() if isinstance(w,ttk.Button))
                    widget=app.widgets[field.offset][1]
                    button.configure(command=lambda f=field,w=widget:app.edit_conditions(f,w,'Each row contains stored latent-skill IDs. Group interpretation and difficulty-block ordering are unverified.'))
            else:app.numeric_row(body,i,field,row)
        body.columnconfigure(1,weight=1,uniform='expanded');body.columnconfigure(2,weight=1,uniform='expanded');bind()
    form.select(min(selected,len(groups)-1))
    if app.expanded_tree.exists(row.pid):app.expanded_tree.selection_set(row.pid);app.expanded_tree.see(row.pid)


def select_entry(app,event=None):
    selected=app.expanded_tree.selection()
    if not selected:return
    row=app.doc.by_pid[selected[0]]
    if app.learning_row and app.learning_row.pid==row.pid:return
    if not app.apply(True):
        if app.learning_row:app.expanded_tree.selection_set(app.learning_row.pid)
        return
    show_entry(app,row)


def connections(view,collection,documents):
    found=[];native=view.names[collection.pid]
    person=documents.get('Characters')
    if view.key=='difficulty' and person and 0x138 in person.by_offset:
        for row in person.records:
            if person.value(row,person.by_offset[0x138])==native:found.append(('Characters',person.filename,row.pid,'Uses this difficulty loadout',row.pid))
    # Exact native-table references from current expanded views (experience calculation links).
    for owner in documents.values():
        for peer in getattr(owner,'views',{}).values():
            if peer.prefix!='EXPANDED_' or peer.key!='exp_calculation':continue
            for row in peer.records:
                if peer.value(row,peer.by_offset[0x20])==native:found.append((MODULE,peer.filename,row.pid,'References this table',peer.names[row.pid]))
    for row in view.rows_by_table[collection.pid]:
        for field in view.fields:
            for _,raw in strings(view.value(row,field)):
                if not raw:continue
                module='Characters' if raw.startswith('PID_') else 'Classes' if raw.startswith('JID_') else 'Items' if raw.startswith('IID_') else 'Skills' if raw.startswith('SID_') else 'Legion' if view.key in ('auto_legions','part2_legions') and raw.startswith('LID_') else None
                if module:
                    prefix={'Characters':'PID_','Classes':'JID_','Items':'IID_','Skills':'SID_','Legion':'LID_'}[module]
                    target=next((d for d in documents.values() if d.prefix==prefix and raw in d.by_pid and (module!='Legion' or d.filename=='Legion.bin')),None)
                    found.append((module,target.filename if target else None,raw,LABELS[view.key][field.offset],raw))
                elif view.key=='exp_calculation':
                    for peer in view.owner.views.values():
                        for target in peer.collections:
                            if peer.names[target.pid]==raw:found.append((MODULE,peer.filename,target.pid,'Referenced experience table',raw))
    return found


def connected(app,parent,record):
    from aid_ui import tree,name_for
    listing=tree(parent,[('relation','Relationship',220),('source','Source',150),('name','English / record',250),('id','Native ID',220)],height=13);targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets[:]=connections(app.doc,record,app.documents)
        for i,(module,source,pid,relation,raw) in enumerate(targets):
            name=translated(app,raw)
            if module==MODULE and source:
                owner=next(d for d in app.documents.values() if d.filename==source);peer=owner.views[pid.partition(':')[0]]
                name=row_name(app,peer.by_pid[pid],peer) if pid in peer.by_pid else collection_name(app,peer.tables_by_id[pid],peer)
            elif module in ('Characters','Classes','Items','Skills','Legion') and source:
                key=next(k for k,d in app.documents.items() if d.filename==source);name=name_for(app,key,pid)
            listing.insert('','end',iid=str(i),values=(relation,source or '(not loaded)',name,raw))
    def navigate(event=None):
        if not listing.selection():return
        module,source,pid,*_=targets[int(listing.selection()[0])]
        if source:app.switch_module(module,pid,source_file=source)
        else:app.status.set('No loaded record matches '+pid)
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=5)
    ttk.Button(bar,text='Refresh links',command=refresh).pack(side='left');ttk.Button(bar,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Label(parent,text='Current direct fields only. Script selection, block execution order, conditional grants and experience formulas are not evaluated.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    app.expanded_links_tree=listing;app.expanded_links=targets;app.expanded_links_open=navigate;app.expanded_links_refresh=refresh;refresh()


def show_table(app,record):
    from aid_ui import tree
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.learning_row=None;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(collection_name(app,record));app.details.set(f'{view.filename} · {view.title} · '+(view.names[record.pid] or f'row {record.index}')+' · fixed native slots')
    entries=ttk.Frame(app.notebook,padding=6);app.notebook.add(entries,text='Entries')
    note='Difficulty blocks 1/2/3 retain their stored order; the mapping to named modes is unverified.' if view.key=='difficulty' else 'Chapter/item/quantity lists are independent raw lists: native rows include multiple items with a single or empty quantity list.' if view.key=='part2_items' else 'Stored values and references only. Modifier scales, aptitude thresholds and automatic selection formulas are unverified.'
    ttk.Label(entries,text=note,style='Hint.TLabel',wraplength=730).pack(anchor='w',pady=(0,4))
    panes=ttk.Panedwindow(entries,orient='vertical');panes.pack(fill='both',expand=True)
    compact=len(view.fields)<=4 and not any(f.kind in ('data[]','string[]','data[,]','u8[]') for f in view.fields)
    upper=ttk.Frame(panes);lower=ttk.Frame(panes);panes.add(upper,weight=3 if compact else 1);panes.add(lower,weight=1 if compact else 3)
    columns=[('slot','Row',45)]+[(str(f.offset),LABELS[view.key][f.offset],130) for f in view.fields[:5]]
    app.expanded_tree=tree(upper,columns,height=5);app.expanded_tree.bind('<<TreeviewSelect>>',lambda e:select_entry(app,e))
    tools=ttk.Frame(lower);tools.pack(fill='x',pady=4);app.expanded_tools=tools
    app.expanded_form=ttk.Notebook(lower);app.expanded_form.pack(fill='both',expand=True)
    def copy_entry():
        if app.learning_row and app.apply(True):app.expanded_clipboard=(view.key,{f.offset:view.value(app.learning_row,f) for f in view.fields})
    def paste_entry():
        if not app.learning_row or app.expanded_clipboard is None or not app.apply(True):return
        key,values=app.expanded_clipboard
        if key!=view.key:app.error('Copy values from the same progression/difficulty section first.');return
        before=dict(view.changes)
        try:
            for off,value in values.items():view.set(app.learning_row,view.by_offset[off],value)
            view.validate_record(app.learning_row)
        except Exception as exc:view.changes=before;app.error(exc);return
        show_entry(app,app.learning_row);app.apply()
    def reset_entry():
        if app.learning_row:
            pid=app.learning_row.pid;view.changes={k:v for k,v in view.changes.items() if k[0]!=pid};show_entry(app,app.learning_row);app.apply()
    for text,action in [('Copy entry',copy_entry),('Paste values',paste_entry),('Reset entry',reset_entry)]:ttk.Button(tools,text=text,command=action).pack(side='left',padx=(0,5))
    refresh_entries(app);rows=view.rows_by_table[record.pid]
    if rows:show_entry(app,rows[0])
    else:ttk.Label(lower,text='Empty native collection. Entry counts stay fixed.').pack(anchor='w')
    links=ttk.Frame(app.notebook,padding=8);app.notebook.add(links,text='Connected entries');connected(app,links,record)
    app.notebook.select(min(active,1))
