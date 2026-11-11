"""Compact SID editor. Enum and floating-point block semantics remain raw."""
import json
import tkinter as tk
from tkinter import ttk
from item_index import reference_ids
from dataclasses import replace

LABELS={
 '引数':'Text argument','引数0':'Text arguments','変数':'Variable','コマンド名':'Command name',
 '無効警告':'Invalid-use warning','使用通知':'Use notification','種類':'Type code','選択方法':'Selection method',
 '選択対象':'Selection target','選択許可':'Selection permission','習得優先':'Learning priority',
 '排他習得':'Exclusive learning','装備判定':'Equip check','装備優先':'Equip priority','表示優先':'Display priority',
 '選択実行':'Selection execution','実行順':'Execution order','タイミング':'Timing code','立場':'Stance code',
 '行動':'Action code','対象':'Target code','引数１':'Argument 1','引数２':'Argument 2','比較':'Comparison code',
 '増強無効化':'Enhancement invalidation','必要フラグ':'Required flags','無効フラグ':'Blocking flags',
 '有効行動':'Action bitmask','効果':'Effect code','値':'Effect values','効果対象':'Effect target','回数':'Count',
 '耐久消費':'Durability cost','HP消費':'HP cost','汚染値':'Contamination value','支援値':'Support value',
 '内射程':'Inner range','外射程':'Outer range','サイズ':'Size','重複数':'Stack count','基礎経験':'Base experience',
 '固定経験':'Fixed experience','周期':'Period values','寿命':'Lifetime','変化':'Change code',
 '継続行動条件':'Continuation condition','攻撃':'Attack bitmask','物攻':'Physical attack','魔攻':'Magic attack',
 '物防':'Physical defense','魔防':'Magic defense','命中':'Hit','回避':'Avoid','必殺':'Critical',
 '必避':'Critical avoid','攻速':'Attack speed','同時習得スキル':'Co-learned skills','付与効果スキル':'Granted-effect skills',
 '耐性スキル':'Resistance skill','バーストスキル':'Burst skill','バースト閾値':'Burst threshold',
 '強制装備':'Forced equipment','変身先':'Transformation target','効果範囲':'Effect area','表示範囲':'Display area',
 '範囲近':'Near range','範囲遠':'Far range','配置確率':'Placement probability','配置条件':'Placement condition',
 '配置地形':'Placement terrain','召喚対象':'Summon target','召喚人数':'Summon count','強化スキル':'Upgraded skill',
 '強化素材':'Upgrade material','素材数':'Material count','伝授素材':'Teaching material','表示':'Display bitmask',
 '発動エフェクト':'Activation effect','発射(移動)エフェクト':'Launch / movement effect','着弾エフェクト':'Impact effect',
 '命中エフェクト':'Hit effect','血印エフェクト':'Blood-mark effect','演出識別子':'Presentation ID',
 '戦闘モーション':'Battle motion','BMAPモーション':'Battle-map motion','コンバット導入音':'Combat intro sound',
 '演出ボイス':'Presentation voice','発動サウンド':'Activation sound','状態エフェクト':'Status effect',
 '状態アイコン':'Status icon','表示アイコン':'Display icon','使用済フラグ':'Used flag','消費済みフラグ':'Consumed flag',
}
OFFSETS={0x88:'Required skills A',0x98:'Blocking skills A',0xb8:'Required skills B',0xc8:'Blocking skills B'}


def display_field(field):return replace(field,name=OFFSETS.get(field.offset,LABELS.get(field.name,field.label)))


def tab_for(field):
    offset=field.offset
    if 0x14a<=offset<=0x1ee:return 'Stats'
    if offset>=0x2f8:return 'Presentation'
    if offset in (0x138,0x280) or 0x76<=offset<=0xf8:return 'Conditions'
    if offset>=0x1f0 and offset not in (0x278,0x279,0x27a):return 'Links'
    if offset>=0xfa:return 'Effects'
    return 'Overview'


def suggestions(app,field):
    values=set()
    from skill_index import strings
    for row in app.doc.records:
        values.update(text for _,text in strings(app.doc.value(row,field)))
    prefixes={0x20:'MSID_',0x30:'MSID_',0xa8:'SID_',0x138:'SID_',0x1f0:'SID_',0x200:'SID_',
              0x210:'SID_',0x220:'SID_',0x238:'IID_',0x248:'JID_',0x258:'RID_',0x268:'RID_',
              0x290:'TID_',0x2a0:'PID_',0x2b8:'SID_',0x2c8:'IID_',0x2e0:'IID_'}
    prefix='SID_' if field.offset in (0x88,0x98,0xb8,0xc8) else prefixes.get(field.offset)
    if prefix:values.update(reference_ids(app,prefix))
    if prefix=='MSID_':values.update(k for k in app.names if k.startswith(prefix))
    return sorted(values-{''})


