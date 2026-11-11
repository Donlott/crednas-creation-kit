"""Profiles, raw preferences, affiliations and the other Profile.bin sections."""
from dataclasses import replace
from tkinter import ttk
from item_index import reference_ids
from skill_ui import scroll_body,numeric_list
from skill_index import strings
from profile_data import connections

LABELS={
 'profiles':{0x20:'Activation conditions',0x30:'Profile group',0x40:'Year',0x42:'Month',0x43:'Day',0x44:'Height (cm)',
  0x48:'Alias message key',0x50:'Title message key',0x58:'Scout introduction key',0x60:'Fast-travel help key',
  0x68:'History years',0x78:'History message keys',0x88:'Hobby message key',0x90:'Likes message key',0x98:'Dislikes message key',
  0xa0:'Facility conversation code',0xa8:'Meat rating',0xa9:'Fish rating',0xaa:'Vegetable rating',0xab:'Sweet rating',0xac:'Spicy rating',0xad:'Bitter rating',0xae:'Delicacy rating',
  0xaf:'Joy rating',0xb0:'Anger rating',0xb1:'Sorrow rating',0xb2:'Distress rating',0xb3:'Laughter rating',0xb4:'Courage rating',0xb5:'Love rating',0xb6:'Hate rating',
  0xb7:'Cleaning rating',0xb8:'Guarding rating',0xb9:'Cat activity rating',0xba:'Library rating',0xbb:'Sacred-song rating',0xbc:'Statue rating',
  0xc0:'Theater rating vector',0xd0:'Liked dishes',0xe0:'Disliked dishes',0xf0:'Liked gift items',0x100:'Disliked gift items',0x110:'Liked categories',0x120:'Disliked categories',0x130:'Speech rating',0x138:'Senior profile targets'},
 'affiliations':{0x20:'Clan message key',0x28:'Route code',0x30:'Icon ID',0x38:'Transition conditions',0x48:'Next affiliation'},
 'expressions':{0x20:'3D model expression',0x28:'2D expression',0x30:'2D motion',0x38:'Mouth-state code',0x39:'Mouth-shape code',0x3c:'Sweat bitmask'},
 'limits':{0x20:'Restriction conditions'},
 'order':{0x20:'Japanese order',0x22:'English order',0x24:'French order',0x26:'Spanish order',0x28:'German order',0x2a:'Italian order',0x2c:'Simplified Chinese order',0x2e:'Traditional Chinese order',0x30:'Korean order'},
}


def display_field(view,field):return replace(field,name=LABELS[view.key].get(field.offset,field.label))


def row_name(app,record,view=None):
    view=view or app.doc;name=view.names[record.pid]
    if not name:return f'Unnamed row {record.index}'
    result=app.translator.resolve(name)
    return name if result.source=='Untranslated' else result.text.removeprefix('Profile: ').removeprefix('Affiliation: ')


def search_text(app,record):
    view=app.doc;values=[view.names[record.pid]]
    for field in view.fields:
        if field.kind in ('string','data','string[]','data[]','string[,]'):
            values.extend(text for _,text in strings(view.value(record,field)))
    return ' '.join(values+[app.translator.resolve(v).text for v in values if v])


def suggestions(app,field):
    view=app.doc;values={text for r in view.records for _,text in strings(view.value(r,field))}
    prefix=None
    if view.key=='profiles':
        prefix='PRF_' if field.offset in (0x30,0x138) else 'IID_' if field.offset in (0xf0,0x100) else None
        stems={0x48:'MPID_',0x50:'MID_Roster_Position_',0x58:'MID_ScoutInfo_',0x60:'MID_FT_',0x78:'MID_Roster_Career_',0x88:'MID_Roster_Hobby_',0x90:'MID_Roster_Like_',0x98:'MID_Roster_Dislike_'}
        if field.offset in stems:values.update(k for k in app.names if k.startswith(stems[field.offset]))
    elif view.key=='affiliations':
        prefix='BID_' if field.offset==0x48 else None
        if field.offset==0x20:values.update(k for k in app.names if k.startswith('MID_Clan_'))
    if prefix:values.update(reference_ids(app,prefix))
    return sorted(values-{''})


