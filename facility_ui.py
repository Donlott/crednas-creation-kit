"""Facility gameplay parameters, rewards, grouped schedules and direct links."""
from dataclasses import replace
from tkinter import ttk
from item_index import reference_ids
from skill_ui import scroll_body,numeric_list
from skill_index import strings,document_views

LABELS={
 '名前':'Name message key','ヘルプ':'Help message key','スケジュール':'Schedule bitmask','名声レベル':'Renown level',
 '値段':'Price','素材':'Material code','味':'Taste code','料理モデル':'Dish model ID','条件':'Conditions',
 'チュートリアルルート指定':'Tutorial route conditions','費用':'Cost','お金':'Money','名声':'Renown','支援値':'Support value',
 'アイテム抽選':'Item lottery reference','アイテム確率':'Item chance (raw float)','必要フラグ':'Required flags',
 '通常':'Normal bitmask','パディング':'Padding byte','特別':'Special bitmask','習得スキル':'Learned skills',
 '比重':'Skill weights','マップ':'Map ID','アイコン':'Icon ID','変化条件':'Icon-change conditions','変化後アイコン':'Alternate icons',
 'フラグ':'Flags','吉曜':'Auspicious-day code','奉仕活動':'Service activity code','奉仕名':'Service name key','奉仕ヘルプ':'Service help key',
 '加護':'Blessing skill','神位個人':'Divine-rank character','場所':'Location code','スポット':'Spot reference','引数':'Arguments',
 'バトルタイトル':'Battle-title key','パーティ設定':'Party setup ID','推奨レベル':'Recommended level','獲得アイテム':'Reward items',
 '連動サブクエスト':'Linked subquest','ワープ先':'Warp destination','過去の記憶':'Past-memory vector',
 'カレンダー詳細':'Calendar detail key','イベント':'Event ID','篇指定':'Route conditions','年':'Year','月':'Month','日':'Day',
 '受付開始時刻':'Reception start (raw)','受付終了時刻':'Reception end (raw)','機能フラグ':'Feature bitmask',
 '基本経験':'Base experience','経験倍率':'Experience multiplier (raw)','兵種経験値':'Class experience','技能経験値':'Skill experience',
 '資金倍率':'Money multiplier (raw)','素材拾得率':'Material-find rate (raw)','素材抽選':'Material lottery',
 '回答グループ':'Answer-group code','個人':'Character','会話':'Conversation key','占い値':'Divination value',
 '内容':'Content message key','種類':'Type code','先生':'Teacher character','誘導中':'Guidance code','実行会話':'Start conversation',
 '戦場':'Battlefield reference','サブクエスト':'Subquest ID','報酬アイテム':'Reward item','報酬兵種フラグ':'Reward class flag',
 'リザルト会話':'Result conversation','サブクエ':'Subquest ID','ツワモノ戦場':'Challenge battlefield','会話番号':'Conversation number',
 '施設定義':'Facility definition','0～6':'00:00–06:00 code','6～12':'06:00–12:00 code','12～18':'12:00–18:00 code','18～24':'18:00–24:00 code',
 '状況名':'Status name','倍率':'Multiplier (raw)','対象施設':'Facility code','個人A':'Character A','識別子A':'Conversation code A',
 '個人B':'Character B','識別子B':'Conversation code B','支援低':'Low-support code','支援中':'Medium-support code','支援高':'High-support code',
 'ラベル':'Label','施設':'Facility ID','ルート':'Route code','項目名':'Entry message key','カウント名':'Counter name','集計':'Aggregation code',
 '必要値':'Required value','因果値':'Causality points','達成条件':'Completion conditions','表示条件':'Display conditions',
 '報酬名':'Reward-name key','効果':'Effect code','演算':'Operation code','値':'Value','クリア数':'Clear count',
 '通知条件':'Notification conditions','通知メッセージ':'Notification message key','引数0':'Message arguments','アイコン名':'Icon ID',
 '指南':'Tutorial reference','通知音':'Notification sound','報酬対象':'Reward target references','報酬技能':'Reward skill-code vector',
 '技能経験':'Skill experience vector','報酬フラグ':'Reward flag','LV':'Level','必要部':'Required part code','必要経験':'Required experience',
 '達成フラグ':'Completion flags',
}

GROUP_LABELS={'武器屋':'Weapon shop','鍛冶屋':'Forge','道具屋':'Item shop','市場':'Market',
 '宿屋':'Inn','商会':'Trading company','観劇':'Theater audience','出演':'Theater performance',
 '闘技場':'Arena','訓練':'Training','資格試験官':'Certification examiner','手形屋':'Permit counter',
 '神殿':'Temple','テルマエ':'Baths','止まり木':'Perch','アンナの店':"Anna's shop",'厩舎':'Stables',
 '酒場':'Tavern','飲み物係':'Drink attendant','軍団兵舎':'Legion barracks','奉仕':'Service',
 '試験':'Certification','饗宴':'Feast'}