def scroll_body(parent):
    canvas=tk.Canvas(parent,highlightthickness=0,background='#f4f5f7')
    bar=ttk.Scrollbar(parent,orient='vertical',command=canvas.yview);bar.pack(side='right',fill='y')
    canvas.configure(yscrollcommand=bar.set);canvas.pack(side='left',fill='both',expand=True)
    body=ttk.Frame(canvas,padding=8);window=canvas.create_window((0,0),window=body,anchor='nw')
    body.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda event:canvas.itemconfigure(window,width=event.width))
    def wheel(event):
        if canvas.bbox('all') and canvas.bbox('all')[3]>canvas.winfo_height():canvas.yview_scroll(-1 if event.num==4 or getattr(event,'delta',0)>0 else 1,'units')
        return 'break'
    def bind(widget):
        if not isinstance(widget,tk.Text):
            for event in ('<MouseWheel>','<Button-4>','<Button-5>'):widget.bind(event,wheel,add='+')
        for child in widget.winfo_children():bind(child)
    return body,lambda:bind(body)


def numeric_list(app,body,index,field,record):
    ttk.Label(body,text=field.label,width=20).grid(row=index,column=0,sticky='nw',pady=3)
    area=tk.Text(body,height=2,width=30,wrap='word',undo=True,font=('DejaVu Sans',9))
    area.insert('1.0',json.dumps(app.doc.value(record,field)));area.grid(row=index,column=1,columnspan=2,sticky='ew',pady=3)
    ttk.Label(body,text=f'{field.kind} · 0x{field.offset:X}\nJSON integer list',style='Hint.TLabel').grid(row=index,column=3,padx=6)
    app.widgets[field.offset]=(field,area)


def stats(app,parent,record):
    body,bind=scroll_body(parent)
    ttk.Label(body,text='Raw stat blocks. Float units and stacking/scaling semantics are not verified.',style='Hint.TLabel').pack(anchor='w',pady=(0,7))
    for title,blocks,count in [('Combat blocks',[(0x14a,2,'Signed 16-bit'),(0x15c,4,'Float')],9),
                                ('Stat blocks',[(0x180,2,'s16 A'),(0x198,4,'Float'),(0x1c4,2,'s16 B'),(0x1da,2,'s16 C')],11)]:
        box=ttk.LabelFrame(body,text=title,padding=7);box.pack(fill='x',pady=(0,10))
        for col,(start,width,label) in enumerate(blocks,1):
            ttk.Label(box,text=f'{label}\n0x{start:X}',style='Hint.TLabel',justify='center').grid(row=0,column=col,padx=6,pady=(0,4))
        for i in range(count):
            f=app.doc.by_offset[blocks[0][0]+i*blocks[0][1]]
            ttk.Label(box,text=LABELS.get(f.name,f.label),width=18).grid(row=i+1,column=0,sticky='w')
            for col,(start,width,_) in enumerate(blocks,1):
                f=app.doc.by_offset[start+i*width];widget=ttk.Entry(box,width=12,justify='right')
                widget.insert(0,app.number_text(app.doc.value(record,f),f.kind));widget.grid(row=i+1,column=col,padx=6,pady=2)
                app.widgets[f.offset]=(f,widget)
    bind()


