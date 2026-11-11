"""Read-only Tk views for the AID module, kept separate from binary editing."""
import json
import tkinter as tk
from tkinter import ttk

from asset_index import GROUP_NAMES, flatten


def name_for(app,module,record_id):
    doc=app.documents.get(module)
    if doc is None or record_id not in doc.by_pid:return record_id
    record=doc.by_pid[record_id];key=doc.value(record,doc.by_offset[0x20])
    result=app.translator.resolve(record_id)
    return app.names.get(key) or (result.text if result.source!='Untranslated' else record_id)


def short_value(value):
    return json.dumps(value,ensure_ascii=False) if isinstance(value,list) else str(value)


def summary(row):
    if row.group=='アセットテーブル':
        parts=[f'{label}: {row.values[offset]}' for offset,label in ((0x30,'Body'),(0x40,'Head'),(0x48,'Hair'),(0x158,'Appearance')) if row.values.get(offset)]
        return ' · '.join(parts) or 'Other appearance settings'
    if row.group=='容姿情報':return f'Voice: {row.values[0x20]} · Portrait: {row.values[0x28]}'
    if row.group=='条件セット':return 'Additional flags: '+', '.join(row.values.get(0x30,[]))
    return row.label or GROUP_NAMES.get(row.group,row.group)


def row_details(app,row):
    lines=[row.title,f'File offset: 0x{row.offset:X}',f'Label: {row.label or "(unnamed)"}',
           'Current appearance values. Conditions are not evaluated; colors are four raw bytes.','']
    for field in row.fields:
        value=row.values[field.offset]
        lines.append(f'{field.label} · {field.kind} · +0x{field.offset:X}')
        if isinstance(value,list) and value and isinstance(value[0],list):
            for i,group in enumerate(value,1):
                lines.append(f'  Group {i}: '+json.dumps(group,ensure_ascii=False))
                lines.append('  English: '+json.dumps([app.translator.resolve(v).text for v in group],ensure_ascii=False))
        else:
            lines.append('  '+short_value(value))
            texts=list(flatten(value))
            if texts:
                translated=[app.translator.resolve(text).text for text in texts]
                if translated!=texts:lines.append('  English: '+' · '.join(translated))
        lines.append('')
    return '\n'.join(lines)


def readonly_text(parent,text=''):
    frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
    widget=tk.Text(frame,wrap='word',height=8,font=('DejaVu Sans',9),borderwidth=0,padx=7,pady=6)
    bar=ttk.Scrollbar(frame,orient='vertical',command=widget.yview);widget.configure(yscrollcommand=bar.set)
    bar.pack(side='right',fill='y');widget.pack(side='left',fill='both',expand=True)
    set_text(widget,text)
    return widget


def set_text(widget,text):
    widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')


def tree(parent,columns,height=8):
    frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
    listing=ttk.Treeview(frame,columns=tuple(c[0] for c in columns),show='headings',selectmode='browse',height=height)
    for key,title,width in columns:listing.heading(key,text=title);listing.column(key,width=width,minwidth=35)
    bar=ttk.Scrollbar(frame,orient='vertical',command=listing.yview);listing.configure(yscrollcommand=bar.set)
    bar.pack(side='right',fill='y');listing.pack(side='left',fill='both',expand=True)
    return listing


def row_panel(app,parent,rows,aid,linked=False):
    pane=ttk.Panedwindow(parent,orient='vertical');pane.pack(fill='both',expand=True)
    top=ttk.Frame(pane);bottom=ttk.Frame(pane);pane.add(top,weight=1);pane.add(bottom,weight=2)
    listing=tree(top,[('source','Source',130),('row','Group / row',175),('match','Reference',85),('summary','Label / contents',330)],height=7)
    detail=readonly_text(bottom)
    for i,row in enumerate(rows):
        mentions=app.asset_index.mentions_by_row[row.key]
        polarity=('Mixed' if (aid,False) in mentions and (aid,True) in mentions else 'Negated' if (aid,True) in mentions else 'Positive')
        if row in app.asset_index.definitions.get(aid,[]):polarity='Definition'
        listing.insert('','end',iid=str(i),values=(row.source,GROUP_NAMES.get(row.group,row.group)+f' #{row.index}',
                                               'Linked record' if linked else polarity,(row.label+' · ' if row.label else '')+summary(row)))
    def select(event=None):
        if listing.selection():set_text(detail,row_details(app,rows[int(listing.selection()[0])]))
    listing.bind('<<TreeviewSelect>>',select)
    if rows:listing.selection_set('0');select()
    else:set_text(detail,'No linked records found in the loaded tables.' if linked else 'No appearance-table rows mention this AID in the loaded files.')
    def edit_row(event=None):
        if not listing.selection():return
        row=rows[int(listing.selection()[0])]
        from appearance_data import SECTIONS
        key=next(key for key,spec in SECTIONS.items() if spec[1]==row.group)
        app.switch_module('Appearance rules',f'{key}:{row.index}',source_file=row.source)
    ttk.Button(parent,text='Edit selected row',command=edit_row).pack(anchor='e',pady=(5,0))
    listing.bind('<Double-1>',edit_row);listing.bind('<Return>',edit_row)
    if linked:app.aid_edit_linked=edit_row
    else:app.aid_edit_rule=edit_row
    return listing,detail


