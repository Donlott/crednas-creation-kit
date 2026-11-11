"""Legion widgets, explicit LID lookup, live direct links and safe joint export."""
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
fingerprint=hashlib.sha256((base/'Legion.bin').read_bytes()).digest()
lid='LID_ダグザ戦士隊';second='LID_ダグザ槍兵隊'
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                assert app.switch_module('Legion',lid);doc=app.doc;row=app.current
                assert len(app.widgets)==28 and len(app.tree.get_children())==109
                assert app.heading.get()=='Trap Springers' and len(app.notebook.tabs())==4
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(text):next(w for w in app.legion_tools.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==text).invoke()
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                choose(0x38,'SID_主人公用輸送隊','SID_主人公用輸送隊');write(0x30,'55');write(0x31,'255');write(0x70,'-32768');write(0x98,'65535')
                write(0x48,'IID_試作品１号|||\nIID_青銅の剣');write(0x58,'SID_主人公用輸送隊');write(0x88,'LEGION_TEST\n!blocked');write(0xa0,'AID_LEGION_TEST\n!AID_LEGION_NEGATIVE')
                assert app.apply();assert app.tree.set(str(row.index),'serial')=='55'
                app.filter();assert app.tree.set(str(row.index),'serial')=='55'
                write(0x70,'-32769');assert not app.switch_module('Items');write(0x70,'-32768');assert app.apply()
                action('Copy values');app.switch_module('Legion',second);action('Paste values');assert app.current.pid==second and doc.value(app.current,doc.by_offset[0x31])==255
                app.reset();assert not any(key[0]==second for key in doc.changes) and any(key[0]==lid for key in doc.changes)
                app.switch_module('Legion',lid);app.legion_links_refresh()
                i=next(i for i,t in enumerate(app.legion_links) if t[0]=='Battle deployment')
                source,pid=app.legion_links[i][1:];app.legion_links_tree.selection_set(str(i));app.legion_links_open()
                assert app.doc.filename==source and app.learning_row.pid==pid and app.doc.value(app.learning_row,app.doc.by_offset[0x40])==lid
                # Context-specific picker must offer legion records, never learning-table collections.
                from deployment_ui import suggestions
                values=suggestions(app,app.doc.by_offset[0x40]);assert lid in values and 'LID_ディートリヒ' not in values
                app.deployment_links_refresh();i=next(i for i,t in enumerate(app.deployment_links) if t[0]=='Legion' and t[2]==lid)
                app.deployment_links_tree.selection_set(str(i));app.deployment_links_open();assert app.active_module=='Legion' and app.current.pid==lid
                app.switch_module('Items','IID_試作品１号|||',source_file='Item_P1.bin');app.item_usage_refresh()
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Legion' and u.record==lid)
                app.item_usage_tree.selection_set(str(i));app.item_usage_open();assert app.active_module=='Legion' and app.current.pid==lid
                app.switch_module('Skills','SID_主人公用輸送隊');app.skill_usage_refresh()
                i=next(i for i,u in enumerate(app.skill_usage_targets) if u.module=='Legion' and u.record==lid)
                app.skill_usage_tree.selection_set(str(i));app.skill_usage_open();assert app.active_module=='Legion'
                app.switch_module('AIDs','AID_LEGION_TEST');assert app.asset_index.direct_count('AID_LEGION_TEST')==1
                user=next(u for u in app.asset_index.users['AID_LEGION_TEST'] if u.module=='Legion');assert user.record==lid
                app.switch_module('Legion',lid);app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==204
                assert project['documents']['Legion.bin']['format']=='fw-legion-edits-v1'
                result=fw.Legion((temporary/'mod/romfs/GameData/Legion.bin').read_bytes())
                for key,value in doc.changes.items():assert result.original(*result.edit_target(*key))==value
                assert len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                app.reset();app.load_project();assert doc.value(row,doc.by_offset[0x70])==-32768
                app.save_project();assert app.open_last_project() and app.active_module=='Legion'
                app.search.set('Trap Springers');app.filter();assert app.tree.get_children();app.search.set('');app.filter()
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.switch_module('Legion',lid);app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'legion-definition.png')],check=True)
                app.notebook.select(3);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'legion-links.png')],check=True)
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Legion.bin').write_bytes((base/'Legion.bin').read_bytes())
                assert app.open_data(standalone/'Legion.bin') and set(app.documents)=={'Legion'} and app.active_module=='Legion'
                app.switch_module('Legion','LID_無し');assert app.current.pid=='LID_無し'
                assert hashlib.sha256((base/'Legion.bin').read_bytes()).digest()==fingerprint
                assert not callbacks,callbacks
                print('PASS: all 28 Legion fields, English names, bounds, copy/reset, scoped LID lookup, bidirectional deployment/IID/SID/AID links, 204-file export, source preservation, project reopen and standalone loading.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
