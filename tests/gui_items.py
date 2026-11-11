"""Actual IID forms, side-file IDs, live SID/item/GLID navigation and exports."""
from pathlib import Path
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
original_loop=tk.Tk.mainloop;failures=[];errors=[]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Items','IID_木製の剣')
                assert len(app.tree.get_children())==1356 and len(app.widgets)==80
                assert len(app.item_source_choice.cget('values'))==3
                assert 'sword' in app.heading.get().lower()
                main=app.doc;record=app.current
                def write(offset,value):
                    f,w=app.widgets[offset]
                    if f.kind in fw.LIST_TYPES:w.delete('1.0','end');w.insert('1.0',value)
                    else:w.delete(0,'end');w.insert(0,value)
                def choose(offset,query,target=None):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    tree=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview));assert tree.get_children()
                    tree.selection_set(next((i for i in tree.get_children() if tree.item(i,'values')[1]==target),tree.get_children()[0]));values=tree.item(tree.selection()[0],'values')
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                    return values
                app.copy_item_button.invoke();assert app.clipboard_get()=='IID_木製の剣'
                app.search.set('sword');app.update();assert app.tree.get_children()
                write(0x4c,'4000000000');write(0x50,'321');write(0x58,'15');write(0x6c,'-5')
                write(0x118,'-1');write(0x11c,'2147483647');write(0x140,'3')
                values=choose(0x130,'IID_青銅の剣');assert values[1]=='IID_青銅の剣' and values[0]!=values[1]
                write(0x98,'');values=choose(0x98,'convoy','SID_主人公用輸送隊');assert values[1]=='SID_主人公用輸送隊'
                app.update();app.after(180,app.quit);original_loop(app)
                assert 'convoy' in app.previews[0x98][0].get('1.0','end-1c').lower()
                assert app.apply() and len(main.changes)>=8
                assert main.value(record,main.by_offset[0x118])==-1
                # Bounds and invalid integers block modules and source changes.
                write(0x4c,'-1');assert not app.switch_module('Characters');write(0x4c,'4000000000')
                write(0x11c,'2147483648');assert not app.switch_module('AIDs');write(0x11c,'2147483647')
                write(0x118,'invalid');app.item_source.set('Item_P0.bin');app.item_source_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc is main and app.item_source.get()=='Item.bin';write(0x118,'-1')
                write(0x4c,'4294967296');assert not app.switch_module('Skills');write(0x4c,'4000000000');assert app.apply()
                assert app.switch_module('Items','IID_開かれし救世の剣',source_file='Item_P0.bin')
                assert len(app.tree.get_children())==16;write(0x4c,'12345');assert app.apply();side=app.doc
                pipe='IID_試作品１号|||'
                assert app.switch_module('Items',pipe,source_file='Item_P1.bin')
                assert len(app.tree.get_children())==16 and app.current.pid==pipe
                app.copy_item_button.invoke();assert app.clipboard_get()==pipe
                write(0x4c,'34321');write(0x120,'IID_木製の剣');assert app.apply()
                app.search.set('|||');app.update();assert any(app.tree.item(i,'values')[1]==pipe for i in app.tree.get_children())
                # Current cross-file forge references navigate to their real source file.
                assert app.switch_module('Items','IID_木製の剣',source_file='Item.bin')
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Items' and u.source=='Item_P1.bin' and u.record==pipe)
                app.item_usage_tree.selection_set(str(i));app.item_usage_open()
                assert app.doc.filename=='Item_P1.bin' and app.current.pid==pipe
                # Unsaved character inventory assignments appear immediately.
                assert app.switch_module('Characters','PID_ディートリヒ')
                widget=app.widgets[0x78][1];old=widget.get('1.0','end-1c');widget.insert('end','\n'+pipe)
                assert app.switch_module('Items',pipe,source_file='Item_P1.bin')
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Characters' and u.record=='PID_ディートリヒ')
                app.item_usage_tree.selection_set(str(i));app.item_usage_open()
                assert app.active_module=='Characters' and app.current.pid=='PID_ディートリヒ'
                # GLID bare item names link to the exact category row and level.
                app.switch_module('Items','IID_傷薬',source_file='Item.bin')
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='GLID progression' and u.table=='GLID_マジーデ' and u.level==5)
                use=app.item_usage_targets[i];app.item_usage_tree.selection_set(str(i));app.item_usage_open();app.update()
                assert app.active_module=='GLID progression' and app.current.pid=='GLID_マジーデ'
                assert app.learning_row.index==use.row and app.progression_level==5
                assert app.widgets[0x48][1].get()=='傷薬'
                # Skill usage now treats loaded item assignments as live editable links.
                app.switch_module('Skills','SID_主人公用輸送隊',source_file='Skill.bin')
                i=next(i for i,u in enumerate(app.skill_usage_targets) if u.module=='Items' and u.record=='IID_木製の剣' and '0x98' in u.field)
                app.skill_usage_tree.selection_set(str(i));app.skill_usage_open()
                assert app.active_module=='Items' and app.current.pid=='IID_木製の剣' and app.doc.filename=='Item.bin'
                write(0x98,'');app.switch_module('Skills','SID_主人公用輸送隊',source_file='Skill.bin')
                assert not any(u.module=='Items' and u.record=='IID_木製の剣' for u in app.skill_usage_targets)
                app.switch_module('Items','IID_木製の剣',source_file='Item.bin');write(0x98,'SID_主人公用輸送隊');assert app.apply()
                assert any(u.module=='Shop & Loot' for u in app.item_usage_targets)
                app.geometry('1000x680');app.notebook.select(1);app.update()
                assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                for tab,name in ((1,'items-stats'),(3,'items-crafting'),(5,'items-usage')):
                    app.notebook.select(tab);app.update()
                    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/(name+'.png'))],check=True)
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert len(project['documents'])==len(app.documents)
                for kind in fw.ITEM_TABLES:
                    source=next(d for d in app.documents.values() if type(d) is kind)
                    result=kind((temporary/'mod/romfs/GameData'/kind.filename).read_bytes())
                    for (pid,offset),value in source.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                app.reset();assert not main.changes and side.changes
                app.load_project();assert main.changes
                app.switch_module('Items',pipe,source_file='Item_P1.bin');app.save_project();assert app.open_last_project()
                assert app.active_module=='Items' and app.doc.filename=='Item_P1.bin' and app.doc.changes
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Item_P1.bin').write_bytes((base/'Item_P1.bin').read_bytes())
                app.open_data(standalone/'Item_P1.bin');assert app.active_module=='Items' and len(app.documents)==1
                assert app.doc.filename=='Item_P1.bin' and len(app.tree.get_children())==16
                assert len(errors)==4,errors
                print('PASS: all 80 IID fields, prices/stats/signed costs, English item/SID pickers, pipe IDs, source isolation, invalid-input blocking, live item/SID/character/exact-GLID navigation, combined exports, reset and saved source restoration.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    sys.argv=['fw_editor.py',str(base)]
    with patch.object(tk.Tk,'mainloop',loop), \
         patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')), \
         patch.object(messagebox,'showinfo'), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))), \
         patch.object(messagebox,'askyesno',return_value=True):fw.main()
    if failures:raise failures[0]
