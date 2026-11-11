"""Compact primary IID editing and source-specific usage navigation."""
import tkinter as tk
from tkinter import ttk,simpledialog
from item_index import reference_ids
from dataclasses import replace
from skill_ui import scroll_body
from skill_index import strings

LABELS={
 '引数':'Text argument','引数0':'Text arguments','種類':'Type code','用途':'Use code','対象':'Target code',
 '値段':'Buy price','売値':'Sell price','価値':'Value code','基礎経験':'Base experience','固定経験':'Fixed experience',
 '耐久':'Durability','威力':'Power','重さ':'Weight','汚染値':'Contamination value','支援スコア':'Support score',
 '内射程':'Inner range','外射程':'Outer range','素材':'Material code','味':'Taste code','グレード':'Grade code',
 'HP回復率':'HP recovery rate','魔法回復率':'Magic recovery rate','物理攻撃':'Physical attack',
 '魔法攻撃':'Magic attack','物理防御':'Physical defense','魔法防御':'Magic defense','命中':'Hit',
 '回避':'Avoid','必殺':'Critical','必避':'Critical avoid','攻速':'Attack speed',
 '装備スキル':'Equipped skills','所持スキル':'Held skills','使用スキル':'Use skill','付与スキル':'Granted skills',
 '解除スキル':'Removed skills','必要スキル':'Required skills','禁止スキル':'Forbidden skills',
 '修理素材':'Repair material','素材数':'Material count','費用':'Cost','錬成先':'Forge target','錬成素材':'Forge material',
 '条件':'Conditions','フラグ':'Flags bitmask','変換先':'Conversion target','変換数':'Conversion count',
 '抽選グループ':'Lottery group','分類':'Classification links','カテゴリ':'Category code','レア度':'Rarity code',
 '発動エフェクト':'Activation effect','発射(移動)エフェクト':'Launch / movement effect','着弾エフェクト':'Impact effect',
 '命中エフェクト':'Hit effect','アセットフラグ':'Asset flag','アイコン名':'Icon name',
}
OFFSETS={0x118:'Repair material count',0x11c:'Repair cost',0x140:'Forge material count',0x144:'Forge cost'}


def display_field(field):return replace(field,name=OFFSETS.get(field.offset,LABELS.get(field.name,field.label)))


def tab_for(field):
    offset=field.offset
    if 0x57<=offset<=0x92:return 'Stats & use'
    if 0x98<=offset<=0xf8:return 'Skills'
    if 0x108<=offset<=0x180:return 'Crafting'
    if offset>=0x198:return 'Presentation'
    return 'Overview'


def suggestions(app,field):
    values={text for doc in app.documents.values() if doc.prefix=='IID_' for row in doc.records for _,text in strings(doc.value(row,doc.by_offset[field.offset]))}
    prefix=('SID_' if 0x98<=field.offset<=0xf8 else
            {0x20:'MIID_',0x30:'MIID_',0x108:'IID_',0x120:'IID_',0x130:'IID_',0x158:'IID_',0x1b8:'AID_'}.get(field.offset))
    if prefix:values.update(reference_ids(app,prefix))
    if prefix=='MIID_':values.update(k for k in app.names if k.startswith(prefix))
    # Lottery/classification references use observed raw values rather than an invented prefix.
    return sorted(values-{''})


