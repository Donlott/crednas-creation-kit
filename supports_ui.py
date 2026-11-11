"""Seven Reliance views, raw directional compatibility cells and editable conditions."""
import json
import tkinter as tk
from tkinter import ttk
from item_index import reference_ids
from dataclasses import replace
from skill_ui import scroll_body,numeric_list
from skill_index import strings

LABELS={'相性(縦軸と横軸の並び、数を揃える)':'Compatibility codes','対象１':'Character 1','対象２':'Character 2',
 '物攻':'Physical attack','魔攻':'Magic attack','物防':'Physical defense','魔防':'Magic defense',
 '命中':'Hit','回避':'Avoid','必殺':'Critical','必避':'Critical avoid','攻速':'Attack speed','初期レベル':'Initial level',
 'ランク':'Rank code','ルート':'Route code','いずれか加入':'Joined-character references','フラグ':'Required flags',
 '支援加算値':'Support addition','デフォルト部':'Default part code','デフォルトルート':'Default route code',
 'デフォルト章':'Default chapter code','連動フラグ':'Linked flag','支援レベル':'Support level code','名声レベル':'Renown level',
 '属性':'Attribute bitmask','必要フラグ':'Required flags','スカウト終了フラグ':'Scout-completion flags',
 '種類':'Type code','交渉難易度':'Negotiation difficulty code','必要アイテム':'Required item','必要数':'Required count',
 '引数':'Arguments','匂わせタイプ':'Hint type code','匂わせフラグ段階':'Hint-stage flags','匂わせラベル共通引数':'Shared hint-label arguments',
 '発生率':'Stored rate vector','話者':'Speaker','対象':'Target character','ボイスラベル名':'Voice label',
 '切替フラグ':'Switch flags','切替ラベル名':'Alternate voice label','渡す飲み物':'Drink items'}
for part in range(1,4):
 for word,english in (('年','Year'),('月','Month'),('日','Day')):LABELS[f'{word}_{part}部']=f'Part {part} {english.lower()}'


def display_field(view,field):
    label=LABELS.get(field.name,field.label)
    if view.key=='talks':label={0x41:'Part code A',0x42:'Chapter code A',0x43:'Part code B',0x44:'Chapter code B'}.get(field.offset,label)
    return replace(field,name=label)


def translated(app,key):
    # Names reflect current Person/Item name-key edits when those tables are loaded.
    for doc in app.documents.values():
        if doc.prefix in ('PID_','IID_') and key in doc.by_pid:
            name=app.names.get(doc.value(doc.by_pid[key],doc.by_offset[0x20]))
            if name:return name
    result=app.translator.resolve(key)
    return key if result.source=='Untranslated' else result.text.removeprefix('Reference: ').removeprefix('Character: ')


def row_name(app,record,view=None):
    view=view or app.doc;name=view.names[record.pid]
    if view.key=='matrix':return translated(app,name)
    if view.key in ('special','talks','voices'):
        a=view.value(record,view.by_offset[0x20]);b=view.value(record,view.by_offset[0x30])
        title=translated(app,a)+' → '+translated(app,b)
        if view.key=='talks':title+=f' · rank {view.value(record,view.by_offset[0x40])}'
        return title
    if view.key=='scout':
        hint=translated(app,view.anchors[record.pid]) if view.anchors[record.pid] else 'Unlabelled section'
        return hint+f' · route {view.value(record,view.by_offset[0x20])}'
    if view.key=='drinks':return {'好物':'Favorite','通常':'Normal','嫌い':'Disliked'}.get(name,name)
    return f'Occurrence {record.index+1}'+('+' if record.index==7 else '')


def search_text(app,record):
    view=app.doc;text=[view.names[record.pid],view.anchors[record.pid]]
    for field in view.fields:
        if field.kind in ('string','data','data[]','string[]'):
            for _,value in strings(view.value(record,field)):text.extend((value,translated(app,value)))
    return ' '.join(text)


def suggestions(app,field):
    view=app.doc;values={text for row in view.records for _,text in strings(view.value(row,field))}
    prefix=None
    if view.key in ('special','talks','voices') and field.offset in (0x20,0x30):prefix='PID_'
    if view.key=='talks' and field.offset==0x48:prefix='PID_'
    if view.key=='scout' and field.offset==0x50 or view.key=='drinks' and field.offset==0x20:prefix='IID_'
    if prefix:values.update(reference_ids(app,prefix))
    return sorted(values-{''})


def refresh_matrix(app):
    if not hasattr(app,'support_matrix_tree') or not app.support_matrix_tree.winfo_exists():return
    if app.current is None:return
    view=app.doc;values=view.value(app.current,view.by_offset[0x20])
    for peer in view.records:
        key=str(peer.index);row=(translated(app,view.names[peer.pid]),values[peer.index],view.names[peer.pid])
        if app.support_matrix_tree.exists(key):app.support_matrix_tree.item(key,values=row)
        else:app.support_matrix_tree.insert('','end',iid=key,values=row)


