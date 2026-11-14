"""Compact compiled-script editor, sharing suite projects and guarded mod export."""
from dataclasses import replace
from pathlib import Path
import math
import struct
import tkinter as tk
from tkinter import ttk, messagebox
from branding import APP_NAME
from script_bytecode import INVERSE, LITERALS, OPCODES, ScriptError, JUMPS
from script_data import ScriptDocument


def open_editor(app,selected=''):
    if not app.documents:
        app.error('Open the original GameData folder first. Script must be beside GameData.');return
    existing=getattr(app,'script_window',None)
    if existing and existing.winfo_exists():
        if selected and selected in existing.paths and selected!=existing.source.get():existing.select_source(selected)
        existing.lift();return existing
    root=Path(app.data_directory).parent/'Script'
    paths=sorted(set(root.rglob('*.bin.zst')) | set(root.rglob('*.bin'))) if root.is_dir() else []
    # A compressed source is preferred when both representations are present.
    paths=[p for p in paths if not (p.suffix=='.bin' and p.with_suffix('.bin.zst').is_file())]
    if not paths:
        app.error('No scripts found. Keep the original Script folder beside GameData.');return
    editor=ScriptEditor(app,root,paths);app.script_window=editor
    editor.select_source(selected if selected in editor.paths else next(iter(editor.paths)))
    return editor


