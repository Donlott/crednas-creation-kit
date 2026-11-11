"""Compact LID editor with append-only entry creation and reference browsing."""
import tkinter as tk
from tkinter import ttk,simpledialog


def list_owners(app,key):
    doc=app.documents.get('Characters')
    if doc is None:return []
    field=doc.by_offset[0x88]
    return [('Characters',row.pid) for row in doc.records if key in doc.value(row,field)]


def refresh_entries(app):
    if app.doc is None or app.current is None or not hasattr(app,'learning_tree'):return
    if not app.learning_tree.winfo_exists():return
    rows=app.doc.rows_by_table[app.current.pid]
    valid={row.pid for row in rows}
    stale=[key for key in app.learning_tree.get_children() if key not in valid]
    if stale:app.learning_tree.delete(*stale)
    for row in rows:
        value=lambda offset:app.doc.value(row,app.doc.by_offset[offset])
        sid=value(0x28);result=app.translator.resolve(sid)
        values=(row.index,value(0x20),value(0x21),value(0x22),
                result.text if result.source!='Untranslated' else '',sid,len(value(0x38)))
        if app.learning_tree.exists(row.pid):app.learning_tree.item(row.pid,values=values)
        else:app.learning_tree.insert('','end',iid=row.pid,values=values)


def show_row(app,row):
    app.clear_previews();app.widgets={};app.learning_row=row
    for child in app.learning_form.winfo_children():child.destroy()
    header=ttk.Frame(app.learning_form);header.pack(fill='x',pady=(0,6))
    ttk.Label(header,text=f'Entry {row.index}',font=('DejaVu Sans',9,'bold')).pack(side='left',padx=(0,12))
    for offset,label in ((0x20,'Level'),(0x21,'Skill type code'),(0x22,'Skill level code')):
        field=app.doc.by_offset[offset]
        ttk.Label(header,text=label).pack(side='left',padx=(0,4))
        widget=ttk.Entry(header,width=5,justify='right');widget.insert(0,str(app.doc.value(row,field)))
        widget.pack(side='left',padx=(0,12));app.widgets[offset]=(field,widget)
    body=ttk.Frame(app.learning_form);body.pack(fill='x')
    for column,text in ((0,'Field'),(1,'Raw reference / Japanese'),(2,'English / explanation')):
        ttk.Label(body,text=text,style='Hint.TLabel').grid(row=0,column=column,sticky='w',pady=(0,4))
    for index,offset in enumerate((0x28,0x38),1):app.reference_row(body,index,app.doc.by_offset[offset],row)
    body.columnconfigure(1,weight=1,uniform='learning');body.columnconfigure(2,weight=1,uniform='learning')


def select_row(app,event=None):
    selection=app.learning_tree.selection()
    if not selection:return
    row=app.doc.by_pid[selection[0]]
    if app.learning_row and row.pid==app.learning_row.pid:return
    if not app.apply(True):
        if app.learning_row:app.learning_tree.selection_set(app.learning_row.pid)
        return
    show_row(app,row)


