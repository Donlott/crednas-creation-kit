"""Actual Tk class creation, live references, pointer exports and older-project replacement."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
blank='JID_New_新規|||';copy='JID_Custom_Gladiator';second='JID_Second'
digest=hashlib.sha256((base/'Job.bin').read_bytes()).digest()
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Classes','JID_闘士');doc=app.doc
                def write(offset,value):
                    f,w=app.widgets[offset]
                    if f.kind in fw.LIST_TYPES:w.delete('1.0','end');w.insert('1.0',value)
                    else:w.delete(0,'end');w.insert(0,value)
                def action(label,key=None):
                    app.notebook.select(0)
                    with patch.object(simpledialog,'askstring',return_value=key) as prompt:
                        app.class_creation_actions[label].invoke();app.update()
                    return prompt
                def choose(offset,target):
                    f,w=app.widgets[offset];app.pick(f,w)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    tree=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    tree.selection_set(next(i for i in tree.get_children() if tree.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert str(app.class_creation_actions['Remove new class'].cget('state'))=='disabled'
                write(0x120,'32768');prompt=action('New class…',blank)
                assert not prompt.called and not doc.new_classes and len(errors)==1
                write(0x120,'39');action('Duplicate class…',copy)
                assert app.current.pid==copy and len(app.widgets)==134 and doc.value(app.current,doc.by_offset[0x120])==39
                assert 'gladiator' in app.translate_value(copy).text.lower()
                assert doc.value(app.current,doc.by_offset[0x48])==doc.value(doc.by_pid['JID_闘士'],doc.by_offset[0x48])
                write(0x31,'2');assert app.apply();assert app.tree.set(str(app.current.index),'serial')=='2'
                action('New class…',blank);assert app.current.pid==blank and len(app.widgets)==134
                before=doc.project();action('New class…',blank);assert len(errors)==2 and doc.project()==before
                action('New class…',None);assert doc.project()==before
                action('New class…',second);choose(0x48,copy);assert app.apply()
                app.switch_module('Classes',copy);choose(0x50,second);assert app.apply()
                # All current class reference choosers see newly created IDs.
                for module,offset,kwargs in [('Characters',0x38,{'record_id':'PID_ディートリヒ'}),
                      ('Skills',0x248,{'record_id':'SID_主人公用輸送隊'}),
                      ('Facilities & Rewards',0x78,{'source_file':'Facility.bin','section':'training'}),
                      ('Progression & Difficulty',0x20,{'source_file':'Growth.bin','section':'auto_class'}),
                      ('Appearance rules',0x20,{'source_file':'AssetTable.bin','section':'rules'})]:
                    assert app.switch_module(module,**kwargs),(module,kwargs)
                    assert copy in app.suggestions(app.doc.by_offset[offset]),module
                app.switch_module('Characters','PID_ディートリヒ');choose(0x38,copy);assert app.apply()
                app.switch_module('GLID progression','GLID_ディートリヒ');write(0x20,'0')
                assert copy.removeprefix('JID_') in app.suggestions(app.doc.fields[1])
                level=app.progression_level;write(app.doc.fields[level].offset,copy.removeprefix('JID_'));assert app.apply()
                assert 'gladiator' in app.translate_value(copy.removeprefix('JID_')).text.lower()
                app.switch_module('Classes',copy);action('Remove new class');assert copy in doc.new_classes and len(errors)==3
                app.class_usage_refresh();targets=app.class_usage_targets
                assert any(u.module=='Characters' for u in targets)
                index=next(i for i,u in enumerate(targets) if u.module=='GLID progression')
                app.class_usage_tree.selection_set(str(index));app.class_usage_open();app.update()
                assert app.active_module=='GLID progression' and app.progression_level==level
                assert app.widgets[app.doc.fields[level].offset][1].get()==copy.removeprefix('JID_')
                app.switch_module('Classes',blank);action('Remove new class');assert blank not in doc.by_pid
                assert doc.by_pid[copy].index==137 and doc.by_pid[second].index==138
                app.switch_module('Classes',copy);write(0x120,'55');assert app.apply();app.reset()
                assert doc.value(app.current,doc.by_offset[0x120])==39 and copy in doc.new_classes
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert project['documents']['Job.bin']['format']=='fw-class-edits-v2'
                result=fw.Job((temporary/'mod/romfs/GameData/Job.bin').read_bytes())
                assert result.original(result.by_pid[second],result.by_offset[0x48])==copy
                assert len(result.records)==139 and len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                old=fw.suite_project(app.documents);old['documents']['Job.bin']=fw.Job(doc.raw).project()
                old_path=temporary/'old.json';old_path.write_text(json.dumps(old),encoding='utf8')
                with patch.object(filedialog,'askopenfilename',return_value=str(old_path)):app.load_project()
                assert not doc.new_classes and app.current.pid in doc.by_pid and copy not in app.live_class_names
                app.load_project();app.switch_module('Classes',copy);app.save_project()
                assert app.open_last_project() and app.active_module=='Classes' and copy in app.doc.new_classes and len(app.documents)==204
                app.switch_module('Classes',copy)
                app.notebook.select(0);app.geometry('1000x680');app.update()
                for b in app.class_creation_actions.values():assert b.winfo_rootx()+b.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update();previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'class-creation.png')],check=True)
                assert hashlib.sha256((base/'Job.bin').read_bytes()).digest()==digest
                assert not callbacks,callbacks
                print('PASS: 134 class widgets; New/Duplicate/Remove; current copies; direct new links; live names/ranks/JID choosers; incoming character/GLID navigation and removal guard; reset/v2/older project/reopen; 204-file export; immutable source; compact layout.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