class ScriptEditor(tk.Toplevel):
    def __init__(self,app,root,paths):
        super().__init__(app);self.app=app;self.root=root
        self.title(APP_NAME+' · Script editor');self.geometry('1140x760');self.minsize(970,650)
        self.transient(app);self.grab_set();self.protocol('WM_DELETE_WINDOW',self.close)
        self.paths={p.relative_to(root).as_posix():p for p in paths}
        self.doc=None;self.fi=None;self.ii=None;self.ci=None;self.pending=None
        self.source=tk.StringVar();self.function_search=tk.StringVar();self.constant_search=tk.StringVar()
        self.notice=tk.StringVar(value='Select a script. Original files stay unchanged.')
        self.value=tk.StringVar();self.mode=tk.StringVar(value='Unsigned bits');self.translation=tk.StringVar()
        bar=ttk.Frame(self,padding=6);bar.pack(fill='x')
        ttk.Label(bar,text='Source').pack(side='left',padx=(0,6))
        self.source_choice=ttk.Combobox(bar,textvariable=self.source,values=list(self.paths),state='readonly',width=50)
        self.source_choice.pack(side='left',fill='x',expand=True);self.source_choice.bind('<<ComboboxSelected>>',lambda _:self.select_source(self.source.get()))
        ttk.Button(bar,text='Save project…',command=lambda:self.action(self.app.save_project)).pack(side='left',padx=4)
        ttk.Button(bar,text='Export mod…',command=lambda:self.action(self.app.export)).pack(side='left')
        ttk.Label(self,text='Edit constants, invert conditions, or replace calls with an existing identical signature. Instruction count, stack slots and branch targets stay fixed.',style='Hint.TLabel',wraplength=1050,padding=(8,3)).pack(anchor='w')
        self.tabs=ttk.Notebook(self);self.tabs.pack(fill='both',expand=True,padx=6,pady=3)
        code=ttk.Frame(self.tabs);constants=ttk.Frame(self.tabs);metadata=ttk.Frame(self.tabs)
        self.tabs.add(code,text='Functions / instructions');self.tabs.add(constants,text='String constants');self.tabs.add(metadata,text='Imports / limits')
        panes=ttk.Panedwindow(code,orient='horizontal');panes.pack(fill='both',expand=True)
        left=ttk.Frame(panes,width=270);right=ttk.Frame(panes);panes.add(left,weight=1);panes.add(right,weight=3)
        ttk.Label(left,text='Find function',style='Hint.TLabel').pack(anchor='w')
        ttk.Entry(left,textvariable=self.function_search).pack(fill='x',pady=3)
        self.function_tree=self.tree(left,[('name','Function / initializer',260)],height=12)
        self.function_tree.bind('<<TreeviewSelect>>',self.select_function)
        self.code_tree=self.tree(right,[('index','#',48),('opcode','Instruction',95),('args','Raw operands',150),('detail','Resolved call / constant',420)],height=12)
        self.code_tree.bind('<<TreeviewSelect>>',self.select_instruction)
        self.code_tree.bind('<Double-1>',self.open_constant_use)
        ttk.Label(constants,text='A constant can be shared by multiple instructions. Editing it changes every use shown below; unrelated metadata strings are preserved.',style='Hint.TLabel',wraplength=1030).pack(anchor='w',pady=4)
        ttk.Label(constants,text='Find string or translation',style='Hint.TLabel').pack(anchor='w')
        ttk.Entry(constants,textvariable=self.constant_search).pack(fill='x',pady=3)
        self.constant_tree=self.tree(constants,[('index','#',45),('raw','Stored value',480),('english','English / glossary',400)],height=10)
        self.constant_tree.bind('<<TreeviewSelect>>',self.select_constant)
        self.uses_tree=self.tree(constants,[('function','Used by function',300),('instruction','Instruction #',100),('opcode','Instruction',100)],height=4)
        self.uses_tree.bind('<Double-1>',self.open_use)
        self.metadata=tk.Text(metadata,wrap='word',font=('DejaVu Sans',10));self.metadata.pack(fill='both',expand=True)
        self.edit=ttk.LabelFrame(self,text='Selected value',padding=6);self.edit.pack(fill='x',padx=6,pady=3)
        self.edit_title=tk.StringVar();ttk.Label(self.edit,textvariable=self.edit_title).grid(row=0,column=0,columnspan=4,sticky='w')
        self.mode_choice=ttk.Combobox(self.edit,textvariable=self.mode,values=('Unsigned bits','Signed integer','Floating point'),state='readonly',width=16)
        self.mode_choice.grid(row=1,column=0,sticky='w',padx=(0,5));self.mode_choice.bind('<<ComboboxSelected>>',self.change_mode)
        self.input=ttk.Entry(self.edit,textvariable=self.value);self.input.grid(row=1,column=1,sticky='ew')
        self.options=ttk.Combobox(self.edit,textvariable=self.value,state='readonly');self.options.grid(row=1,column=1,sticky='ew');self.options.grid_remove()
        self.apply_button=ttk.Button(self.edit,text='Apply value',command=self.commit);self.apply_button.grid(row=1,column=2,padx=5)
        ttk.Button(self.edit,text='Restore source value',command=self.restore).grid(row=1,column=3)
        ttk.Label(self.edit,textvariable=self.translation,style='English.TLabel',wraplength=950).grid(row=2,column=0,columnspan=4,sticky='ew',pady=(4,0))
        self.edit.columnconfigure(1,weight=1)
        ttk.Label(self,textvariable=self.notice,relief='sunken',padding=6).pack(fill='x')
        self.value.trace_add('write',self.preview)
        self.function_search.trace_add('write',lambda *_:self.filter_functions())
        self.constant_search.trace_add('write',lambda *_:self.filter_constants())

    @staticmethod
    def tree(parent,columns,height):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
        tree=ttk.Treeview(frame,columns=[x[0] for x in columns],show='headings',height=height)
        for key,label,width in columns:tree.heading(key,text=label);tree.column(key,width=width,minwidth=35,stretch=True)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y');return tree

    def error(self,exc):
        messagebox.showerror('Script editor',str(exc),parent=self)

    def action(self,callback):
        if self.commit():callback()
        if self.winfo_exists():self.grab_set()

    def select_source(self,name):
        previous=self.doc.filename.removeprefix('Script/') if self.doc else ''
        if not self.commit():self.source.set(previous);return
        try:
            path=self.paths[name];filename='Script/'+name
            doc=next((d for d in self.app.documents.values() if d.filename==filename),None)
            if doc is None:
                clean=self.app.session_state()==self.app.saved_state
                doc=ScriptDocument(path.read_bytes(),filename)
                key='Scripts · '+filename;self.app.documents[key]=doc;self.app.sources[key]=path.resolve()
                if clean:self.app.saved_state=self.app.session_state()
            if doc.tutorial_programs:raise ScriptError('This source contains active reviewed tutorial programs. Turn scene bypasses off in Tools → Forced tutorials before editing. Persistent unlock guards stay installed for existing saves; edit their original source only in a separate clean project.')
            self.doc=doc;self.source.set(name);self.fi=self.ii=self.ci=None;self.pending=None
            self.function_search.set('');self.constant_search.set('');self.filter_functions();self.filter_constants();self.show_form(None)
            self.code_tree.delete(*self.code_tree.get_children());self.uses_tree.delete(*self.uses_tree.get_children())
            self.metadata.configure(state='normal');self.metadata.delete('1.0','end')
            self.metadata.insert('1.0','Imports:\n'+'\n'.join(doc.module.info.imports)+'\n\nThis is an instruction-level editor, not recovered AngelScript source.\n\nSupported: arbitrary-length UTF-8 string constants; 32/64-bit numeric literals; paired conditional-branch inversion; calls to existing references with identical types, argument directions, receiver and traits.\n\nNot supported here: inserting/removing instructions or functions, arbitrary jump destinations, changing signatures/stack slots, adding engine APIs/imports. The separate Forced tutorials tool uses a small set of source-guarded completion recipes, not arbitrary instruction editing.\n\nString caches and ASF payload size are rebuilt; every export is parsed and checked again. Structural validation does not simulate game events. Test a separate mod with a save backup.\n\nScripts join the normal suite project (v2). Save and export from this window or the main toolbar. Exports keep original compression and relative Script paths. Never overwrite your extracted game data.')
            self.metadata.configure(state='disabled');self.update_notice()
        except Exception as exc:self.source.set(previous);self.error(exc)

    def update_notice(self):
        if self.doc:self.notice.set(f'{self.doc.filename} · {len(self.doc.module.functions)} functions · {len(self.doc.module.constants)} string constants · {len(self.doc.changes)} edits · save a project to keep edits')

    def filter_functions(self):
        if not self.doc:return
        text=self.function_search.get().casefold();self.function_tree.delete(*self.function_tree.get_children())
        for i,function in sorted(enumerate(self.doc.module.functions),key=lambda pair:(not bool(pair[1].signature.name),pair[1].label.casefold())):
            if text in function.label.casefold():self.function_tree.insert('','end',iid=str(i),values=(function.label,))

    def filter_constants(self):
        if not self.doc:return
        text=self.constant_search.get().casefold();self.constant_tree.delete(*self.constant_tree.get_children())
        for i,token in enumerate(self.doc.module.constants):
            value=self.doc.strings.get(i,token.text);english=self.app.translator.resolve(value).text
            if text in (value+' '+english).casefold():self.constant_tree.insert('','end',iid=str(i),values=(str(i)+(' *' if i in self.doc.strings else ''),value,english))

    def select_function(self,event=None):
        values=self.function_tree.selection()
        if not values:return
        index=int(values[0])
        if index==self.fi:return
        if not self.commit():
            if self.fi is not None and self.function_tree.exists(str(self.fi)):self.function_tree.selection_set(str(self.fi))
            return
        self.fi=index;self.ii=self.ci=None;self.show_form(None);self.show_instructions()

    def show_instructions(self):
        self.code_tree.delete(*self.code_tree.get_children())
        if self.fi is None:return
        for i,old in enumerate(self.doc.module.functions[self.fi].instructions):
            opcode,args=self.doc.instruction(self.fi,i);ins=replace(old,opcode=opcode,arguments=args);detail=self.doc.module.describe(ins)
            if ins.name in ('PGA','PshGPtr') and not args[0]&1:
                ci=args[0]>>1;detail=f'string[{ci}]: '+self.doc.strings.get(ci,self.doc.module.constants[ci].text)
            if ins.name in JUMPS:
                delta=args[0]&0xffffffff;delta=delta-(1<<32) if delta&(1<<31) else delta
                detail=f'branch → #{i+delta+(1 if delta>=0 else 0)} (target fixed)'
            self.code_tree.insert('','end',iid=str(i),values=(str(i)+(' *' if (self.fi,i) in self.doc.instructions else ''),ins.name,', '.join(str(x) for x in args),detail))

    def select_instruction(self,event=None):
        selected=self.code_tree.selection()
        if not selected:return
        ii=int(selected[0])
        if self.pending==('instruction',self.fi,ii):return
        if not self.commit():return
        self.ii=ii;self.ci=None;self.show_form(('instruction',self.fi,ii))

    def select_constant(self,event=None):
        selected=self.constant_tree.selection()
        if not selected:return
        ci=int(selected[0])
        if self.pending==('string',ci):return
        if not self.commit():return
        self.ci=ci;self.ii=None;self.show_form(('string',ci));self.uses_tree.delete(*self.uses_tree.get_children());self.uses=[]
        for fi,function in enumerate(self.doc.module.functions):
            for ii,ins in enumerate(function.instructions):
                if ins.name in ('PGA','PshGPtr') and ins.arguments[0]==ci*2:
                    index=len(self.uses);self.uses.append((fi,ii));self.uses_tree.insert('','end',iid=str(index),values=(function.label,ii,ins.name))

    def open_use(self,event=None):
        if not self.uses_tree.selection() or not self.commit():return
        fi,ii=self.uses[int(self.uses_tree.selection()[0])];self.function_search.set('');self.function_tree.selection_set(str(fi));self.function_tree.see(str(fi));self.select_function()
        self.tabs.select(0);self.code_tree.selection_set(str(ii));self.code_tree.see(str(ii));self.select_instruction()

    def open_constant_use(self,event=None):
        selected=self.code_tree.selection()
        if not selected or self.fi is None or not self.commit():return
        ins=self.doc.module.functions[self.fi].instructions[int(selected[0])]
        if ins.name not in ('PGA','PshGPtr') or ins.arguments[0]&1:return
        ci=ins.arguments[0]>>1;self.constant_search.set('');self.tabs.select(1)
        self.constant_tree.selection_set(str(ci));self.constant_tree.see(str(ci));self.select_constant()

    def show_form(self,pending):
        self.pending=None;self.input.grid();self.options.grid_remove();self.mode_choice.grid_remove();self.apply_button.configure(state='normal');self.translation.set('');self.call_values={}
        if not pending:
            self.edit_title.set('Select an instruction or string constant.');self.value.set('');self.input.configure(state='disabled');self.apply_button.configure(state='disabled');self.baseline='';return
        self.input.configure(state='normal')
        if pending[0]=='string':
            ci=pending[1];self.edit_title.set(f'String constant #{ci} · all uses in this script');self.value.set(self.doc.strings.get(ci,self.doc.module.constants[ci].text))
        else:
            _,fi,ii=pending;old=self.doc.module.functions[fi].instructions[ii];opcode,args=self.doc.instruction(fi,ii);kind=self.doc.module.editable(old)
            self.edit_title.set(f'{self.doc.module.functions[fi].label} · instruction #{ii} · {old.name}')
            if kind=='literal':
                self.mode.set('Unsigned bits');self.previous_mode='Unsigned bits';self.mode_choice.grid();self.value.set(str(args[-1]&((1<<LITERALS[old.name])-1)))
            elif kind=='condition':
                self.input.grid_remove();self.options.grid();self.options.configure(values=(old.name,INVERSE[old.name]));self.value.set(OPCODES[opcode][0])
            elif kind=='call':
                self.call_values={f'{i}: {label}':i for i,label in self.doc.module.call_options(old)}
                self.input.grid_remove();self.options.grid();self.options.configure(values=list(self.call_values));self.value.set(next(k for k,v in self.call_values.items() if v==args[0]))
            else:
                self.value.set(', '.join(str(x) for x in args));self.input.configure(state='readonly');self.apply_button.configure(state='disabled')
        self.pending=pending;self.baseline=self.value.get();self.preview()

    def preview(self,*_):
        if self.pending and self.pending[0]=='string':self.translation.set(self.app.translator.resolve(self.value.get()).text)
        elif self.pending and self.pending[0]=='instruction':
            old=self.doc.module.functions[self.pending[1]].instructions[self.pending[2]]
            self.translation.set('Literal type is not recoverable here: choose the intended integer/float interpretation.' if old.name in LITERALS else 'Changing an event command or condition can alter game behavior. Test in a separate mod.')

    def literal_bits(self,text=None,mode=None):
        _,fi,ii=self.pending;old=self.doc.module.functions[fi].instructions[ii];bits=LITERALS[old.name]
        value=self.value.get() if text is None else text;mode=self.mode.get() if mode is None else mode
        if mode=='Floating point':
            number=float(value)
            if not math.isfinite(number):raise ScriptError('Enter a finite floating-point number.')
            return int.from_bytes(struct.pack('<f' if bits==32 else '<d',number),'little')
        number=int(value,0) if value.strip().lower().startswith(('0x','-0x','+0x')) else int(value)
        lower=0 if mode=='Unsigned bits' else -(1<<(bits-1));upper=(1<<bits)-1 if mode=='Unsigned bits' else (1<<(bits-1))-1
        if not lower<=number<=upper:raise ScriptError(f'Value is outside the {bits}-bit {mode.lower()} range.')
        return number&((1<<bits)-1)

    def change_mode(self,event=None):
        if not self.pending:return
        try:
            # Changing interpretation uses the applied value, rather than silently parsing text as a new type.
            if self.value.get()!=self.baseline:raise ScriptError('Apply the current value before changing its interpretation.')
            _,fi,ii=self.pending;old=self.doc.module.functions[fi].instructions[ii];bits=LITERALS[old.name];value=self.doc.instruction(fi,ii)[1][-1]&((1<<bits)-1)
            if self.mode.get()=='Floating point':text=repr(struct.unpack('<f' if bits==32 else '<d',value.to_bytes(bits//8,'little'))[0])
            elif self.mode.get()=='Signed integer':text=str(value-(1<<bits) if value&(1<<(bits-1)) else value)
            else:text=str(value)
            self.value.set(text);self.baseline=text;self.previous_mode=self.mode.get()
        except Exception as exc:
            self.mode.set(getattr(self,'previous_mode','Unsigned bits'));self.error(exc)

    def commit(self):
        if not self.pending or self.value.get()==self.baseline:return True
        try:
            if self.pending[0]=='string':self.doc.set_string(self.pending[1],self.value.get())
            else:
                _,fi,ii=self.pending;old=self.doc.module.functions[fi].instructions[ii];opcode,args=self.doc.instruction(fi,ii);args=list(args)
                if old.name in LITERALS:
                    value=self.literal_bits();bits=LITERALS[old.name]
                    args[-1]=value-(1<<bits) if value&(1<<(bits-1)) else value
                elif old.name in INVERSE:opcode=next(i for i,(name,layout) in enumerate(OPCODES) if name==self.value.get())
                else:args[0]=self.call_values[self.value.get()]
                self.doc.set_instruction(fi,ii,opcode,args)
            self.baseline=self.value.get();self.update_notice()
            # Tree rows update without clearing selection or losing the active editor.
            if self.pending[0]=='string':
                ci=self.pending[1]
                if self.constant_tree.exists(str(ci)):self.constant_tree.item(str(ci),values=(str(ci)+(' *' if ci in self.doc.strings else ''),self.value.get(),self.translation.get()))
            elif self.code_tree.exists(str(self.pending[2])):
                fi,ii=self.pending[1:];old=self.doc.module.functions[fi].instructions[ii];opcode,args=self.doc.instruction(fi,ii);ins=replace(old,opcode=opcode,arguments=args)
                self.code_tree.item(str(ii),values=(str(ii)+(' *' if (fi,ii) in self.doc.instructions else ''),ins.name,', '.join(str(x) for x in args),self.doc.module.describe(ins)))
            return True
        except Exception as exc:self.error(exc);return False

    def restore(self):
        if not self.pending:return
        pending=self.pending
        if pending[0]=='string':self.doc.set_string(pending[1],self.doc.module.constants[pending[1]].text);self.filter_constants()
        else:
            _,fi,ii=pending;old=self.doc.module.functions[fi].instructions[ii];self.doc.set_instruction(fi,ii,old.opcode,old.arguments);self.show_instructions()
        self.show_form(pending);self.update_notice()

    def close(self):
        if not self.commit():return
        self.grab_release();self.destroy()
