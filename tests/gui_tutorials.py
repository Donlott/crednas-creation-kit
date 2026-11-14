"""Route catalog, blocked native effects, native scheduling and legacy migration UI."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
import tkinter as tk
from tkinter import filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
import tutorial_data as td
from tutorial_ui import open_editor

base=Path(os.environ['FW_GAME_DATA']);failures=[];errors=[];callbacks=[]
hashes={ref[0]:hashlib.sha256((base/ref[0]).read_bytes()).digest() for p in td.PRESETS for ref in p.rows}
for p in td.PRESETS:
    if p.script:hashes[p.script]=hashlib.sha256((base.parent/p.script).read_bytes()).digest()
hashes[td.BRIDGE_SOURCE]=hashlib.sha256((base.parent/td.BRIDGE_SOURCE).read_bytes()).digest()
original_loop=tk.Tk.mainloop
with tempfile.TemporaryDirectory() as temporary:
    temp=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temp/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                assert app.switch_module('Events','timeline:0:94',source_file='Timeline_Part1_Kai.bin')
                row=app.learning_row;owner=app.doc.owner
                widget=app.widgets[0x5e][1];widget.delete(0,'end');widget.insert(0,'1830')
                main_menu=app.nametowidget(app.cget('menu'));tools=app.nametowidget(main_menu.entrycget(2,'menu'))
                index=next(i for i in range(tools.index('end')+1) if tools.entrycget(i,'label')=='Forced tutorials…')
                tools.invoke(index);window=app.tutorial_window;app.update()
                assert open_editor(app) is window and len(window.variables)==39
                assert len(app.documents)==209 and app.doc.value(row,app.doc.by_offset[0x5e])==1830
                def select(key):
                    window.tree.selection_set(key);window.tree.see(key);window.select();app.update()
                select('cai-exam');assert str(window.check.cget('state'))=='disabled' and 'permit' in window.reason.get()
                window.toggle();assert not window.variables['cai-exam'].get()
                select('cai-arena');assert str(window.check.cget('state'))=='normal'
                window.check.invoke();assert window.variables['cai-arena'].get()
                select('cai-recruitment');window.check.invoke();assert window.variables['cai-recruitment'].get()
                assert window.apply() and td.inspect_state(app.documents,td.BY_KEY['cai-recruitment'])[0]=='disabled'
                assert app.widgets[0x21][1].get()=='13' and app.widgets[0x5e][1].get()=='1830'
                ready=[p for p in td.PRESETS if not p.blocked]
                for p in ready:window.variables[p.key].set(True)
                assert window.apply();window.action(app.save_project);window.action(app.export)
                project=json.loads((temp/'project.json').read_text())
                assert project['documents']['Script/hub/Hub_000_KAI.bin.zst']['format']=='fw-script-edits-v2'
                for p in ready:
                    assert td.inspect_state(app.documents,p)[0]=='disabled'
                    for _,v,r in td.targets(app.documents,p):
                        for off in td.CONTROLLED:assert v.value(r,v.by_offset[off])==v.original(r,v.by_offset[off])
                assert not list((temp/'mod').rglob('*.backup-*'))
                select('cai-recruitment');window.check.invoke();assert window.apply()
                assert td.inspect_state(app.documents,td.BY_KEY['cai-recruitment'])[0]=='normal'
                assert td.inspect_state(app.documents,td.BY_KEY['cai-trading'])[0]=='disabled'
                window.destroy();app.load_project();window=open_editor(app)
                assert all(window.variables[p.key].get() for p in ready)
                window.search.set('trading');app.update()
                visible=[k for route in window.tree.get_children() for k in window.tree.get_children(route)]
                assert len(visible)==4
                window.search.set('');window.route.set('Theodora');app.update()
                assert all(k=='route:Theodora' for k in window.tree.get_children())
                window.route.set('All routes');app.update()
                select('leda-drinks');assert str(window.check.cget('state'))=='normal'
                assert 'normal vendor' in window.detail.get()
                for p in ready:window.variables[p.key].set(False)
                assert window.apply()
                assert td.document(app.documents,td.BRIDGE_SOURCE).tutorial_programs
                assert all(td.inspect_state(app.documents,p)[0]=='normal' for p in ready)
                window.destroy();app.switch_module('Characters')
                # A saved old shortcut is visible and migrated, retaining a custom clock field.
                p=td.BY_KEY['cai-recruitment'];o,v,r=td.targets(app.documents,p)[0]
                for off,value in td.legacy_values(p).items():v.set(r,v.by_offset[off],value)
                window=open_editor(app);select('cai-recruitment')
                assert window.states[p.key][0]=='legacy' and window.variables[p.key].get()
                assert window.apply() and v.value(r,v.by_offset[0x21])==13 and v.value(r,v.by_offset[0x5e])==1830
                # Custom table conflicts are never silently overwritten.
                p=td.BY_KEY['cai-trading'];o,v,r=td.targets(app.documents,p)[0];v.set(r,v.by_offset[0x28],['CUSTOM'])
                window.refresh();select(p.key)
                assert str(window.check.cget('state'))=='disabled' and 'custom' in window.reason.get()
                assert window.apply() and v.value(r,v.by_offset[0x28])==['CUSTOM']
                # Capture the focused dependency explanation and compact catalog.
                select('cai-arena');window.geometry('800x620');app.update()
                assert window.detail_label.winfo_width()>=700
                window.geometry('980x690');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temp));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(window.winfo_id()),str(previews/'forced-tutorials-reworked.png')],check=True)
                window.destroy()
                # Ordinary script editing cannot display a stale original body as the active program.
                from script_ui import open_editor as script_editor
                editor=script_editor(app,'hub/Hub_000_KAI.bin.zst');app.update()
                assert len(errors)==1 and 'active reviewed tutorial' in errors[0];editor.destroy()
                isolated=temp/'isolated';isolated.mkdir();(isolated/'Variable.bin').write_bytes((base/'Variable.bin').read_bytes())
                assert app.open_data(isolated);window=open_editor(app)
                assert all(state[0] in ('blocked','unavailable') for state in window.states.values());window.destroy()
                assert not callbacks,callbacks
                for fn,digest in hashes.items():
                    source=base.parent/fn if fn.startswith('Script/') else base/fn
                    assert hashlib.sha256(source.read_bytes()).digest()==digest
                print('PASS: 28 groups / 39 route entries; route/search filtering; blocked dependencies; native type/date intact; 20 independent recipes; persistent unlock checks; source guards; save/reload/export; isolated reversal; legacy migration; custom edit protection; script UI guard; no backups; originals unchanged.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(250,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')), \
         patch.object(messagebox,'showinfo'),patch.object(messagebox,'askyesno',return_value=True), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
