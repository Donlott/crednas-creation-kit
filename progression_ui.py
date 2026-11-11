"""GLID automatic progression: category rows containing level 1 through 80+ values."""
import tkinter as tk
from tkinter import ttk


CATEGORY_HINTS={0:'Class names (observed)',2:'Mount values (observed)',
                **{i:'Item names (observed)' for i in range(4,9)}}


def row_title(app,row):
    category=app.doc.value(row,app.doc.by_offset[0x20])
    return f'Entry {row.index} · category {category} · {CATEGORY_HINTS.get(category,"Meaning unverified")}'


def refresh_levels(app):
    if app.learning_row is None or not hasattr(app,'progression_tree') or not app.progression_tree.winfo_exists():return
    row=app.learning_row;listing=app.progression_tree;selected=app.progression_level
    expected=[]
    for level,field in enumerate(app.doc.fields[1:],1):
        raw=app.doc.value(row,field)
        if not raw and not app.progression_show_empty.get() and level!=selected:continue
        key=str(level);expected.append(key);result=app.translate_value(raw)
        values=(f'{level}+' if level==80 else level,result.text if raw else '—',raw)
        if listing.exists(key):listing.item(key,values=values)
        else:listing.insert('','end',iid=key,values=values)
        listing.move(key,'','end')
    for key in listing.get_children():
        if key not in expected:listing.delete(key)
    if listing.exists(str(selected)):listing.selection_set(str(selected))
    rows=app.doc.rows_by_table[app.current.pid]
    app.progression_rows.configure(values=[row_title(app,r) for r in rows])
    app.progression_rows.current(row.index)
    app.progression_hint.set(CATEGORY_HINTS.get(app.doc.value(row,app.doc.by_offset[0x20]),'Category meaning unverified'))


def show_level(app,level):
    app.clear_previews();app.widgets={};app.progression_level=level
    for child in app.progression_form.winfo_children():child.destroy()
    row=app.learning_row
    header=ttk.Frame(app.progression_form);header.pack(fill='x',pady=(0,6))
    ttk.Label(header,text=f'Level {"80+" if level==80 else level}',font=('DejaVu Sans',9,'bold')).pack(side='left',padx=(0,18))
    ttk.Label(header,text='Category code').pack(side='left',padx=(0,5))
    field=app.doc.by_offset[0x20];category_value=tk.StringVar(value=str(app.doc.value(row,field)))
    widget=ttk.Entry(header,width=5,justify='right',textvariable=category_value)
    widget.pack(side='left',padx=(0,12));app.widgets[0x20]=(field,widget)
    ttk.Label(header,textvariable=app.progression_hint,style='Hint.TLabel').pack(side='left')
    body=ttk.Frame(app.progression_form);body.pack(fill='x')
    for col,label in enumerate(('Field','Raw name / value','English / explanation')):
        ttk.Label(body,text=label,style='Hint.TLabel').grid(row=0,column=col,sticky='w')
    app.reference_row(body,1,app.doc.by_offset[0x28+(level-1)*8],row)
    body.columnconfigure(1,weight=1,uniform='progression');body.columnconfigure(2,weight=1,uniform='progression')
    def category_changed(*_):
        for offset in app.previews:app.queue_preview(offset)
    callback=category_value.trace_add('write',category_changed)
    app.preview_bindings.append((category_value,callback))


def select_level(app,event=None):
    selection=app.progression_tree.selection()
    if not selection:return
    level=int(selection[0])
    if level==app.progression_level:return
    old=app.progression_level
    if not app.apply(True):app.progression_tree.selection_set(str(old));return
    show_level(app,level)
    # Applying the old form restores its selection; now display the requested level.
    app.progression_tree.selection_set(str(level))


