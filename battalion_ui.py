"""Searchable direct-purchase battalion catalog; no source tables are rewritten."""
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from branding import APP_NAME
from battalion_data import BattalionPatch,MODULE,load_sources,catalog,source_tables,build_outputs


def open_editor(app):
    if not app.documents and not getattr(app,'data_directory',None):app.error('Open your extracted game data folder first.');return
    if not app.apply(True):return
    window=getattr(app,'battalion_window',None)
    if window and window.winfo_exists():window.lift();return window
    try:
        clean=app.session_state()==app.saved_state
        if load_sources(app.documents,app.sources,app.data_directory):app.suggestion_cache.clear();app.rebuild_translator()
        if clean:app.saved_state=app.session_state()
        window=BattalionEditor(app);app.battalion_window=window;return window
    except Exception as exc:app.error(str(exc))


class BattalionEditor(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.offers={};self.current=None
        self.title(APP_NAME+' · Buyable battalions');self.geometry('1020x720');self.minsize(850,620)
        self.transient(app);self.grab_set()
        patch=next((d for d in app.documents.values() if isinstance(d,BattalionPatch)),None)
        base=Path(app.data_directory);names=getattr(app,'names_directory',None)
        self.pending_prices=deepcopy(patch.prices) if patch else {}
        self.pending_disabled=set(patch.disabled) if patch else set();self.pending_limits=deepcopy(patch.limits) if patch else {}
        self.enabled=tk.BooleanVar(value=bool(patch and patch.enabled));self.search=tk.StringVar();self.gold=tk.StringVar();self.limit=tk.StringVar(value='0');self.available=tk.BooleanVar(value=True)
        self.main_path=tk.StringVar(value=str(patch.main_path if patch else base.parent.parent/'exefs/main'))
        self.message_path=tk.StringVar(value=str(patch.message_path if patch else (Path(names) if names else base.parent/'Msg/USen')/'Item.msbt.zst'))
        self.notice=tk.StringVar();self.selected_label=tk.StringVar(value='Select a battalion')
        body=ttk.Frame(self,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Buyable battalions · experimental',style='Title.TLabel').pack(anchor='w')
        description=ttk.Label(body,text='Buy combat battalions directly at Dagsion’s item shop on Theodora’s Part I route, from chapter 4 after the barracks unlock. They go to your barracks. Normal assignment and command requirements still apply.',wraplength=970)
        description.pack(fill='x',pady=(6,8));ttk.Checkbutton(body,text='Enable direct battalion sales',variable=self.enabled).pack(anchor='w')
        for label,var in [('Original exefs/main',self.main_path),('English Item message bank',self.message_path)]:
            line=ttk.Frame(body);line.pack(fill='x',pady=3);ttk.Label(line,text=label,width=25).pack(side='left')
            ttk.Entry(line,textvariable=var).pack(side='left',fill='x',expand=True,padx=(0,5))
            ttk.Button(line,text='Browse…',command=lambda v=var:self.browse(v)).pack(side='right')
        line=ttk.Frame(body);line.pack(fill='x',pady=(8,5));ttk.Label(line,text='Search').pack(side='left',padx=(0,6))
        ttk.Entry(line,textvariable=self.search).pack(side='left',fill='x',expand=True)
        ttk.Button(line,text='Refresh catalog',command=self.refresh_catalog).pack(side='left',padx=5)
        ttk.Button(line,text='Reset prices',command=self.reset_prices).pack(side='right')
        area=ttk.Frame(body);area.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(area,columns=('gambit','troops','command','price','available','limit'),selectmode='browse',height=12)
        self.tree.heading('#0',text='Battalion');self.tree.column('#0',width=235,minwidth=170)
        for key,label,width in [('gambit','Gambit',240),('troops','Troops',60),('command','Command',80),('price','Gold',70),('available','Sell',55),('limit','Per chapter',90)]:
            self.tree.heading(key,text=label);self.tree.column(key,width=width,minwidth=width,stretch=key=='gambit')
        scroll=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');self.tree.bind('<<TreeviewSelect>>',self.select)
        ttk.Label(body,textvariable=self.selected_label).pack(fill='x',pady=(7,3))
        line=ttk.Frame(body);line.pack(fill='x')
        ttk.Checkbutton(line,text='Sell this battalion',variable=self.available).pack(side='left')
        ttk.Label(line,text='Gold').pack(side='left',padx=(12,5));ttk.Spinbox(line,textvariable=self.gold,from_=1,to=65535,width=9).pack(side='left')
        ttk.Label(line,text='Per chapter').pack(side='left',padx=(12,5));ttk.Spinbox(line,textvariable=self.limit,from_=0,to=127,width=5).pack(side='left')
        ttk.Label(line,text='0 = unlimited').pack(side='left',padx=6);ttk.Button(line,text='Set offer',command=self.set_offer).pack(side='right')
        help_label=ttk.Label(body,text='Keep English Legion and Skill message banks beside Item. Defaults use each battalion’s stored gold price. Full barracks: no delivery, payment or stock consumption. Can be exported together with Buyable mounts. Re-export the complete mod and restart the game after changes. In-game testing is still required.',wraplength=970,style='Hint.TLabel')
        help_label.pack(fill='x',pady=7);ttk.Label(body,textvariable=self.notice,wraplength=970).pack(fill='x')
        actions=ttk.Frame(body);actions.pack(side='bottom',fill='x',pady=(7,0))
        ttk.Button(actions,text='Save project…',command=lambda:self.action(app.save_project)).pack(side='left')
        ttk.Button(actions,text='Export mod…',command=lambda:self.action(app.export)).pack(side='left',padx=6)
        ttk.Button(actions,text='Close',command=self.destroy).pack(side='right');ttk.Button(actions,text='Apply',command=self.apply).pack(side='right',padx=6)
        body.bind('<Configure>',lambda e:[label.configure(wraplength=max(300,e.width-24)) for label in (description,help_label)])
        self.search.trace_add('write',lambda *_:self.filter());self.refresh_catalog(quiet=True)

    def browse(self,var):
        path=Path(var.get());chosen=filedialog.askopenfilename(title='Select original exefs/main' if var is self.main_path else 'Select English Item message bank',initialdir=str(path.parent) if path.parent.is_dir() else None,parent=self)
        if chosen:
            var.set(chosen)
            if var is self.message_path:self.refresh_catalog()

    def refresh_catalog(self,quiet=False):
        try:
            from fw_editor import Legion,messages,DataError
            if not self.set_offer():return False
            _,legion,skills=source_tables(self.app.documents);names={};root=Path(self.message_path.get()).parent
            for name in ('Legion','Skill'):
                path=next((root/(name+s) for s in ('.msbt.zst','.msbt') if (root/(name+s)).is_file()),None)
                if path is None:raise DataError('Keep English Legion and Skill message banks beside Item.')
                names.update(messages(path.read_bytes()))
            offers=catalog(Legion(legion.build()),skills,names);self.offers={o.iid:o for o in offers};self.filter()
            self.notice.set(f'{len(offers)} combat battalions · prices, availability and chapter limits are editable.');return True
        except Exception as exc:
            self.notice.set(str(exc))
            if not quiet:messagebox.showerror('Buyable battalions',str(exc),parent=self)
            return False

    def filter(self):
        if not self.set_offer():return
        selected=self.current;q=self.search.get().casefold();self.tree.delete(*self.tree.get_children())
        for o in self.offers.values():
            if q not in (o.name+' '+o.gambit+' '+o.lid).casefold():continue
            self.tree.insert('','end',iid=o.iid,text=o.name,values=(o.gambit,o.troops,o.command,self.pending_prices.get(o.iid,o.default_price),'No' if o.iid in self.pending_disabled else 'Yes',self.pending_limits.get(o.iid,'Unlimited')))
        if selected in self.offers and self.tree.exists(selected):self.tree.selection_set(selected);self.tree.see(selected)

    def set_offer(self):
        if self.current not in self.offers:return True
        try:
            gold=int(self.gold.get());limit=int(self.limit.get())
            if not 1<=gold<=65535:raise ValueError('Price must be 1–65,535 gold.')
            if not 0<=limit<=127:raise ValueError('Per chapter must be 0–127; 0 means unlimited.')
            self.pending_prices[self.current]=gold
            if self.available.get():self.pending_disabled.discard(self.current)
            else:self.pending_disabled.add(self.current)
            if limit:self.pending_limits[self.current]=limit
            else:self.pending_limits.pop(self.current,None)
            if self.tree.exists(self.current):
                self.tree.set(self.current,'price',gold);self.tree.set(self.current,'available','Yes' if self.available.get() else 'No');self.tree.set(self.current,'limit',limit or 'Unlimited')
            return True
        except Exception as exc:messagebox.showerror('Buyable battalions',str(exc),parent=self);return False

    def select(self,event=None):
        selection=self.tree.selection()
        if not selection or selection[0]==self.current:return
        if not self.set_offer():
            if self.current and self.tree.exists(self.current):self.tree.selection_set(self.current)
            return
        self.current=selection[0];o=self.offers[self.current]
        self.selected_label.set(o.name+' · '+o.gambit);self.gold.set(str(self.pending_prices.get(o.iid,o.default_price)))
        self.available.set(o.iid not in self.pending_disabled);self.limit.set(str(self.pending_limits.get(o.iid,0)))

    def reset_prices(self):
        if not self.set_offer():return
        self.pending_prices={}
        if self.current in self.offers:self.gold.set(str(self.offers[self.current].default_price))
        self.filter();self.notice.set('Default prices restored; availability and limits retained. Apply to keep them.')

    def apply(self):
        if not self.set_offer():return False
        try:
            current=next((d for d in self.app.documents.values() if isinstance(d,BattalionPatch)),None)
            if not self.enabled.get():
                if current:current.configure_all(False,self.pending_prices,self.pending_disabled,self.pending_limits)
                text='Battalion sales disabled. Re-export and restart the game.'
            else:
                candidate=BattalionPatch(self.main_path.get(),self.message_path.get());candidate.configure_all(True,self.pending_prices,self.pending_disabled,self.pending_limits)
                build_outputs({**self.app.documents,MODULE:candidate})
                self.app.documents[MODULE]=candidate;self.app.sources[MODULE]=candidate.main_path
                text='Battalion sales enabled. Save your project and export the complete mod.'
            self.notice.set(text);self.app.status.set(text);return True
        except Exception as exc:messagebox.showerror('Buyable battalions',str(exc),parent=self);return False

    def action(self,callback):
        if self.apply():callback()