def stats(app,parent,record):
    body,bind=scroll_body(parent)
    ttk.Label(body,text='Raw item values and signed stat modifiers. Weapon/enum code meanings remain unverified.',
              style='Hint.TLabel',wraplength=720).pack(anchor='w',pady=(0,7))
    panels=ttk.Frame(body);panels.pack(fill='x')
    sections=[('Use parameters',range(0x57,0x63)),('Weapon values',range(0x63,0x6b)),
              ('Combat modifiers',range(0x6c,0x7e,2)),('Stat modifiers',range(0x7e,0x94,2))]
    for index,(title,offsets) in enumerate(sections):
        frame=ttk.LabelFrame(panels,text=title,padding=7);frame.grid(row=index//2,column=index%2,sticky='nsew',padx=(0,9),pady=(0,9))
        for row,offset in enumerate(offsets):
            original=app.doc.by_offset[offset];field=display_field(original)
            ttk.Label(frame,text=field.label,width=20).grid(row=row,column=0,sticky='w',pady=2)
            widget=ttk.Entry(frame,width=7,justify='right');widget.insert(0,str(app.doc.value(record,field)))
            widget.grid(row=row,column=1,padx=5,pady=2);app.widgets[offset]=(field,widget)
            widget.bind('<Enter>',lambda event,f=original:app.status.set(f'{f.name} · {f.kind} · 0x{f.offset:X}'))
    panels.columnconfigure(0,weight=1);panels.columnconfigure(1,weight=1);bind()


def usage(app,parent,record):
    from aid_ui import tree,name_for
    from item_index import ItemIndex
    ttk.Label(parent,text='Current references, including shop/lottery edits and observed GLID item-name cells. Counts are references, not confirmed equipped owners.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(parent,[('source','Source',110),('name','Record / English',180),('field','Reference field',250),('raw','Raw ID',220)],height=15)
    targets=[];count=tk.StringVar();detail=tk.StringVar()
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets.clear()
        index=app.item_index or ItemIndex()
        for use in index.uses(record.pid,app.documents):
            name=app.translator.resolve(use.table or use.record).text;label=use.field
            key=next((k for k,d in app.documents.items() if d.filename==use.source),None)
            if use.module in ('Characters','Classes','Items','Skills') and key:name=name_for(app,key,use.record)
            if use.module=='Progression & Difficulty':
                from expanded_ui import row_name,display_field as expanded_field
                owner=next(d for d in app.documents.values() if d.filename==use.source);view=owner.views[use.record.partition(':')[0]]
                name=row_name(app,view.by_pid[use.record],view);offset=int(use.field.rpartition('0x')[2],16)
                label=expanded_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Legion':
                from legion_ui import display_field as legion_field
                owner=app.documents['Legion'];offset=int(use.field.rpartition('0x')[2],16)
                label=legion_field(owner.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Battle deployment':
                from deployment_ui import row_name,display_field as deployment_field
                owner=next(d for d in app.documents.values() if d.filename==use.source);view=owner.views['units']
                name=row_name(app,view.by_pid[use.record],view)
                offset=int(use.field.rpartition('0x')[2],16)
                label=deployment_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Shop & Loot':
                from shop_ui import collection_name,display_field as shop_field
                owner=next(d for d in app.documents.values() if d.filename==use.source)
                view=owner.views[use.record.partition(':')[0]]
                table,index=view.row_location[use.record]
                name=collection_name(app,view.tables_by_id[table],view)+f' · entry {index}'
                offset=int(use.field.rpartition('0x')[2],16)
                label=shop_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Facilities & Rewards':
                from facility_ui import row_name,display_field as facility_field
                owner=next(d for d in app.documents.values() if d.filename==use.source)
                view=owner.views[use.record.partition(':')[0]]
                name=row_name(app,view.by_pid[use.record],view)
                offset=int(use.field.rpartition('0x')[2],16)
                label=facility_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Profiles & Affiliations':
                from profile_ui import row_name,display_field as profile_field
                owner=app.documents['Profiles & Affiliations'];view=owner.views[use.record.partition(':')[0]]
                name=row_name(app,view.by_pid[use.record],view)
                offset=int(use.field.rpartition('0x')[2],16)
                label=profile_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Appearance rules':
                from appearance_ui import row_name,display_field as appearance_field
                owner=next(d for d in app.documents.values() if d.filename==use.source)
                view=owner.views[use.record.partition(':')[0]]
                name=row_name(app,view.by_pid[use.record],view)
                offset=int(use.field.rpartition('0x')[2],16)
                label=appearance_field(view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module=='Supports & Recruitment':
                from supports_ui import row_name,display_field as support_field
                owner=next(d for d in app.documents.values() if d.filename==use.source)
                view=owner.views[use.record.partition(':')[0]]
                name=row_name(app,view.by_pid[use.record],view)
                offset=int(use.field.rpartition('0x')[2],16)
                label=support_field(view,view.by_offset[offset]).label+f' · 0x{offset:X}'
            if use.module in ('Items','Skills') and key:
                offset=int(use.field.rpartition('0x')[2],16);source=app.documents[key]
                formatter=display_field
                if use.module=='Skills':
                    from skill_ui import display_field as formatter
                label=formatter(source.by_offset[offset]).label+f' · 0x{offset:X}'
            listing.insert('','end',iid=str(len(targets)),values=(use.source,name,label+use.path+(' · negated' if use.negative else ''),use.record))
            targets.append(use)
        count.set(f'{len(targets)} references. Shared progression tables may affect several characters; conditions are not evaluated.')
    def selected(event=None):
        if listing.selection():
            use=targets[int(listing.selection()[0])];detail.set(f'{use.source} · {use.record} · {use.field}{use.path}\n{use.text}')
    def navigate(event=None):
        if not listing.selection():return
        use=targets[int(listing.selection()[0])]
        if use.module in ('Items','Skills','Appearance rules','Facilities & Rewards','Shop & Loot','Battle deployment','Progression & Difficulty','Events'):app.switch_module(use.module,use.record,source_file=use.source)
        elif use.module=='GLID progression':
            if app.switch_module(use.module,use.table):
                from progression_ui import show_level,refresh_levels
                app.learning_row=app.doc.rows_by_table[use.table][use.row]
                show_level(app,use.level);refresh_levels(app);app.progression_tree.see(str(use.level))
        elif use.module=='Learning tables':
            if app.switch_module(use.module,use.table):
                from learning_ui import select_row
                app.learning_tree.selection_set(app.doc.rows_by_table[use.table][use.row].pid);select_row(app)
        elif use.module:app.switch_module(use.module,use.record)
        else:app.status.set('Read-only reference: '+use.source+' · '+use.record+' · '+use.field)
    ttk.Label(parent,textvariable=count,style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=5)
    ttk.Label(parent,textvariable=detail,style='Hint.TLabel',wraplength=740).pack(anchor='w')
    tools=ttk.Frame(parent);tools.pack(fill='x',pady=6)
    ttk.Button(tools,text='Refresh references',command=refresh).pack(side='left')
    ttk.Button(tools,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<<TreeviewSelect>>',selected);listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    app.item_usage_tree=listing;app.item_usage_targets=targets;app.item_usage_open=navigate;app.item_usage_refresh=refresh
    refresh()


def evidence(app,parent,record):
    from aid_ui import tree,readonly_text
    ttk.Label(parent,text='Original string-pool occurrences, including definitions. Current unsaved references are shown in Used by. GLID bare names are resolved there by category.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(parent,[('source','Source file',225),('offset','String offset',100),('text','Original text',410)],height=8)
    index=app.item_index;rows=index.evidence.get(record.pid,[]) if index else []
    for i,row in enumerate(rows):listing.insert('','end',iid=str(i),values=(row.source,f'0x{row.offset:X}',row.text))
    report=[f'{len(rows)} original string occurrences. No script or runtime-rule evaluation.','',
            'Current structured references: loaded characters, classes, skills, items and LID entries.',
            'Observed bare item-name references: GLID categories4–8. No inheritance simulation.',
            'Read-only structured references: shop and lottery collections.','',
            'Readable files: '+str(len(index.scanned_files) if index else 0)]
    if index:
        report.extend(['','Read-only collections:']+[f'{source} · {group} · {key}: {amount} rows' for source,group,key,amount in index.collections])
        report.extend(['','Files with errors (may be partially indexed):']+[f'{source}: {error}' for source,error in index.errors])
    readonly_text(parent,'\n'.join(report))


def show_item(app,record):
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(app.display(record));app.details.set(f'{record.pid} · {app.doc.filename} · '+('new item' if record.pid in app.doc.new_items else 'original item'))
    groups={title:[] for title in ('Overview','Stats & use','Skills','Crafting','Presentation')}
    for field in app.doc.fields:groups[tab_for(field)].append(field)
    for title,fields in groups.items():
        frame=ttk.Frame(app.notebook);app.notebook.add(frame,text=title)
        if title=='Stats & use':stats(app,frame,record);continue
        body,bind=scroll_body(frame)
        first=0
        if title=='Overview':
            tools=ttk.Frame(body);tools.grid(row=0,column=0,columnspan=4,sticky='ew',pady=(0,6))
            def create(duplicate=False,remove=False):
                if not app.apply(True):return
                doc=app.doc
                try:
                    if remove:
                        from item_index import ItemIndex
                        uses=[use for use in ItemIndex().uses(record.pid,app.documents) if not (use.source==doc.filename and use.record==record.pid)]
                        if uses:app.error(f'This item has {len(uses)} current references in loaded data. Remove or replace them first; see Used by.');return
                        doc.remove_item(record.pid);target=doc.records[0].pid
                    else:
                        owners=[d for d in app.documents.values() if d.prefix=='IID_']
                        stem=record.pid+'_Copy' if duplicate else 'IID_Custom';suggested=stem;number=2
                        while any(suggested in owner.by_pid or suggested in owner.labels for owner in owners):
                            suggested=f'{stem}_{number}';number+=1
                        key=simpledialog.askstring('Duplicate item' if duplicate else 'New item',
                            'Enter a unique IID_ ID. The item is created in '+doc.filename+'.',initialvalue=suggested,parent=app)
                        if key is None:return
                        if any(key in owner.by_pid for owner in owners):app.error('That IID already exists in a loaded item file.');return
                        target=doc.create_item(key,record.pid if duplicate else None).pid
                except Exception as exc:app.error(exc);return
                app.current=None;app.widgets={};app.suggestion_cache.clear();app.clear_previews();app.rebuild_translator()
                app.switch_module('Items',target,source_file=doc.filename);app.notebook.select(0)
                app.status.set('New item removed.' if remove else 'Item created in '+doc.filename+'. Configure its data and place it through character, shop, reward or deployment references; save or export to keep it.')
            app.item_creation_actions={}
            for label,command in [('New item…',create),('Duplicate item…',lambda:create(True)),('Remove new item',lambda:create(remove=True))]:
                button=ttk.Button(tools,text=label,command=command);button.pack(side='left',padx=(0,5));app.item_creation_actions[label]=button
            if record.pid not in app.doc.new_items:app.item_creation_actions['Remove new item'].configure(state='disabled')
            ttk.Label(body,text='Creation is experimental; test the exported mod in game. Blank items need configuration. Name/help fields reuse message keys.',
                      style='Hint.TLabel',wraplength=720).grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,5))
            first=2
        tip={'Overview':'Name/description fields edit message keys. Enum codes remain numeric.',
             'Skills':'Equipped, held, used, granted, removed, required and forbidden skill references remain distinct.',
             'Crafting':'Repair, forging, conversion and lottery references. Counts/costs retain the signedness of the source schema.',
             'Presentation':'Effect, asset and icon identifiers. This editor does not preview models or icons.'}[title]
        ttk.Label(body,text=tip,style='Hint.TLabel',wraplength=720).grid(row=first,column=0,columnspan=4,sticky='w',pady=(0,7))
        for i,original in enumerate(fields,first+1):
            field=display_field(original)
            if field.kind in ('string','data','string[]','data[]'):app.reference_row(body,i,field,record)
            else:
                app.numeric_row(body,i,field,record)
                if field.kind in ('int','u32','b32'):app.widgets[field.offset][1].configure(width=12)
        body.columnconfigure(1,weight=1,uniform='item');body.columnconfigure(2,weight=1,uniform='item');bind()
    used=ttk.Frame(app.notebook,padding=8);app.notebook.add(used,text='Used by');usage(app,used,record)
    other=ttk.Frame(app.notebook,padding=8);app.notebook.add(other,text='File references');evidence(app,other,record)
    app.notebook.select(min(active,len(app.notebook.tabs())-1))