def show_table(app,record):
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.current=record;app.learning_row=None;app.widgets={}
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(app.display(record))
    rows=app.doc.rows_by_table[record.pid]
    added=len(app.doc.added_entries.get(record.pid,()))
    app.details.set(f'{record.pid} · {len(rows)} entries'+(f' · {added} added' if added else '')+(' · new list' if record.pid in app.doc.new_lists else ' · original list'))
    entries=ttk.Frame(app.notebook,padding=7);app.notebook.add(entries,text='Entries')
    usage=ttk.Frame(app.notebook,padding=7);app.notebook.add(usage,text='Used by')
    ttk.Label(entries,text='Additions are experimental: test the exported mod in game. Type/level codes remain raw; conditions use one ID per line.',
              style='Hint.TLabel',wraplength=720).pack(anchor='w',pady=(0,6))
    pane=ttk.Panedwindow(entries,orient='vertical');pane.pack(fill='both',expand=True)
    upper=ttk.Frame(pane);lower=ttk.Frame(pane,padding=(0,8,0,0));pane.add(upper,weight=2);pane.add(lower,weight=1)
    frame=ttk.Frame(upper);frame.pack(fill='both',expand=True)
    columns=('row','level','type','rank','name','sid','conditions')
    listing=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse',height=9)
    for key,title,width in [('row','#',32),('level','Level',45),('type','Type code',70),('rank','Skill level',70),
                            ('name','English / explanation',210),('sid','Raw SID',230),('conditions','Conditions',80)]:
        listing.heading(key,text=title);listing.column(key,width=width,minwidth=28)
    scroll=ttk.Scrollbar(frame,orient='vertical',command=listing.yview);scroll.pack(side='right',fill='y')
    listing.configure(yscrollcommand=scroll.set);listing.pack(side='left',fill='both',expand=True)
    horizontal=ttk.Scrollbar(upper,orient='horizontal',command=listing.xview);horizontal.pack(fill='x');listing.configure(xscrollcommand=horizontal.set)
    app.learning_tree=listing;app.learning_form=lower
    refresh_entries(app)
    listing.bind('<<TreeviewSelect>>',lambda event:select_row(app,event))
    tools=ttk.Frame(entries);tools.pack(fill='x',pady=(6,0))
    def copy_entry():
        if not app.learning_row or not app.apply(True):return
        app.learning_clipboard={f.offset:app.doc.value(app.learning_row,f) for f in app.doc.fields}
        app.status.set('Copied learning entry values; select an entry to paste into.')
    def paste_entry():
        if not app.learning_row or not app.learning_clipboard or not app.apply(True):return
        before=dict(app.doc.changes)
        try:
            for offset,value in app.learning_clipboard.items():app.doc.set(app.learning_row,app.doc.by_offset[offset],value)
        except Exception as exc:app.doc.changes=before;app.error(exc);return
        show_row(app,app.learning_row);app.apply()
    def swap(direction):
        if not app.learning_row or not app.apply(True):return
        index=app.learning_row.index;other=index+direction
        if not 0<=other<len(rows):return
        a,b=rows[index],rows[other]
        values_a={f.offset:app.doc.value(a,f) for f in app.doc.fields};values_b={f.offset:app.doc.value(b,f) for f in app.doc.fields}
        before=dict(app.doc.changes)
        try:
            for f in app.doc.fields:app.doc.set(a,f,values_b[f.offset]);app.doc.set(b,f,values_a[f.offset])
        except Exception as exc:app.doc.changes=before;app.error(exc);return
        show_row(app,b);listing.selection_set(b.pid);listing.see(b.pid);app.apply()
    def add_entry(duplicate=False,undo=False):
        if not app.apply(True):return
        try:
            if undo:
                app.doc.remove_last_added(record.pid)
                remaining=app.doc.rows_by_table[record.pid];target=remaining[-1] if remaining else None
            else:
                if duplicate and not app.learning_row:return
                target=app.doc.duplicate_entry(app.learning_row) if duplicate else app.doc.append_entry(record.pid)
        except Exception as exc:app.error(exc);return
        show_table(app,record)
        if target:
            target=app.doc.by_pid[target.pid]
            app.learning_tree.selection_set(target.pid);app.learning_tree.see(target.pid);show_row(app,target)
        app.filter()
        app.status.set('Last addition removed.' if undo else 'Entry appended. Choose its skill and requirements, then save a project or export a mod.')
    app.learning_actions={}
    for row,actions in enumerate([
            [('Add entry',add_entry),('Duplicate entry',lambda:add_entry(True)),('Undo last addition',lambda:add_entry(undo=True))],
            [('Copy entry',copy_entry),('Paste values',paste_entry),('Swap ↑',lambda:swap(-1)),('Swap ↓',lambda:swap(1))]]):
        for column,(text,action) in enumerate(actions):
            button=ttk.Button(tools,text=text,command=action);button.grid(row=row,column=column,sticky='w',padx=(0,5),pady=2)
            app.learning_actions[text]=button
    if not rows:app.learning_actions['Duplicate entry'].configure(state='disabled')
    if not added:app.learning_actions['Undo last addition'].configure(state='disabled')
    list_tools=ttk.Frame(entries);list_tools.pack(before=pane,fill='x',pady=(0,5))
    def change_list(duplicate=False,remove=False):
        if not app.apply(True):return
        try:
            if remove:
                owners=list_owners(app,record.pid)
                if owners:app.error(f'This list is assigned to {len(owners)} characters. Remove their learning-list references first.');return
                app.doc.remove_list(record.pid);target=app.doc.collections[-1].pid
            else:
                stem=record.pid+'_Copy' if duplicate else 'LID_Custom'
                suggested=stem;number=2
                while suggested in app.doc.tables_by_id or suggested in app.doc.labels:
                    suggested=f'{stem}_{number}';number+=1
                key=simpledialog.askstring('Duplicate learning list' if duplicate else 'New learning list',
                    'Enter a unique LID_ ID for the new list. Existing IDs stay unchanged.',
                    initialvalue=suggested,parent=app)
                if key is None:return
                target=app.doc.create_list(key,record.pid if duplicate else None).pid
        except Exception as exc:app.error(exc);return
        app.current=None;app.learning_row=None;app.widgets={};app.suggestion_cache.clear()
        app.switch_module('Learning tables',target);app.notebook.select(0)
        app.status.set('New list removed.' if remove else 'Learning list created. Assign its LID in Characters → Learning tables to use it, then save or export.')
    app.learning_list_actions={}
    for label,command in [('New list…',change_list),('Duplicate list…',lambda:change_list(True)),('Remove new list',lambda:change_list(remove=True))]:
        button=ttk.Button(list_tools,text=label,command=command);button.pack(side='left',padx=(0,5))
        app.learning_list_actions[label]=button
    if record.pid not in app.doc.new_lists:app.learning_list_actions['Remove new list'].configure(state='disabled')
    if rows:listing.selection_set(rows[0].pid);show_row(app,rows[0])
    else:ttk.Label(lower,text='This list has no entries. Use Add entry to create its first row.').pack(anchor='w')
    # Direct references only. Do not imply that GLID/scripts have been evaluated.
    ttk.Label(usage,text='Current character learning-table references. Scripts and GLID progression are not scanned here.',
              style='Hint.TLabel',wraplength=720).pack(anchor='w',pady=(0,6))
    from aid_ui import tree,name_for
    owners=list_owners(app,record.pid)
    user_tree=tree(usage,[('name','Character / class',180),('field','Field',155),('id','Raw ID',330)],height=15)
    for i,(module,pid) in enumerate(owners):
        user_tree.insert('','end',iid=str(i),values=(name_for(app,module,pid),'Learning tables',pid))
    # Class learning references are not a primary Job.bin field in this layout.
    ttk.Label(usage,text=f'{len(owners)} direct character records found.',style='Hint.TLabel').pack(anchor='w',pady=5)
    def open_owner(event=None):
        if user_tree.selection():app.switch_module(*owners[int(user_tree.selection()[0])])
    user_tree.bind('<Double-1>',open_owner);user_tree.bind('<Return>',open_owner)
    ttk.Button(usage,text='Open selected entry',command=open_owner).pack(anchor='e')
    app.learning_users_tree=user_tree
    app.notebook.select(min(active,1))