def display_field(view,field):
    label=LABELS.get(field.name,field.label)
    if view.key=='training':label={0x68:'Weapon A',0x78:'Classes A',0x88:'Weapon B',0x98:'Classes B'}.get(field.offset,label)
    if view.key=='multipliers':
        index=(field.offset-0x20)//0x18+1;label+=f' {index}'
    if view.key=='temples':
        pairs={0x88:'Location code A',0x90:'Spot reference A',0xa0:'Arguments A',0xb0:'Location code B',0xb8:'Spot reference B',0xc8:'Arguments B',
            0xe8:'Battle-title key A',0xf0:'Party setup A',0xf8:'Recommended level A',0x100:'Reward items A',
            0x118:'Battle-title key B',0x120:'Party setup B',0x128:'Recommended level B',0x130:'Reward items B'}
        label=pairs.get(field.offset,label)
    if view.key=='questions' and field.offset>=0x40:label=f'Answer {(field.offset-0x40)//16+1} (bare name)'
    if view.key=='actions' and field.name=='表示':label={0x2a:'Experience display code',0x2c:'Class-XP display code',0x2e:'Skill-XP display code',0x30:'Money display code',0x48:'Material display code'}[field.offset]
    if view.key=='demos':label={0x30:'Part code A',0x31:'Chapter code A',0x32:'Part code B',0x33:'Chapter code B'}.get(field.offset,label)
    if view.key=='notices' and field.offset==0x20:label='Condition bitmask'
    if view.key=='exspots' and field.offset==0x30:label='Learned skill (bare name)'
    return replace(field,name=label)


def translated(app,raw):
    result=app.translator.resolve(raw)
    return raw if result.source=='Untranslated' else result.text


def group_title(app,raw):
    prefix,_,name=raw.partition('_')
    return GROUP_LABELS.get(name,translated(app,raw)) if prefix in ('OPH','SIT') else translated(app,raw)


def row_name(app,record,view=None):
    view=view or app.doc;name=view.names[record.pid]
    first=view.by_offset.get(0x20)
    if view.container==2:
        group=group_title(app,view.group_label(record));_,leaf=view.locations[record.pid]
        value=view.value(record,first) if view.key=='statuses' else ''
        return f'{group} · '+(translated(app,value) if value else f'row {leaf}')
    if first and first.kind=='string':
        value=view.value(record,first)
        if value in app.names:return app.names[value].replace('\n',' ')
    if name:return translated(app,name)
    if view.key=='renown':return f'Renown level {view.value(record,first)}'
    return f'Unnamed row {record.index}'


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid],view.group_label(record)]
    for field in view.fields:
        if field.kind in ('string','data','string[]','data[]','string[,]'):
            values.extend(text for _,text in strings(view.value(record,field)))
    return ' '.join(values+[translated(app,value) for value in values if value])


def suggestions(app,field):
    view=app.doc;values={text for r in view.records for _,text in strings(view.value(r,field))}
    prefix={
     'training':{0x68:'IID_',0x78:'JID_',0x88:'IID_',0x98:'JID_'},'baths':{0x48:'SID_'},
     'temples':{0x68:'SID_',0x78:'PID_',0x100:'IID_',0x130:'IID_'},'questions':{0x20:'PID_'},
     'lessons':{0x38:'PID_',0x70:'IID_'},'banter':{0x28:'PID_',0x40:'PID_'},
     'notices':{0xa8:'IID_'},'renown':{0x68:'IID_'},
    }.get(view.key,{}).get(field.offset)
    if prefix:values.update(reference_ids(app,prefix))
    if view.key=='questions' and field.offset>=0x40:values.update(k.removeprefix('PCHA_') for k in app.catalog if k.startswith('PCHA_'))
    if view.key=='exspots' and field.offset==0x30:values.update(k.removeprefix('SID_') for k in app.catalog if k.startswith('SID_'))
    if any(value.startswith('MID_') for value in values):values.update(k for k in app.names if k.startswith('MID_'))
    return sorted(values-{''})


def module_for(module,view):
    return {'SHOP_':'Shop & Loot','FACILITY_':'Facilities & Rewards','PROFILE_':'Profiles & Affiliations','APPEARANCE_':'Appearance rules','SID_':'Skills','IID_':'Items'}.get(view.prefix,module)