def linked(app,parent,record):
    from aid_ui import tree
    listing=tree(parent,[('name','Record / English',240),('field','Direct relationship',250),('raw','Raw ID',260)],height=15)
    targets=[]
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets[:]=connections(app.doc,record,app.documents)
        for i,target in enumerate(targets):
            if target.module=='Characters':
                from supports_ui import translated
                name=translated(app,target.raw)
            else:
                owner=app.documents['Profiles & Affiliations'];view=owner.views[target.record.partition(':')[0]]
                name=row_name(app,view.by_pid[target.record],view)
            listing.insert('','end',iid=str(i),values=(name,target.relation,target.raw))
    def navigate(event=None):
        if listing.selection():
            target=targets[int(listing.selection()[0])];app.switch_module(target.module,target.record)
    tools=ttk.Frame(parent);tools.pack(fill='x',pady=6)
    ttk.Button(tools,text='Refresh links',command=refresh).pack(side='left')
    ttk.Button(tools,text='Open selected entry',command=navigate).pack(side='right')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    ttk.Label(parent,text='Current direct field references, including unsaved character edits. Affiliation transitions and profile conditions are not evaluated; incoming/outgoing links do not imply active ownership.',style='Hint.TLabel',wraplength=730).pack(anchor='w')
    app.profile_links_tree=listing;app.profile_links=targets;app.profile_links_open=navigate;app.profile_links_refresh=refresh;refresh()


def show_row(app,record):
    view=app.doc;active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(row_name(app,record));app.details.set(f'Profile.bin · {view.title} · row {record.index} · '+(view.names[record.pid] or '(unnamed)'))
    groups={'Bio & history':[],'Preferences':[],'Social & activities':[]} if view.key=='profiles' else {'Fields':[]}
    for field in view.fields:
        title=('Preferences' if 0xa8<=field.offset<=0xae or 0xd0<=field.offset<=0x120 else 'Social & activities' if field.offset>=0xa0 else 'Bio & history') if view.key=='profiles' else 'Fields'
        groups[title].append(field)
    for title,fields in groups.items():
        tab=ttk.Frame(app.notebook);app.notebook.add(tab,text=title)
        body,bind=scroll_body(tab)
        tip={'profiles':'References edit message keys, not localized text. Keep history years and history message keys the same length. Preference/activity ratings remain raw codes; the theater vector positions are unverified.',
             'affiliations':'Existing clan-name/icon/route references and conditional next-affiliation link. Route codes, group semantics and transition priority are not inferred.',
             'expressions':'Existing expression, motion and mouth/sweat codes. This does not preview faces or change animation files.',
             'limits':'Conditions attached to existing native conversation keys. Dialogue text and scripts are not rewritten.',
             'order':'Signed 16-bit per-language order values. Negative/sentinel meanings are unverified; native record order stays fixed.'}[view.key]
        ttk.Label(body,text=tip,style='Hint.TLabel',wraplength=730).grid(row=0,column=0,columnspan=4,sticky='w',pady=(0,7))
        if view.key=='profiles' and title=='Bio & history':
            ttk.Label(body,text='Source note: profile conditions are generally irreversible; the schema cautions against toggled flags and combined part/chapter thresholds.',style='Hint.TLabel',wraplength=730).grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,7))
        for i,original in enumerate(fields,2):
            field=display_field(view,original)
            if field.kind in ('s16[]','u8[]'):numeric_list(app,body,i,field,record)
            elif field.kind in ('string','data','string[]','data[]','string[,]'):app.reference_row(body,i,field,record)
            else:app.numeric_row(body,i,field,record)
        body.columnconfigure(1,weight=1,uniform='profile');body.columnconfigure(2,weight=1,uniform='profile');bind()
    if view.key in ('profiles','affiliations','order'):
        tab=ttk.Frame(app.notebook,padding=8);app.notebook.add(tab,text='Connected entries');linked(app,tab,record)
    app.notebook.select(min(active,len(app.notebook.tabs())-1))