def show_aid(app,aid):
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.widgets={};app.current=None;app.current_aid=aid
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    result=app.translator.resolve(aid)
    app.heading.set(result.text.removeprefix('Appearance: ') if result.source!='Untranslated' else aid)
    users=app.asset_index.users.get(aid,[]);rows=app.asset_index.rows_by_aid.get(aid,[])
    direct=app.asset_index.direct_count(aid)
    selected_source=getattr(app,'current_aid_source',None)
    app.details.set(f'{aid} · {direct} direct owners · {len(rows)} table rows'+(' · '+selected_source if selected_source else '')+' · current rules')
    tabs={}
    for title in ('Who uses it','Rules & flags','Linked data','Other references','Coverage'):
        tab=ttk.Frame(app.notebook,padding=7);app.notebook.add(tab,text=title);tabs[title]=tab
    tab=tabs['Who uses it']
    ttk.Label(tab,text='Current character/class/item/legion flags and related-character links. Links do not prove the final appearance.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    listing=tree(tab,[('name','Owner / English',165),('kind','Relationship',125),('field','Field',165),('id','Raw ID',260)],height=15)
    for i,user in enumerate(users):
        listing.insert('','end',iid=str(i),values=(name_for(app,user.module,user.record),user.relationship,user.field,user.record))
    evidence=tk.StringVar(value='Select a row to see the exact flag or linked-character path.')
    ttk.Label(tab,textvariable=evidence,style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=6)
    def selected(event=None,listing=listing):
        if listing.selection():
            user=users[int(listing.selection()[0])];evidence.set(user.module+' · '+user.text)
    def open_user(event=None,listing=listing):
        if listing.selection():
            user=users[int(listing.selection()[0])]
            target='Items' if user.module.startswith('Items') else user.module
            app.module_tabs[target]=0;app.switch_module(target,user.record,source_file=app.documents[user.module].filename)
    listing.bind('<<TreeviewSelect>>',selected);listing.bind('<Double-1>',open_user);listing.bind('<Return>',open_user)
    ttk.Button(tab,text='Open selected entry',command=open_user).pack(anchor='e')
    if not users:evidence.set('No direct character/class/item assignments or related-character links were found. Check the rules and other source references.')
    app.aid_users_tree=listing
    tab=tabs['Rules & flags']
    ttk.Label(tab,text='Current definitions and AID mentions, including negated tests. Select a row and choose Edit selected row. Original order stays fixed.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    app.aid_rules_tree,app.aid_rule_detail=row_panel(app,tab,rows,aid)
    tab=tabs['Linked data']
    ttk.Label(tab,text='Named links from positive references, including FID voice/portrait data. Alternatives are shown, not a resolved outfit.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    app.aid_linked_tree,app.aid_linked_detail=row_panel(app,tab,app.asset_index.linked_rows(aid),aid,True)
    tab=tabs['Other references']
    ttk.Label(tab,text='Original on-disk string occurrences, not confirmed assignments. Current unsaved assignments and appearance rules are shown in the other tabs.',
              style='Hint.TLabel',wraplength=740).pack(anchor='w',pady=(0,6))
    pane=ttk.Panedwindow(tab,orient='vertical');pane.pack(fill='both',expand=True)
    upper=ttk.Frame(pane);lower=ttk.Frame(pane);pane.add(upper,weight=1);pane.add(lower,weight=1)
    refs=app.asset_index.evidence.get(aid,[])
    listing=tree(upper,[('source','Source file',230),('offset','String offset',100),('kind','Mention',90),('text','Raw string',320)],height=8)
    detail=readonly_text(lower)
    for i,ref in enumerate(refs):listing.insert('','end',iid=str(i),values=(ref.source,f'0x{ref.offset:X}','Negated' if ref.negative else 'Text',ref.text))
    def ref_select(event=None):
        if listing.selection():
            ref=refs[int(listing.selection()[0])]
            set_text(detail,f'{ref.source} · string offset 0x{ref.offset:X}\n\n{ref.text}\n\nEnglish / glossary:\n{app.translator.resolve(ref.text).text}')
    listing.bind('<<TreeviewSelect>>',ref_select)
    if refs:listing.selection_set('0');ref_select()
    else:set_text(detail,'No other readable GameData string-pool references found.')
    app.aid_source_tree=listing
    coverage=app.asset_index.coverage()
    lines=['AID browser coverage','',f'{coverage["aids"]} distinct AIDs discovered.',
           f'{len(coverage["files"])} readable GameData files; {len(coverage["errors"])} files skipped.','',
           'Sources: AssetTable*.bin groups, live Person/Job/Item asset-flag fields and readable GameData .bin string pools.',
           'Appearance tables are editable in Module → Appearance rules and included in projects/mod exports when loaded.',
           'Rules are conditional and can overlap. This browser does not simulate precedence, evaluate conditions or predict final appearances.',
           'Character reuse and original-character links are shown as relationships, not proven inherited appearance.',
           'Scripts, compressed files and runtime-generated flags are not evaluated. Missing assets are not evidence that an AID is invalid.','',
           'This AID was found in:']+list(app.asset_index.sources_for(aid))+['','Appearance tables:']
    for source,groups in coverage['asset_tables'].items():
        lines.append(source)
        lines.extend('  '+GROUP_NAMES.get(group,group)+': '+str(count) for group,count in groups.items())
    lines+=['','Skipped files:']+[source+': '+error for source,error in coverage['errors']]
    lines+=['','Readable source files:']+coverage['files']
    readonly_text(tabs['Coverage'],'\n'.join(lines))
    app.notebook.select(min(active,len(tabs)-1))
