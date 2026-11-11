"""Class creation tools and navigation for explicit live class references."""
import tkinter as tk
from tkinter import ttk,simpledialog
from class_index import uses


def tools(app,body,record):
    bar=ttk.Frame(body);bar.grid(row=0,column=0,columnspan=4,sticky='ew',pady=(0,6))
    def create(duplicate=False,remove=False):
        if not app.apply(True):return
        doc=app.doc
        try:
            if remove:
                incoming=[u for u in uses(record.pid,app.documents) if not (u.source==doc.filename and u.record==record.pid)]
                if incoming:app.error(f'This class has {len(incoming)} current references in loaded data. Clear or replace them first; see Used by.');return
                doc.remove_class(record.pid);target=doc.records[0].pid
            else:
                stem=record.pid+'_Copy' if duplicate else 'JID_Custom';key=stem;number=2
                while key in doc.by_pid or key in doc.labels:key=f'{stem}_{number}';number+=1
                key=simpledialog.askstring('Duplicate class' if duplicate else 'New class',
                    'Enter a unique JID_ ID. The class is created in Job.bin.',initialvalue=key,parent=app)
                if key is None:return
                target=doc.create_class(key,record.pid if duplicate else None).pid
        except Exception as exc:app.error(exc);return
        app.current=None;app.widgets={};app.suggestion_cache.clear();app.clear_previews();app.rebuild_translator()
        app.switch_module('Classes',target);app.notebook.select(0)
        app.status.set('New class removed.' if remove else 'Class created. Configure its stats, skills and links, then assign it or set promotion/progression references; save or export.')
    app.class_creation_actions={}
    for label,command in [('New class…',create),('Duplicate class…',lambda:create(True)),('Remove new class',lambda:create(remove=True))]:
        button=ttk.Button(bar,text=label,command=command);button.pack(side='left',padx=(0,5));app.class_creation_actions[label]=button
    if record.pid not in app.doc.new_classes:app.class_creation_actions['Remove new class'].configure(state='disabled')
    ttk.Label(body,text='Creation is experimental; test the exported mod in game. Copies retain all current values and links. Name/help fields are message keys.',
              style='Hint.TLabel',wraplength=700).grid(row=1,column=0,columnspan=4,sticky='w',pady=(0,6))


def usage(app,body,record,find_uses=uses,kind="class",auto_refresh=True):
    from aid_ui import name_for
    hint='Current explicit JID references and observed GLID class-name cells.' if kind=='class' else 'Current explicit PID references in supported loaded editable fields. Headers and indirect identifiers are not scanned.'
    ttk.Label(body,text=hint+' Loaded script constants are included; unopened scripts, unsupported groups and runtime rules are not evaluated.',style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=(0,8))
    frame=ttk.Frame(body);frame.pack(fill='both',expand=True)
    listing=ttk.Treeview(frame,columns=('name','kind','pid'),show='headings',height=15)
    for key,label,width in [('name','Record / English',180),('kind','Source / reference field',285),('pid','Raw record ID',280)]:
        listing.heading(key,text=label);listing.column(key,width=width)
    listing.pack(side='left',fill='both',expand=True)
    bar=ttk.Scrollbar(frame,orient='vertical',command=listing.yview);bar.pack(side='right',fill='y');listing.configure(yscrollcommand=bar.set)
    targets=[];count=tk.StringVar()
    def refresh():
        if not app.apply(True):return
        listing.delete(*listing.get_children());targets[:]=find_uses(record.pid,app.documents)
        for i,use in enumerate(targets):
            key=next((k for k,d in app.documents.items() if d.filename==use.source),None)
            name=name_for(app,key,use.record) if key and use.module in ('Characters','Classes','Items','Skills') else app.translator.resolve(use.table or use.record).text
            listing.insert('','end',iid=str(i),values=(name,use.source+' · '+use.field,use.record))
        count.set(f'{len(targets)} stored references; counts are occurrences, not guaranteed runtime assignments.')
    def navigate(event=None):
        if not listing.selection():return
        use=targets[int(listing.selection()[0])]
        if use.module=='GLID progression':
            if app.switch_module(use.module,use.table):
                from progression_ui import show_level,refresh_levels
                row=app.doc.rows_by_table[use.table][use.row];app.progression_rows.current(row.index)
                app.learning_row=row;show_level(app,use.level);refresh_levels(app)
        elif use.module=='Learning tables':
            if app.switch_module(use.module,use.table):
                from learning_ui import select_row
                app.learning_tree.selection_set(use.record);select_row(app)
        else:
            app.switch_module(use.module,use.record,source_file=use.source)
    ttk.Label(body,textvariable=count,style='Hint.TLabel',wraplength=700).pack(anchor='w',pady=5)
    ttk.Button(body,text='Open selected entry',command=navigate).pack(anchor='e')
    ttk.Button(body,text='Refresh references',command=refresh).pack(anchor='w')
    listing.bind('<Double-1>',navigate);listing.bind('<Return>',navigate)
    for suffix,value in [('tree',listing),('targets',targets),('open',navigate),('refresh',refresh)]:setattr(app,kind+'_usage_'+suffix,value)
    if auto_refresh:refresh()
    else:
        count.set('Open this tab or refresh to scan current references.')
        def selected(event):
            if body.winfo_exists() and app.notebook.select()==str(body.master.master):refresh()
        hook=app.notebook.bind('<<NotebookTabChanged>>',selected,add='+')
        def cleanup(event):
            if event.widget is body:
                try:app.notebook.unbind('<<NotebookTabChanged>>',hook)
                except tk.TclError:pass
        body.bind('<Destroy>',cleanup)