def show_table(app,record):
    active=app.notebook.index('current') if app.notebook.tabs() else 0
    app.clear_previews();app.widgets={};app.current=record;app.learning_row=None
    for tab in app.notebook.tabs():app.nametowidget(tab).destroy()
    app.heading.set(app.display(record));rows=app.doc.rows_by_table[record.pid]
    app.details.set(f'{record.pid} · {len(rows)} category rows · table ID and row count fixed')
    entries=ttk.Frame(app.notebook,padding=7);app.notebook.add(entries,text='Progression')
    usage=ttk.Frame(app.notebook,padding=7);app.notebook.add(usage,text='Used by')
    ttk.Label(entries,text='Stored level entries only; blank cells stay blank. No inheritance or automatic-growth simulation.',
              style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=(0,6))
    bar=ttk.Frame(entries);bar.pack(fill='x',pady=(0,6))
    ttk.Label(bar,text='Category row').pack(side='left',padx=(0,6))
    chooser=ttk.Combobox(bar,state='readonly',width=47);chooser.pack(side='left',fill='x',expand=True)
    app.progression_rows=chooser;app.progression_hint=tk.StringVar()
    app.progression_show_empty=tk.BooleanVar(value=True)
    def toggle_empty():
        if not app.apply(True):app.progression_show_empty.set(not app.progression_show_empty.get());return
        refresh_levels(app)
    ttk.Checkbutton(bar,text='Show empty levels',variable=app.progression_show_empty,command=toggle_empty).pack(side='right',padx=(8,0))
    from aid_ui import tree,name_for
    app.progression_tree=tree(entries,[('level','Level',65),('name','English / explanation',260),('raw','Raw name / value',290)],height=12)
    app.progression_form=ttk.Frame(entries,padding=(0,9,0,3));app.progression_form.pack(fill='x')
    tools=ttk.Frame(entries);tools.pack(fill='x',pady=(6,0));app.progression_tools=tools
    def choose_row(event=None):
        index=chooser.current()
        if index<0 or app.learning_row and index==app.learning_row.index:return
        if not app.apply(True):chooser.current(app.learning_row.index);return
        app.learning_row=rows[index];app.progression_level=1
        show_level(app,1);refresh_levels(app);app.progression_tree.see('1')
    chooser.bind('<<ComboboxSelected>>',choose_row)
    app.progression_tree.bind('<<TreeviewSelect>>',lambda event:select_level(app,event))
    def copy_row():
        if not app.learning_row or not app.apply(True):return
        app.progression_clipboard={f.offset:app.doc.value(app.learning_row,f) for f in app.doc.fields}
        app.status.set('Copied category and all 80 level values. Paste into an existing GLID row.')
    def paste_row():
        values=getattr(app,'progression_clipboard',None)
        if not app.learning_row or values is None or not app.apply(True):return
        before=dict(app.doc.changes)
        try:
            for offset,value in values.items():app.doc.set(app.learning_row,app.doc.by_offset[offset],value)
        except Exception as exc:app.doc.changes=before;app.error(exc);return
        show_level(app,app.progression_level);app.apply()
    def restore_level(clear=False):
        if not app.learning_row or not app.apply(True):return
        field=app.doc.by_offset[0x28+(app.progression_level-1)*8]
        app.doc.set(app.learning_row,field,'' if clear else app.doc.original(app.learning_row,field))
        show_level(app,app.progression_level);app.apply()
    for text,command in [('Copy row',copy_row),('Paste row',paste_row),('Clear level',lambda:restore_level(True)),('Reset level',restore_level)]:
        ttk.Button(tools,text=text,command=command).pack(side='left',padx=(0,5))
    ttk.Label(entries,text='The chooser preserves bare names (no JID_/IID_ prefix). Category meanings are inferred from existing data.',
              style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=(7,0))
    if rows:
        app.learning_row=rows[0];app.progression_level=1
        show_level(app,1);refresh_levels(app)
    else:ttk.Label(app.progression_form,text='No category rows. Row counts are preserved.').pack(anchor='w')
    ttk.Label(usage,text='Current direct character progression references. Scripts, difficulty rules and runtime selection are not evaluated.',
              style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=(0,6))
    listing=tree(usage,[('name','Character',185),('field','Field',150),('id','Raw PID',330)],height=15);owners=[]
    document=app.documents.get('Characters')
    if document:
        field=document.by_offset[0x128]
        for owner in document.records:
            if document.value(owner,field)==record.pid:
                listing.insert('','end',iid=str(len(owners)),values=(name_for(app,'Characters',owner.pid),field.label,owner.pid))
                owners.append(owner.pid)
    ttk.Label(usage,text=f'{len(owners)} direct character records found. Shared GLIDs affect every referencing character.',style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=5)
    def open_owner(event=None):
        if listing.selection():app.switch_module('Characters',owners[int(listing.selection()[0])])
    listing.bind('<Double-1>',open_owner);listing.bind('<Return>',open_owner)
    ttk.Button(usage,text='Open selected entry',command=open_owner).pack(anchor='e')
    app.progression_users_tree=listing
    app.notebook.select(min(active,1))
