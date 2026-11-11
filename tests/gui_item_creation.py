"""Item creation, live choosers, guarded removal and complete project/export UI."""
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
hashes={k.filename:hashlib.sha256((base/k.filename).read_bytes()).digest() for k in fw.ITEM_TABLES}
blank='IID_New_新規|||';copy='IID_Custom_Sword';side_id='IID_Custom_Side|||';sid='SID_主人公用輸送隊'
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Items','IID_木製の剣');main=app.doc
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(label,key=None):
                    app.notebook.select(0)
                    with patch.object(simpledialog,'askstring',return_value=key) as prompt:
                        app.item_creation_actions[label].invoke();app.update()
                    return prompt
                def choose(offset,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert str(app.item_creation_actions['Remove new item'].cget('state'))=='disabled'
                write(0x4c,'-1');prompt=action('New item…',blank)
                assert not prompt.called and not main.new_items and len(errors)==1
                write(0x4c,str(main.original(app.current,main.by_offset[0x4c])))
                action('New item…',blank);assert app.current.pid==blank and len(app.widgets)==80 and main.added_item_count==1
                assert not main.changes and main.modified and main.record_changed(blank)
                write(0x48,'2');assert app.apply();assert str(app.tree.set(str(app.current.index),'serial'))=='2'
                app.switch_module('Items','IID_木製の剣');write(0x4c,'777');action('Duplicate item…',copy)
                assert app.current.pid==copy and main.value(app.current,main.by_offset[0x4c])==777
                assert len(app.widgets)==80 and main.added_item_count==2 and 'sword' in app.translate_value(copy).text.lower()
                write(0x98,sid);assert app.apply()
                before=main.project();action('New item…',copy);assert len(errors)==2 and main.project()==before
                action('New item…',None);assert main.project()==before
                side=next(d for d in app.documents.values() if d.filename=='Item_P1.bin')
                app.switch_module('Items',side.records[0].pid,source_file=side.filename)
                action('New item…',copy);assert not side.new_items and len(errors)==3
                action('Duplicate item…',side_id);assert app.doc is side and side_id in side.by_pid and side.added_item_count==1
                write(0x4c,'123');assert app.apply()
                # Every IID-aware module receives the new IDs without rebuilding source indexes.
                checks=[('Classes',0x80,{'record_id':'JID_闘士'}),('Skills',0x238,{'record_id':sid}),
                        ('Legion',0x48,{}),('Profiles & Affiliations',0xf0,{'section':'profiles'}),
                        ('Facilities & Rewards',0x68,{'source_file':'Facility.bin','section':'training'}),
                        ('Supports & Recruitment',0x50,{'section':'scout'}),
                        ('Progression & Difficulty',0x20,{'source_file':'Growth.bin','section':'auto_items'})]
                for module,offset,kwargs in checks:
                    assert app.switch_module(module,**kwargs),(module,kwargs)
                    values=app.suggestions(app.doc.by_offset[offset]);assert copy in values and side_id in values,module
                battle=next(d for d in app.documents.values() if isinstance(d,fw.Deployment) and d.records)
                group=next(k for k,rows in battle.views['units'].rows_by_table.items() if rows)
                assert app.switch_module('Battle deployment',group,source_file=battle.filename)
                assert copy in app.suggestions(app.doc.by_offset[0x68])
                assert app.switch_module('GLID progression','GLID_ディートリヒ')
                original=app.widgets[0x20][1].get();write(0x20,'4')
                assert copy.removeprefix('IID_') in app.suggestions(app.doc.fields[1]);write(0x20,original)
                assert app.switch_module('Characters','PID_ディートリヒ')
                write(0x78,'');choose(0x78,copy);assert app.apply()
                assert 'sword' in app.translate_value(copy).text.lower()
                assert app.switch_module('Shop & Loot',source_file='Item.bin',section='shops')
                assert copy in app.suggestions(app.doc.by_offset[0x28]);choose(0x28,copy);assert app.apply()
                assert app.switch_module('Items',copy)
                assert app.current.pid==copy and app.doc is main
                action('Remove new item');assert copy in main.new_items and len(errors)==4,(list(main.new_items),errors)
                app.item_usage_refresh();assert any(u.module=='Characters' for u in app.item_usage_targets)
                assert any(u.module=='Shop & Loot' for u in app.item_usage_targets)
                # An unassigned new item can be removed; existing indexes stay stable.
                app.switch_module('Items',blank);action('Remove new item')
                assert blank not in main.by_pid and main.by_pid[copy].index==1356
                app.switch_module('Items',copy);assert blank not in app.suggestions(main.by_offset[0x108])
                assert app.switch_module('Skills',sid);app.skill_usage_refresh()
                index=next(i for i,u in enumerate(app.skill_usage_targets) if u.module=='Items' and u.record==copy and u.source=='Item.bin')
                app.skill_usage_tree.selection_set(str(index));app.skill_usage_open();assert app.current.pid==copy
                # Reset restores creation-time copy values and retains the new definition.
                write(0x4c,'999');assert app.apply();app.reset()
                assert copy in main.new_items and main.value(main.by_pid[copy],main.by_offset[0x4c])==777
                app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert project['documents']['Item.bin']['format']=='fw-item-edits-v3'
                assert project['documents']['Item_P1.bin']['format']=='fw-item-edits-v3'
                assert len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                for owner in (main,side):
                    result=type(owner)((temporary/'mod/romfs/GameData'/owner.filename).read_bytes())
                    for key in owner.new_items:
                        for field in owner.fields:assert result.original(result.by_pid[key],field)==owner.value(owner.by_pid[key],field)
                # Older projects can replace additions while the removed IID is selected.
                old=fw.suite_project(app.documents)
                for key,owner in app.documents.items():
                    if isinstance(owner,(fw.Item,fw.Person)):old['documents'][owner.filename]=type(owner)(owner.raw).project()
                old_path=temporary/'old.json';old_path.write_text(json.dumps(old,ensure_ascii=False),encoding='utf8')
                with patch.object(filedialog,'askopenfilename',return_value=str(old_path)):app.load_project()
                assert not main.new_items and app.current.pid in main.by_pid and copy not in app.live_item_names
                app.load_project();assert copy in main.new_items and side_id in side.new_items
                app.switch_module('Items',side_id,source_file='Item_P1.bin');app.save_project()
                assert app.open_last_project() and app.doc.filename=='Item_P1.bin' and side_id in app.doc.new_items
                app.switch_module('Items',copy);app.notebook.select(0);app.geometry('1000x680');app.update()
                for button in app.item_creation_actions.values():assert button.winfo_rootx()+button.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update();previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'item-creation.png')],check=True)
                for name,digest in hashes.items():assert hashlib.sha256((base/name).read_bytes()).digest()==digest
                assert not callbacks,callbacks
                print('PASS: all80 new item fields; New/Duplicate/Remove; 3 sources; Unicode/pipes; invalid input/collisions/cancel; live item names/types; all IID chooser modules; inventory/shop placements and removal guard; skill links; v3/legacy/reopen/reset; 204-file export and source preservation.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