def matrix(app,parent,record):
    from aid_ui import tree
    view=app.doc;field=view.by_offset[0x20]
    ttk.Label(parent,text='Select a column character to edit this row’s directed compatibility code. The original matrix is asymmetric; reverse cells are edited separately.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,7))
    listing=tree(parent,[('name','Column character',240),('value','Raw code',90),('rid','Raw column RID',370)],height=15)
    app.support_matrix_tree=listing;app.support_peer=view.records[0]
    bar=ttk.Frame(parent);bar.pack(fill='x',pady=7)
    pair=tk.StringVar();ttk.Label(bar,textvariable=pair).pack(side='left',padx=(0,10))
    ttk.Label(bar,text='Code (0–255)').pack(side='left',padx=(0,5))
    cell=ttk.Entry(bar,width=5,justify='right');cell.pack(side='left');app.support_cell=cell
    def vector():
        try:value=int(cell.get(),10)
        except ValueError as exc:raise ValueError('Compatibility code must be a whole number.') from exc
        values=view.value(record,field);values[app.support_peer.index]=value
        return values
    app.support_commit=lambda:view.set(record,field,vector())
    app.support_dirty=lambda:vector()!=view.value(record,field)
    def select_peer(event=None):
        if not listing.selection():return
        peer=view.records[int(listing.selection()[0])]
        if peer.pid==app.support_peer.pid:return
        old=app.support_peer
        if not app.apply(True):listing.selection_set(str(old.index));return
        app.support_peer=peer
        cell.delete(0,'end');cell.insert(0,str(view.value(record,field)[peer.index]))
        pair.set('Row → '+translated(app,view.names[peer.pid]))
    listing.bind('<<TreeviewSelect>>',select_peer)
    def reset_cell():
        if not app.apply(True):return
        cell.delete(0,'end');cell.insert(0,str(view.original(record,field)[app.support_peer.index]));app.apply()
    ttk.Button(bar,text='Reset cell',command=reset_cell).pack(side='left',padx=8)
    ttk.Label(parent,text='Stored codes are not labelled as ranks: their exact gameplay interpretation has not been verified. Matrix dimensions and RID order stay fixed.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w')
    cell.insert(0,str(view.value(record,field)[0]));pair.set('Row → '+translated(app,view.names[app.support_peer.pid]))
    refresh_matrix(app);listing.selection_set('0')


def connected(app,parent,record):
    from aid_ui import tree
    view=app.doc;owners=[]
    ttk.Label(parent,text='Direct character references and current matrix owners. Recruitment section hints are identified separately; conditions and runtime recruitment are not evaluated.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(parent,[('name','Character',190),('field','Relationship',250),('raw','Raw PID',320)],height=15)
    person=app.documents.get('Characters')
    if person and view.key=='matrix':
        for owner in person.records:
            if person.value(owner,person.by_offset[0x108])==view.names[record.pid]:owners.append((owner.pid,'Current support-reference owner'))
    elif view.key=='scout':
        anchor=view.anchors[record.pid]
        if anchor.startswith('PID_'):owners.append((anchor,'Previous named section anchor (hint)'))
    else:
        for field in view.fields:
            if field.kind in ('string','data','data[]','string[]'):
                for path,value in strings(view.value(record,field)):
                    if value.startswith('PID_'):owners.append((value,display_field(view,field).label+path))
    for i,(pid,kind) in enumerate(owners):listing.insert('','end',iid=str(i),values=(translated(app,pid),kind,pid))
    def navigate(event=None):
        if listing.selection():
            pid=owners[int(listing.selection()[0])][0]
            if person and pid in person.by_pid:app.switch_module('Characters',pid)
            else:app.status.set('Character source is not loaded: '+pid)
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Button(parent,text='Open selected character',command=navigate).pack(anchor='e',pady=6)
    app.support_connected_tree=listing;app.support_connected_open=navigate


def show_row(app,record):
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={};app.support_commit=None;app.support_dirty=None
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(row_name(app,record));app.details.set(f'Reliance.bin · {view.title} · row {record.index} · native names/order fixed')
    edit=ttk.Frame(app.notebook,padding=8);app.notebook.add(edit,text='Matrix row' if view.key=='matrix' else 'Fields')
    if view.key=='matrix':matrix(app,edit,record)
    else:
        body,bind=scroll_body(edit)
        name=view.names[record.pid] or '(empty native name)'
        note='Native name: '+name
        if view.key=='scout':note+=' · Previous named PID section: '+(view.anchors[record.pid] or '(none)')
        ttk.Label(body,text=note,style='Hint.TLabel',wraplength=730).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,7))
        text={'special':'Pair references, signed combat modifiers and initial-level code.',
              'talks':'Existing support-event conditions and references. Editing these fields does not create dialogue or rename conversation IDs. Part/chapter pairs remain A/B because their full selection semantics are unverified.',
              'scout':'Recruitment requirements for this fixed row. Blank native names retain the previous named PID as a section hint; route/type/attribute meanings remain raw codes.',
              'assist':'Fixed-length rate vectors, as stored. Position-to-rank mapping and percentage semantics are unverified.',
              'voices':'Linked-voice references and switch flags. Audio files are not modified.',
              'drinks':'Tobias recruitment drink-item lists; category names remain fixed.'}[view.key]
        ttk.Label(body,text=text,style='Hint.TLabel',wraplength=730).grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,7))
        for row,original in enumerate(view.fields,2):
            f=display_field(view,original)
            if f.kind in ('u8[]','s16[]'):numeric_list(app,body,row,f,record)
            elif f.kind in ('string','data','string[]','data[]'):app.reference_row(body,row,f,record)
            else:app.numeric_row(body,row,f,record)
        body.columnconfigure(1,weight=1,uniform='support');body.columnconfigure(2,weight=1,uniform='support');bind()
    links=ttk.Frame(app.notebook,padding=8);app.notebook.add(links,text='Connected characters');connected(app,links,record)
    app.notebook.select(min(active,1))