def direct_links(view,record,documents):
    """Exact direct references; original scripts, probabilities and event rules are not evaluated."""
    views=list(document_views(documents));lookup={};found=[]
    for module,peer in views:
        for row in getattr(peer,'collections',peer.records):
            name=peer.names[row.pid] if hasattr(peer,'names') else row.pid
            if name:lookup.setdefault(name,[]).append((module_for(module,peer),peer.filename,row.pid,peer,row))
    for field in view.fields:
        if field.kind not in ('string','data','string[]','data[]','string[,]'):continue
        for path,value in strings(view.value(record,field)):
            if view.key=='exspots' and field.offset==0x30:value='SID_'+value
            if view.key=='questions' and field.offset>=0x40:value='PCHA_'+value
            for module,source,pid,peer,row in lookup.get(value,[]):
                found.append((module,source,pid,'Outgoing: '+display_field(view,field).label+path,value,peer,row))
    native=view.names[record.pid]
    if native:
        for module,peer in views:
            if peer.prefix not in ('FACILITY_','PROFILE_'):continue
            for row in peer.records:
                for field in peer.fields:
                    if field.kind not in ('string','data','string[]','data[]','string[,]'):continue
                    for path,value in strings(peer.value(row,field)):
                        # Perch choices store names without the PCHA_ prefix.
                        if peer.prefix=='FACILITY_' and peer.key=='questions' and field.offset>=0x40:value='PCHA_'+value
                        if value==native:
                            if peer.prefix=='FACILITY_':label=display_field(peer,field).label
                            else:
                                from profile_ui import display_field as profile_field
                                label=profile_field(peer,field).label
                            found.append((module_for(module,peer),peer.filename,row.pid,'Incoming: '+label+path,native,peer,row))
    return found


def linked(app,parent,record):
    from aid_ui import tree,name_for
    listing=tree(parent,[('source','Source',130),('name','Record / English',205),('field','Direct relationship',230),('raw','Raw reference',230)],height=14)
    targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets[:]=direct_links(app.doc,record,app.documents)
        for i,(module,source,pid,relation,raw,peer,row) in enumerate(targets):
            if peer.prefix=='SHOP_':
                from shop_ui import collection_name
                name=collection_name(app,row,peer)
            elif peer.prefix=='FACILITY_':name=row_name(app,row,peer)
            elif peer.prefix=='PROFILE_':
                from profile_ui import row_name as profile_name
                name=profile_name(app,row,peer)
            elif peer.prefix=='APPEARANCE_':
                from appearance_ui import row_name as asset_name
                name=asset_name(app,row,peer)
            else:
                key=next((key for key,doc in app.documents.items() if doc.filename==source),None)
                name=name_for(app,key,pid) if key and module not in ('Learning tables','GLID progression') else translated(app,pid)
            listing.insert('','end',iid=str(i),values=(source,name,relation,raw))
    def navigate(event=None):
        if listing.selection():
            module,source,pid,*_=targets[int(listing.selection()[0])];app.switch_module(module,pid,source_file=source)
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=6)
    ttk.Button(bar,text='Refresh links',command=refresh).pack(side='left');ttk.Button(bar,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Label(parent,text='Outgoing references resolve to loaded editable records. Incoming links scan current facility/reward/profile fields. Duplicate sources stay separate. Scripts, scene choreography and runtime selection are not evaluated.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    app.facility_links_tree=listing;app.facility_links=targets;app.facility_links_open=navigate;app.facility_links_refresh=refresh;refresh()


def show_row(app,record):
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(row_name(app,record));app.details.set(f'{view.filename} · {view.title} · row {record.index} · '+(view.names[record.pid] or '(unnamed)')+(' · '+view.group_label(record) if view.container==2 else ''))
    edit=ttk.Frame(app.notebook);app.notebook.add(edit,text='Fields');body,bind=scroll_body(edit)
    note='Edit existing values and references. Enum/bitmask codes, multiplier units and probability scales remain raw. Native IDs, order and counts stay fixed.'
    if view.key=='baths':note+=' Keep learned skills and their weight lists the same length; weights are not labelled as percentages.'
    if view.container==2:note+=' Group headers and leaf counts remain unchanged; Group filters the list.'
    ttk.Label(body,text=note,style='Hint.TLabel',wraplength=730).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,8))
    for i,original in enumerate(view.fields,1):
        field=display_field(view,original)
        if field.kind in ('u8[]','s16[]'):numeric_list(app,body,i,field,record)
        elif field.kind in ('string','data','string[]','data[]','string[,]'):app.reference_row(body,i,field,record)
        else:app.numeric_row(body,i,field,record)
    body.columnconfigure(1,weight=1,uniform='facility');body.columnconfigure(2,weight=1,uniform='facility');bind()
    links=ttk.Frame(app.notebook,padding=8);app.notebook.add(links,text='Connected entries');linked(app,links,record)
    app.notebook.select(min(active,1))
