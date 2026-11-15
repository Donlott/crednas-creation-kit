"""Searchable mount/skill catalog with per-offer prices."""
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from branding import APP_NAME
from mount_data import MountPatch,MODULE,source_tables,load_sources,build_outputs
from mount_catalog import catalog


def open_editor(app):
    if not app.documents and not getattr(app,'data_directory',None):app.error('Use Open data… to choose your extracted game folder first.');return
    if not app.apply(True):return
    existing=getattr(app,'mount_window',None)
    if existing and existing.winfo_exists():existing.lift();return existing
    try:
        clean=app.session_state()==app.saved_state
        loaded=load_sources(app.documents,app.sources,app.data_directory)
        if loaded:
            app.suggestion_cache.clear();app.rebuild_translator()
        if clean:app.saved_state=app.session_state()
        window=MountEditor(app);app.mount_window=window;return window
    except Exception as exc:app.error(str(exc))


class MountEditor(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.offers={};self.current=None
        self.title(APP_NAME+' · Buyable mounts');self.geometry('1040x740');self.minsize(850,650)
        self.transient(app);self.grab_set()
        patch=next((d for d in app.documents.values() if isinstance(d,MountPatch)),None)
        base=Path(app.data_directory);names=getattr(app,'names_directory',None)
        main=patch.main_path if patch else base.parent.parent/'exefs/main'
        bank=patch.message_path if patch else (Path(names) if names else base.parent/'Msg/USen')/'Item.msbt.zst'
        self.pending_prices=deepcopy(patch.prices) if patch else {}
        self.pending_disabled=set(patch.disabled) if patch else set();self.pending_limits=deepcopy(patch.limits) if patch else {}
        self.enabled=tk.BooleanVar(value=bool(patch and patch.enabled));self.search=tk.StringVar();self.gold=tk.StringVar()
        self.available=tk.BooleanVar(value=True);self.limit=tk.StringVar(value='0')
        self.main_path=tk.StringVar(value=str(main));self.message_path=tk.StringVar(value=str(bank));self.notice=tk.StringVar(value='Select a variant to change its price.')
        self.selected_label=tk.StringVar(value='Select a mount / skill variant')
        body=ttk.Frame(self,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Buyable mounts · experimental',style='Title.TLabel').pack(anchor='w')
        self.description=ttk.Label(body,text='All supported mount/skill variants are sold directly at Dagsion’s item shop for Cai, from chapter 5 after the stable unlock. Skills use their normal bond levels. Named unique mounts can only be owned once at a time.',wraplength=1000)
        self.description.pack(fill='x',pady=(6,8))
        ttk.Checkbutton(body,text='Enable direct mount sales',variable=self.enabled).pack(anchor='w')
        for label,var in [('Original exefs/main',self.main_path),('English Item message bank',self.message_path)]:
            frame=ttk.Frame(body);frame.pack(fill='x',pady=3)
            ttk.Label(frame,text=label,width=25).pack(side='left')
            ttk.Entry(frame,textvariable=var).pack(side='left',fill='x',expand=True,padx=(0,5))
            ttk.Button(frame,text='Browse…',command=lambda v=var:self.browse(v)).pack(side='right')
        bar=ttk.Frame(body);bar.pack(fill='x',pady=(8,5))
        ttk.Label(bar,text='Search').pack(side='left',padx=(0,6));ttk.Entry(bar,textvariable=self.search).pack(side='left',fill='x',expand=True)
        ttk.Button(bar,text='Refresh catalog',command=self.refresh_catalog).pack(side='left',padx=5)
        ttk.Button(bar,text='Reset prices',command=self.reset_prices).pack(side='right')
        area=ttk.Frame(body);area.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(area,columns=('skill','upgrade','price','available','limit','unique'),selectmode='browse',height=12)
        self.tree.heading('#0',text='Mount');self.tree.column('#0',width=195,minwidth=150)
        for key,label,width in [('skill','Skill',165),('upgrade','Upgraded skill',165),('price','Gold',65),('available','Sell',55),('limit','Per chapter',85),('unique','Unique',55)]:
            self.tree.heading(key,text=label);self.tree.column(key,width=width,minwidth=width,stretch=key in ('skill','upgrade'))
        scroll=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');self.tree.bind('<<TreeviewSelect>>',self.select)
        edit=ttk.Frame(body);edit.pack(fill='x',pady=7)
        ttk.Label(edit,textvariable=self.selected_label).pack(fill='x',pady=(0,4))
        edit=ttk.Frame(edit);edit.pack(fill='x')
        ttk.Checkbutton(edit,text='Sell this variant',variable=self.available).pack(side='left')
        ttk.Label(edit,text='Gold').pack(side='left',padx=(12,0))
        ttk.Spinbox(edit,textvariable=self.gold,from_=1,to=65535,width=9).pack(side='left',padx=6)
        ttk.Label(edit,text='Per chapter').pack(side='left',padx=(12,5))
        ttk.Spinbox(edit,textvariable=self.limit,from_=0,to=127,width=5).pack(side='left')
        ttk.Label(edit,text='0 = unlimited').pack(side='left',padx=6)
        ttk.Button(edit,text='Set offer',command=self.set_price).pack(side='right')
        self.help=ttk.Label(body,text='Keep the English Ride and Skill message banks beside Item. Requires the verified executable. Full storage or an already-owned unique mount means no delivery and no charge. Stock limits apply separately to each variant and refill to the cap each chapter. Owned mounts stay unchanged. Export all generated files together and restart the game. In-game testing is still required.',wraplength=1000,style='Hint.TLabel')
        self.help.pack(fill='x',pady=5)
        ttk.Label(body,textvariable=self.notice,wraplength=1000).pack(fill='x',pady=4)
        actions=ttk.Frame(body);actions.pack(side='bottom',fill='x')
        ttk.Button(actions,text='Close',command=self.destroy).pack(side='right');ttk.Button(actions,text='Apply',command=self.apply).pack(side='right',padx=6)
        ttk.Button(actions,text='Save project…',command=lambda:self.action(app.save_project)).pack(side='left')
        ttk.Button(actions,text='Export mod…',command=lambda:self.action(app.export)).pack(side='left',padx=6)
        body.bind('<Configure>',lambda e:[label.configure(wraplength=max(300,e.width-24)) for label in (self.description,self.help)])
        self.search.trace_add('write',lambda *_:self.filter());self.refresh_catalog(quiet=True)

    def browse(self,var):
        path=Path(var.get());chosen=filedialog.askopenfilename(title='Select '+('original exefs/main' if var is self.main_path else 'English Item message bank'),initialdir=str(path.parent) if path.parent.is_dir() else None,parent=self)
        if chosen:
            var.set(chosen)
            if var is self.message_path:self.refresh_catalog()

    def refresh_catalog(self,quiet=False):
        try:
            from fw_editor import Binary,messages,DataError
            _,job,skills=source_tables(self.app.documents);names={};root=Path(self.message_path.get()).parent
            for name in ('Ride','Skill'):
                path=next((root/(name+suffix) for suffix in ('.msbt.zst','.msbt') if (root/(name+suffix)).is_file()),None)
                if path is None:raise DataError('Keep English Ride and Skill message banks beside Item, then refresh the catalog.')
                names.update(messages(path.read_bytes()))
            offers=catalog(Binary(job.build()),skills,names);self.offers={o.iid:o for o in offers};self.filter()
            self.notice.set(f'{len({o.rid for o in offers})} mount types · {len(offers)} skill variants · availability, prices and chapter limits are editable per row.')
            return True
        except Exception as exc:
            self.notice.set(str(exc))
            if not quiet:messagebox.showerror('Buyable mounts',str(exc),parent=self)
            return False

    def filter(self):
        selected=self.current;q=self.search.get().casefold();self.tree.delete(*self.tree.get_children())
        for o in self.offers.values():
            if q not in (o.mount_name+' '+o.skill_name+' '+o.upgrade_name+' '+o.rid).casefold():continue
            self.tree.insert('','end',iid=o.iid,text=o.mount_name,values=(o.skill_name,o.upgrade_name,self.pending_prices.get(o.iid,o.default_price),'No' if o.iid in self.pending_disabled else 'Yes',self.pending_limits.get(o.iid,'Unlimited'),'Yes' if o.unique else ''))
        if selected and self.tree.exists(selected):self.tree.selection_set(selected);self.tree.see(selected)

    def set_price(self):
        if self.current not in self.offers:return True
        try:
            value=int(self.gold.get());limit=int(self.limit.get())
            if not 1<=value<=65535:raise ValueError('Price must be from 1 to 65,535 gold.')
            if not 0<=limit<=127:raise ValueError('Per-chapter limit must be from 0 to 127; 0 means unlimited.')
            self.pending_prices[self.current]=value
            if self.available.get():self.pending_disabled.discard(self.current)
            else:self.pending_disabled.add(self.current)
            if limit:self.pending_limits[self.current]=limit
            else:self.pending_limits.pop(self.current,None)
            if self.tree.exists(self.current):
                self.tree.set(self.current,'price',value);self.tree.set(self.current,'available','Yes' if self.available.get() else 'No');self.tree.set(self.current,'limit',limit or 'Unlimited')
            return True
        except Exception as exc:messagebox.showerror('Buyable mounts',str(exc),parent=self);return False

    def select(self,event=None):
        selection=self.tree.selection()
        if not selection:return
        chosen=selection[0]
        if chosen==self.current:return
        if not self.set_price():
            if self.current and self.tree.exists(self.current):self.tree.selection_set(self.current)
            return
        self.current=chosen;o=self.offers[chosen];self.selected_label.set(o.mount_name+' · '+o.skill_name)
        self.gold.set(str(self.pending_prices.get(chosen,o.default_price)));self.available.set(chosen not in self.pending_disabled);self.limit.set(str(self.pending_limits.get(chosen,0)))

    def reset_prices(self):
        self.pending_prices={}
        if self.current in self.offers:self.gold.set(str(self.offers[self.current].default_price))
        self.filter();self.notice.set('Default catalog prices restored. Apply to keep them.')

    def apply(self):
        if not self.set_price():return False
        try:
            current=next((d for d in self.app.documents.values() if isinstance(d,MountPatch)),None)
            if not self.enabled.get():
                if current:current.configure_all(False,self.pending_prices,self.pending_disabled,self.pending_limits)
                text='Direct mount sales disabled. Re-export and restart the game.'
            else:
                candidate=MountPatch(self.main_path.get(),self.message_path.get());candidate.configure_all(True,self.pending_prices,self.pending_disabled,self.pending_limits)
                trial={**self.app.documents,MODULE:candidate};build_outputs(trial)
                self.app.documents[MODULE]=candidate;self.app.sources[MODULE]=candidate.main_path
                text='Mount catalog enabled. Save the project or export a test mod, then restart the game.'
            self.notice.set(text);self.app.status.set(text);return True
        except Exception as exc:messagebox.showerror('Buyable mounts',str(exc),parent=self);return False

    def action(self,callback):
        if self.apply():callback()
