"""Route-grouped tutorial catalog with explicit dependency and migration status."""
import tkinter as tk
from tkinter import ttk,messagebox
from branding import APP_NAME
from tutorial_data import PRESETS,inspect_state,apply_choices,load_sources


LABELS={'normal':'Off · testable','disabled':'On · experimental','legacy':'Migration needed','repair':'Unlock checks needed',
        'blocked':'Needs tracing','unavailable':'Source / edit conflict'}


def open_editor(app):
    if not app.documents:app.error('Open your original game data first.');return
    if not app.apply(True):return
    existing=getattr(app,'tutorial_window',None)
    if existing and existing.winfo_exists():existing.lift();return existing
    try:
        clean=app.session_state()==app.saved_state
        load_sources(app.documents,app.sources,app.data_directory)
        if clean:app.saved_state=app.session_state()
        window=TutorialEditor(app);app.tutorial_window=window;return window
    except Exception as exc:app.error(str(exc))


class TutorialEditor(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.current=None
        self.title(APP_NAME+' · Forced tutorials');self.geometry('980x690');self.minsize(800,620)
        self.transient(app);self.grab_set()
        self.variables={p.key:tk.BooleanVar() for p in PRESETS};self.states={}
        self.search=tk.StringVar();self.route=tk.StringVar(value='All routes');self.selected=tk.BooleanVar()
        self.heading=tk.StringVar(value='Select a sequence');self.detail=tk.StringVar();self.reason=tk.StringVar()
        self.notice=tk.StringVar(value='28 groups · 39 route-specific entries. Unverified completion paths are unavailable.')
        body=ttk.Frame(self,padding=10);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Forced tutorials · progression checks',style='Title.TLabel').pack(anchor='w')
        self.intro_label=ttk.Label(body,text='Testable options retain native timeline events and scheduling fields. File validation cannot guarantee runtime clock or flag behavior. '
                  'Unlock checks remain in exported projects when a bypass is turned off, for saves that skipped the introduction. Unresolved sequences remain unavailable.',wraplength=930)
        self.intro_label.pack(fill='x',pady=(5,8))
        bar=ttk.Frame(body);bar.pack(fill='x',pady=(0,5))
        ttk.Entry(bar,textvariable=self.search).pack(side='left',fill='x',expand=True,padx=(0,6))
        ttk.Combobox(bar,textvariable=self.route,values=('All routes','Cai','Dietrich','Theodora','Leda','Prologue'),state='readonly',width=16).pack(side='right')
        area=ttk.Frame(body);area.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(area,columns=('number','chapter','state'),selectmode='browse',height=12)
        self.tree.heading('#0',text='Sequence');self.tree.column('#0',width=420,minwidth=260)
        for key,title,width in [('number','List #',55),('chapter','Chapter',65),('state','Status',170)]:
            self.tree.heading(key,text=title);self.tree.column(key,width=width,minwidth=width,stretch=False)
        scroll=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.select)
        self.tree.bind('<Double-1>',lambda event:self.toggle());self.tree.bind('<space>',lambda event:self.toggle())
        panel=ttk.Frame(body,padding=(0,8));panel.pack(fill='x')
        ttk.Label(panel,textvariable=self.heading,font=('DejaVu Sans',10,'bold')).pack(anchor='w')
        self.check=ttk.Checkbutton(panel,text='Bypass forced guidance (experimental)',variable=self.selected,command=self.choose,state='disabled')
        self.check.pack(anchor='w',pady=3)
        self.detail_label=ttk.Label(panel,textvariable=self.detail,wraplength=930);self.detail_label.pack(fill='x')
        self.reason_label=ttk.Label(panel,textvariable=self.reason,style='Hint.TLabel',wraplength=930);self.reason_label.pack(fill='x',pady=(3,0))
        self.notice_label=ttk.Label(body,textvariable=self.notice,wraplength=930);self.notice_label.pack(fill='x',pady=5)
        actions=ttk.Frame(body);actions.pack(fill='x',side='bottom')
        ttk.Button(actions,text='Close',command=self.destroy).pack(side='right')
        ttk.Button(actions,text='Apply',command=self.apply).pack(side='right',padx=5)
        ttk.Button(actions,text='Save project…',command=lambda:self.action(app.save_project)).pack(side='left')
        ttk.Button(actions,text='Export mod…',command=lambda:self.action(app.export)).pack(side='left',padx=5)
        self.search.trace_add('write',lambda *_:self.filter());self.route.trace_add('write',lambda *_:self.filter())
        body.bind('<Configure>',lambda e:[w.configure(wraplength=max(300,e.width-24)) for w in (self.intro_label,self.notice_label,self.detail_label,self.reason_label)])
        self.refresh()

    def refresh(self):
        for preset in PRESETS:
            state,reason=inspect_state(self.app.documents,preset);self.states[preset.key]=(state,reason)
            self.variables[preset.key].set(state in ('disabled','legacy','repair'))
        self.filter()

    def filter(self):
        selected=self.current;self.tree.delete(*self.tree.get_children());q=self.search.get().casefold()
        for route in ('Cai','Dietrich','Theodora','Leda','Prologue'):
            peers=[p for p in PRESETS if p.route==route and self.route.get() in ('All routes',route)
                   and q in (p.title+' '+p.route+' '+str(p.group)).casefold()]
            if not peers:continue
            self.tree.insert('','end',iid='route:'+route,text=route,open=True)
            for p in sorted(peers,key=lambda p:(p.chapter or 99,p.group)):
                state=self.states.get(p.key,('unavailable',''))[0];label=LABELS[state]
                if state in ('normal','disabled') and self.variables[p.key].get()!=(state=='disabled'):label='Pending '+('on' if self.variables[p.key].get() else 'off')
                self.tree.insert('route:'+route,'end',iid=p.key,text=p.title,values=(p.group,p.chapter or 'Quest',label))
        if selected and self.tree.exists(selected):self.tree.selection_set(selected);self.tree.see(selected)
        else:
            self.current=None;self.check.configure(state='disabled');self.heading.set('Select a sequence');self.detail.set('');self.reason.set('')

    def select(self,event=None):
        keys=self.tree.selection()
        if not keys or keys[0].startswith('route:'):
            self.current=None;self.check.configure(state='disabled');return
        self.current=keys[0];p=next(p for p in PRESETS if p.key==self.current)
        state,reason=self.states[p.key];self.selected.set(self.variables[p.key].get())
        self.check.configure(state='normal' if state in ('normal','disabled','legacy','repair') else 'disabled')
        self.heading.set(f'#{p.group} · {p.route} · '+p.title)
        self.detail.set(p.description or 'No executable completion recipe is supplied until the dependencies below are accounted for.')
        self.reason.set(reason)

    def choose(self):
        if self.current and self.states[self.current][0] in ('normal','disabled','legacy','repair'):
            self.variables[self.current].set(self.selected.get());self.filter();self.select()

    def toggle(self):
        self.select()
        if self.current and str(self.check.cget('state'))!='disabled':
            self.selected.set(not self.selected.get());self.choose()

    def apply(self):
        try:
            choices={key:value.get() for key,value in self.variables.items() if self.states[key][0] in ('normal','disabled','legacy','repair')}
            count=apply_choices(self.app.documents,choices)
            if getattr(self.app,'active_module',None)=='Events' and getattr(self.app,'learning_row',None):
                from event_ui import show_entry,refresh_entries
                show_entry(self.app,self.app.learning_row);refresh_entries(self.app)
            self.refresh();text=f'{count} option(s) changed. Save a project or export a separate test mod.'
            self.notice.set(text);self.app.status.set(text);return True
        except Exception as exc:messagebox.showerror('Forced tutorials',str(exc),parent=self);return False

    def action(self,callback):
        if self.apply():callback()
        if self.winfo_exists():self.grab_set()
