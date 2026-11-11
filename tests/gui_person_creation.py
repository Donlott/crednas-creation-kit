"""Actual character controls, slot guards, PID choosers and deployment navigation."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
blank='PID_New_新規|||';copy='PID_Custom_Dietrich';second='PID_Second'
digest=hashlib.sha256((base/'Person.bin').read_bytes()).digest()
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Characters','PID_ディートリヒ');doc=app.doc
                original_slots={r.pid:doc.value(r,doc.by_offset[0x30]) for r in doc.records}
                def write(off,value):
                    f,w=app.widgets[off]
                    if f.kind in fw.LIST_TYPES:w.delete('1.0','end');w.insert('1.0',value)
                    else:w.delete(0,'end');w.insert(0,value)
                def action(label,key=None,serial=0):
                    app.notebook.select(0)
                    with patch.object(simpledialog,'askstring',return_value=key) as prompt,patch.object(simpledialog,'askinteger',return_value=serial):
                        app.character_creation_actions[label].invoke();app.update()
                    return prompt
                def choose(off,key):
                    f,w=app.widgets[off];app.pick(f,w)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel));tree=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    tree.selection_set(next(i for i in tree.get_children() if tree.item(i,'values')[1]==key))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert str(app.character_creation_actions['Remove new character'].cget('state'))=='disabled'
                assert len(app.widgets)==142 and 0x30 not in app.widgets
                write(0x1c2,'32768');prompt=action('New character…',blank)
                assert not prompt.called and not doc.new_characters and len(errors)==1,(prompt.called,doc.new_characters,errors,callbacks)
                write(0x1c2,'44');action('Duplicate character…',copy,42)
                assert app.current.pid==copy and len(app.widgets)==142 and doc.value(app.current,doc.by_offset[0x1c2])==44
                assert doc.value(app.current,doc.by_offset[0x30])==42 and 'dietrich' in app.translate_value(copy).text.lower()
                assert 0x30 not in app.widgets
                action('New character…',blank)
                assert app.current.pid==blank and doc.value(app.current,doc.by_offset[0x30])==0
                assert not app.variants.get() and app.tree.exists(str(app.current.index)), 'new serial-zero entry must stay visible'
                before=doc.project();action('New character…',blank);assert len(errors)==2 and doc.project()==before
                action('New character…','PID_Occupied',42);assert len(errors)==3 and doc.project()==before
                action('New character…',None);action('New character…','PID_CancelSerial',None);assert doc.project()==before
                action('Duplicate character…',second);assert doc.value(app.current,doc.by_offset[0x30])==0
                # New PIDs appear in every relevant reference chooser.
                checks=[('Classes',0x1e8,{'record_id':'JID_闘士'}),('Skills',0x2a0,{'record_id':'SID_主人公用輸送隊'}),
                        ('Facilities & Rewards',0x20,{'source_file':'Facility.bin','section':'questions'}),
                        ('Supports & Recruitment',0x20,{'section':'special'}),
                        ('Progression & Difficulty',0x20,{'source_file':'Person.bin','section':'auto_gear'}),
                        ('Appearance rules',0x20,{'source_file':'AssetTable.bin','section':'rules'})]
                for module,off,kwargs in checks:
                    assert app.switch_module(module,**kwargs),(module,kwargs)
                    assert copy in app.suggestions(app.doc.by_offset[off]),module
                app.switch_module('Characters',second);assert copy in app.suggestions(doc.by_offset[0x268])
                choose(0x268,copy);assert app.apply()
                battle=next(d for d in app.documents.values() if isinstance(d,fw.Deployment) and d.views['units'].records)
                view=battle.views['units'];unit=view.records[0]
                app.switch_module('Battle deployment',unit.pid,source_file=battle.filename)
                assert copy in app.suggestions(app.doc.by_offset[0x20]);choose(0x20,copy);assert app.apply()
                app.switch_module('Characters',copy);action('Remove new character');assert copy in doc.new_characters and len(errors)==4
                app.notebook.select(6);app.update();assert app.character_usage_targets
                assert any(u.module=='Characters' and u.record==second for u in app.character_usage_targets)
                index=next(i for i,u in enumerate(app.character_usage_targets) if u.module=='Battle deployment')
                app.character_usage_tree.selection_set(str(index));app.character_usage_open();app.update()
                assert app.active_module=='Battle deployment' and app.learning_row.pid==unit.pid
                assert app.widgets[0x20][1].get()==copy
                app.switch_module('Characters',blank);action('Remove new character');assert blank not in doc.by_pid
                assert doc.by_pid[copy].index==2923 and doc.by_pid[second].index==2924
                app.switch_module('Characters',copy);write(0x1c2,'55');assert app.apply();app.reset()
                assert doc.value(app.current,doc.by_offset[0x1c2])==44 and doc.value(app.current,doc.by_offset[0x30])==42
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert project['documents']['Person.bin']['format']=='fw-character-edits-v3'
                result=fw.Person((temporary/'mod/romfs/GameData/Person.bin').read_bytes())
                assert len(result.records)==2925 and len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                assert result.original(result.by_pid[second],result.by_offset[0x268])==copy
                assert all(result.original(result.by_pid[key],result.by_offset[0x30])==serial for key,serial in original_slots.items())
                old=fw.suite_project(app.documents);old['documents']['Person.bin']=fw.Person(doc.raw).project()
                old_path=temporary/'old.json';old_path.write_text(json.dumps(old),encoding='utf8')
                with patch.object(filedialog,'askopenfilename',return_value=str(old_path)):app.load_project()
                assert not doc.new_characters and app.current.pid in doc.by_pid and copy not in app.live_character_names
                app.load_project();app.switch_module('Characters',copy);app.save_project()
                assert app.open_last_project() and app.active_module=='Characters' and copy in app.doc.new_characters and len(app.documents)==204
                app.switch_module('Characters',copy);app.notebook.select(0);app.geometry('1000x680');app.update()
                for b in app.character_creation_actions.values():assert b.winfo_rootx()+b.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update();previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'character-creation.png')],check=True)
                assert hashlib.sha256((base/'Person.bin').read_bytes()).digest()==digest and not callbacks,callbacks
                print('PASS: 143 fields; New/Duplicate/Remove; serial uniqueness/zero/cancel/immutability; visible new entries; live PID choosers/names; deployment assignment/exact usage navigation/removal guard; v3/reset/legacy/reopen; original slots; 204-file export; source hash; compact layout.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
