"""New lists, whole-list copies, character assignment and versioned reopening."""
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
hashes={name:hashlib.sha256((base/name).read_bytes()).digest() for name in ('Growth.bin','Person.bin')}
new='LID_Custom_新規';copy='LID_Copy_Dietrich';dit='PID_ディートリヒ';sid='SID_主人公用輸送隊'
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Learning tables','LID_ディートリヒ');d=app.doc
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(label,key=None):
                    with patch.object(simpledialog,'askstring',return_value=key) as prompt:
                        app.learning_list_actions[label].invoke();app.update()
                    return prompt
                assert str(app.learning_list_actions['Remove new list'].cget('state'))=='disabled'
                write(0x20,'999');prompt=action('New list…',new)
                assert not prompt.called and not d.new_lists and len(errors)==1
                write(0x20,'17');action('New list…',new)
                assert app.current.pid==new and len(app.tree.get_children())==97
                assert not app.widgets and not app.learning_tree.get_children() and d.added_list_count==1
                assert '1 new lists' in app.count_label.cget('text')
                app.learning_actions['Add entry'].invoke();app.update();write(0x28,sid);assert app.apply()
                assert app.switch_module('Learning tables','LID_ディートリヒ')
                action('Duplicate list…',copy)
                assert app.current.pid==copy and len(app.learning_tree.get_children())==56 and d.added_list_count==2
                assert d.value(d.rows_by_table[copy][0],d.by_offset[0x20])==17
                write(0x28,sid);write(0x38,'independent list');assert app.apply()
                assert d.value(d.rows_by_table['LID_ディートリヒ'][0],d.by_offset[0x38])==[]
                before=d.project();action('New list…',copy);assert len(errors)==2 and d.project()==before
                action('New list…',None);assert d.project()==before
                # Assign the custom ID with the actual character reference chooser.
                assert app.switch_module('Characters',dit)
                field,widget=app.widgets[0x88];widget.delete('1.0','end')
                options=app.suggestions(field)
                observed={value for row in app.doc.records for value in app.doc.value(row,field)}
                legion_only=next(key for key in app.documents['Legion'].by_pid if key not in d.tables_by_id and key not in observed)
                assert new in options and copy in options and legion_only not in options
                app.pick(field,widget)
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==copy))
                next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke();assert app.apply()
                assert app.doc.value(app.current,field)==[copy]
                assert app.switch_module('Learning tables',copy)
                assert any(app.learning_users_tree.item(i,'values')[2]==dit for i in app.learning_users_tree.get_children())
                action('Remove new list');assert len(errors)==3 and copy in d.tables_by_id
                # Live SID usages target a row inside the new list.
                assert app.switch_module('Skills',sid);app.skill_usage_refresh()
                target=next(i for i,u in enumerate(app.skill_usage_targets) if u.module=='Learning tables' and u.table==copy and u.row==0)
                app.skill_usage_tree.selection_set(str(target));app.skill_usage_open()
                assert app.current.pid==copy and app.learning_row.pid==copy+'::0'
                # Remove another, unassigned new list and keep the copy's identity.
                app.switch_module('Learning tables',new);action('Remove new list')
                assert new not in d.tables_by_id and d.tables_by_id[copy].index==96
                app.switch_module('Characters',dit);assert new not in app.suggestions(app.doc.by_offset[0x88])
                app.switch_module('Learning tables',copy);app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                growth=project['documents']['Growth.bin'];assert growth['format']=='fw-growth-edits-v4' and growth['new_lists']==[copy]
                result=fw.Learning((temporary/'mod/romfs/GameData/Growth.bin').read_bytes())
                assert len(result.collections)==97 and len(result.rows_by_table[copy])==56
                person=fw.Person((temporary/'mod/romfs/GameData/Person.bin').read_bytes())
                assert person.original(person.by_pid[dit],person.by_offset[0x88])==[copy]
                assert len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                # Replacing a v4 project while its new table is selected is safe.
                legacy=fw.suite_project(app.documents);legacy['documents']['Growth.bin']=fw.Learning(d.raw).project()
                legacy['documents']['Person.bin']=fw.Person(app.documents['Characters'].raw).project()
                old=temporary/'old.json';old.write_text(json.dumps(legacy,ensure_ascii=False),encoding='utf8')
                with patch.object(filedialog,'askopenfilename',return_value=str(old)):app.load_project()
                assert not d.new_lists and app.current.pid in d.tables_by_id
                app.load_project();assert d.new_lists==[copy];app.switch_module('Learning tables',copy)
                app.save_project();assert app.open_last_project() and app.documents['Learning tables'].new_lists==[copy]
                app.switch_module('Learning tables',copy);app.geometry('1000x680');app.update()
                for button in [*app.learning_actions.values(),*app.learning_list_actions.values()]:
                    assert button.winfo_rootx()+button.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                    assert button.winfo_rooty()+button.winfo_height()<=app.winfo_rooty()+app.winfo_height()
                app.geometry('1180x780');app.update();previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'learning-new-list.png')],check=True)
                for name,digest in hashes.items():assert hashlib.sha256((base/name).read_bytes()).digest()==digest
                assert not callbacks,callbacks
                print('PASS: New/Duplicate/Remove list controls, unique IDs and cancellation, invalid-input blocking, whole-list copies, live character chooser/assignment, assigned-list removal guard, SID links, 204-file export, v4 project/reopen/legacy replacement and compact layout.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
