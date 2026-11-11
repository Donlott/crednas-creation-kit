"""Actual deployment Tk forms, fixed slots, current links and nested exports."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
hashes={p.name:hashlib.sha256(p.read_bytes()).digest() for p in (base/'Dispos').glob('*.bin')}
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                assert app.switch_module('Battle deployment',source_file='Dispos/DB_01.bin')
                assert len(app.deployment_source_choice.cget('values'))==171
                assert len(app.widgets)==42 and len(app.deployment_form.tabs())==3
                assert app.deployment_form.tab(1,'text')=='Inventory'
                owner=app.doc.owner;group=app.current;row=app.learning_row;names=dict(app.doc.names)
                def write(offset,value):
                    widget=app.widgets[offset][1];widget.delete(0,'end');widget.insert(0,value)
                def action(text):next(w for w in app.deployment_tools.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==text).invoke()
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                choose(0x20,'Majide','PID_マジーデ');write(0x34,'-128');write(0x37,'127');write(0x3b,'77')
                pipe='IID_試作品１号|||';choose(0x68,pipe,pipe);write(0x78,'4294967295');write(0xf8,'synthetic argument')
                assert app.apply();assert owner.views['units'].value(row,app.doc.by_offset[0x20])=='PID_マジーデ'
                write(0x34,'-129');assert not app.switch_module('Items');assert app.active_module=='Battle deployment'
                write(0x34,'-128');assert app.apply()
                action('Copy unit');app.switch_module('Battle deployment',source_file='Dispos/DB_02.bin')
                target=app.learning_row;target_owner=app.doc.owner;action('Paste values')
                assert app.doc.value(target,app.doc.by_offset[0x20])=='PID_マジーデ'
                action('Reset unit');assert not target_owner.changes
                assert owner.changes and owner.views['units'].names==names
                app.switch_module('Battle deployment',row.pid,source_file=owner.filename);action('Open character')
                assert app.active_module=='Characters' and app.current.pid=='PID_マジーデ'
                app.switch_module('Items',pipe,source_file='Item_P1.bin');app.item_usage_refresh()
                index=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Battle deployment' and u.source==owner.filename and u.record==row.pid)
                app.item_usage_tree.selection_set(str(index));app.item_usage_open()
                assert app.doc.filename==owner.filename and app.learning_row.pid==row.pid and app.notebook.index('current')==0
                app.deployment_links_refresh();index=next(i for i,t in enumerate(app.deployment_links) if t[2]=='PID_マジーデ')
                app.deployment_links_tree.selection_set(str(index));app.deployment_links_open();assert app.current.pid=='PID_マジーデ'
                app.switch_module('Battle deployment',row.pid,source_file=owner.filename)
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert len(project['documents'])==204 and project['documents'][owner.filename]['format']=='fw-deployment-edits-v1'
                files=list((temporary/'mod/romfs/GameData').rglob('*.bin'));assert len(files)==204
                assert not (temporary/'mod/romfs/GameData/BattleField.bin').exists()
                result=fw.Deployment((temporary/'mod/romfs/GameData'/owner.filename).read_bytes(),owner.filename)
                for key,value in owner.changes.items():assert result.original(*result.edit_target(*key))==value
                app.reset();assert not owner.changes;app.load_project();assert owner.changes
                app.save_project();assert app.open_last_project() and app.active_module=='Battle deployment' and app.doc.filename==owner.filename
                app.search.set('Majide');app.filter();assert app.tree.get_children();app.search.set('');app.filter()
                # Read-only battlefield links appear on the first prologue deployment.
                app.switch_module('Battle deployment',source_file='Dispos/SC00_00.bin');assert app.deployment_maps_tree.get_children()
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'deployment-units.png')],check=True)
                app.deployment_form.select(2);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'deployment-ai.png')],check=True)
                # A folder with only Dispos sources is usable, including empty native groups.
                standalone=temporary/'standalone';(standalone/'Dispos').mkdir(parents=True)
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                from fixture import deployment_fixture
                (standalone/'Dispos/SYNTHETIC.bin').write_bytes(deployment_fixture())
                assert app.open_data(standalone/'Dispos/SYNTHETIC.bin') and len(app.documents)==1
                assert app.switch_module('Battle deployment','units:1') and not app.widgets and app.learning_row is None
                assert app.doc.owner.build()==app.doc.raw
                for name,digest in hashes.items():assert hashlib.sha256((base/'Dispos'/name).read_bytes()).digest()==digest
                assert not callbacks,callbacks
                print('PASS: 42 deployment fields, English PID/IID pickers, signed/flag bounds, cross-file copy/reset, current item links and exact navigation, 204-file nested export, source immutability, project re-open, empty groups, battlefield links and compact layout.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