def usage(app,parent,record):
    from aid_ui import tree,name_for
    from skill_index import SkillIndex
    ttk.Label(parent,text='Current field references, including item skills, prerequisites, exclusions and links. This does not mean a skill is equipped or active.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(parent,[('source','Source',120),('name','Record / English',190),('field','Reference field',210),('raw','Raw ID',220)],height=15)
    targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets.clear()
        index=app.skill_index or SkillIndex()
        for use in index.uses(record.pid,app.documents):
            name=app.translator.resolve(use.table or use.record).text
            if use.module and use.module not in ('Learning tables','Supports & Recruitment','Appearance rules','Profiles & Affiliations','Facilities & Rewards','Shop & Loot','Battle deployment','Progression & Difficulty'):
                key=next((key for key,doc in app.documents.items() if doc.filename==use.source),None)
                if key:name=name_for(app,key,use.record)
            label=use.field
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
            if use.module in ('Skills','Items'):
                source=next(doc for doc in app.documents.values() if doc.filename==use.source)
                offset=int(use.field.rpartition('0x')[2],16)
                formatter=display_field
                if use.module=='Items':
                    from item_ui import display_field as formatter
                label=formatter(source.by_offset[offset]).label+f' · 0x{offset:X}'
            listing.insert('','end',iid=str(len(targets)),values=(use.source,name,label+use.path+(' · negated' if use.negative else ''),use.record))
            targets.append(use)
        app.skill_usage_count.set(f'{len(targets)} references. Auxiliary-table rows are read-only; all source files remain distinct.')
    app.skill_usage_count=tk.StringVar();ttk.Label(parent,textvariable=app.skill_usage_count,style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=5)
    detail=tk.StringVar();ttk.Label(parent,textvariable=detail,style='Hint.TLabel',wraplength=740).pack(anchor='w')
    def selected(event=None):
        if listing.selection():
            use=targets[int(listing.selection()[0])];detail.set(f'{use.source} · {use.field}{use.path}\n{use.text}')
    def navigate(event=None):
        if not listing.selection():return
        use=targets[int(listing.selection()[0])]
        if use.module in ('Skills','Items','Appearance rules','Facilities & Rewards','Shop & Loot','Battle deployment','Progression & Difficulty'):app.switch_module(use.module,use.record,source_file=use.source)
        elif use.module=='Learning tables':
            if app.switch_module('Learning tables',use.table):
                from learning_ui import select_row
                app.learning_tree.selection_set(app.doc.rows_by_table[use.table][use.row].pid);select_row(app)
        elif use.module:app.switch_module(use.module,use.record)
        else:app.status.set('Read-only reference: '+use.source+' · '+use.record+' · '+use.field)
    listing.bind('<<TreeviewSelect>>',selected);listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    tools=ttk.Frame(parent);tools.pack(fill='x',pady=6)
    ttk.Button(tools,text='Refresh references',command=refresh).pack(side='left')
    ttk.Button(tools,text='Open selected entry',command=navigate).pack(side='right')
    app.skill_usage_tree=listing;app.skill_usage_targets=targets;app.skill_usage_refresh=refresh;app.skill_usage_open=navigate
    refresh()


def evidence(app,parent,record):
    from aid_ui import tree,readonly_text
    ttk.Label(parent,text='Original string-pool occurrences, including definitions. These are file evidence, not confirmed assignments. Unsaved edits are shown in Used by.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(parent,[('source','Source file',240),('offset','String offset',100),('text','Original text',400)],height=9)
    index=app.skill_index;rows=index.evidence.get(record.pid,[]) if index else []
    for i,row in enumerate(rows):listing.insert('','end',iid=str(i),values=(row.source,f'0x{row.offset:X}',row.text))
    report=[f'{len(rows)} original string occurrences. Compressed scripts and runtime-generated references are not evaluated.','',
            'Structured live references: Person.bin, Job.bin, LID entries and loaded Skill/Item files.',
            'Structured read-only references: auxiliary Skill groups; unloaded item files if available.','',
            'Readable GameData files: '+str(len(index.scanned_files) if index else 0),'']
    if index:
        report.extend(f'{source} · {group}: {count} scanned rows' for source,group,count in index.link_tables)
        report.extend(['','Files with errors (may be partially indexed):']+[f'{source}: {error}' for source,error in index.errors])
    readonly_text(parent,'\n'.join(report))


def show_skill(app,record):
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(app.display(record))
    definitions=[doc.filename for doc in app.documents.values() if doc.prefix=='SID_' and record.pid in doc.by_pid]
    app.details.set(f'{record.pid} · {app.doc.filename} · ID fixed'+(' · also in '+', '.join(f for f in definitions if f!=app.doc.filename) if len(definitions)>1 else ''))
    groups={title:[] for title in ('Overview','Effects','Conditions','Stats','Links','Presentation')}
    for f in app.doc.fields:groups[tab_for(f)].append(f)
    for title,fields in groups.items():
        frame=ttk.Frame(app.notebook);app.notebook.add(frame,text=title)
        if title=='Stats':stats(app,frame,record);continue
        body,bind=scroll_body(frame)
        tip='Codes and bitmasks remain raw numbers. Hover a field to inspect its original name, type and offset.'
        if title=='Conditions':tip='Grouped skill references: one JSON list per line, or use the group editor. Boolean group semantics remain unverified.'
        ttk.Label(body,text=tip,style='Hint.TLabel',wraplength=740).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,7))
        for i,original in enumerate(fields,1):
            f=display_field(original)
            if f.kind in ('s16[]','u8[]'):numeric_list(app,body,i,f,record)
            elif f.kind in ('float','u8','s8','u16','s16','b16','b32','u32','s32','bool','b8'):app.numeric_row(body,i,f,record)
            else:app.reference_row(body,i,f,record)
        body.columnconfigure(1,weight=1,uniform='skill');body.columnconfigure(2,weight=1,uniform='skill');bind()
    used=ttk.Frame(app.notebook,padding=8);app.notebook.add(used,text='Used by')
    usage(app,used,record)
    other=ttk.Frame(app.notebook,padding=8);app.notebook.add(other,text='File references')
    evidence(app,other,record)
    app.notebook.select(min(active,len(app.notebook.tabs())-1))
