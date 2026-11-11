"""Real widgets: append, duplicate, undo, save/reopen, usages and mod exports."""
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
source_hash=hashlib.sha256((base/'Growth.bin').read_bytes()).digest()
key='LID_ディートリヒ';sid='SID_主人公用輸送隊'
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Learning tables',key)
                d=app.doc;old_rows=list(d.rows_by_table[key])
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(text):app.learning_actions[text].invoke();app.update()
                action('Add entry');assert len(d.rows_by_table[key])==57 and app.learning_row.index==56
                assert not d.changes and d.modified and '1 added entries' in app.count_label.cget('text')
                assert [r.pid for r in d.rows_by_table[key][:56]]==[r.pid for r in old_rows]
                write(0x20,'999');action('Duplicate entry');assert len(d.rows_by_table[key])==57
                assert errors and len(errors)==1
                write(0x20,'24');write(0x28,sid);write(0x38,'3部\nexpansion_test');assert app.apply()
                action('Duplicate entry');assert app.learning_row.index==57 and d.added_count==2
                assert d.value(app.learning_row,d.by_offset[0x28])==sid
                write(0x38,'independent');assert app.apply()
                assert d.value(d.rows_by_table[key][56],d.by_offset[0x38])==['3部','expansion_test']
                action('Undo last addition');assert d.added_count==1 and app.learning_row.index==56
                action('Duplicate entry');assert d.added_count==2
                # The usage browser navigates directly to the added learning row.
                added=app.learning_row.pid
                assert app.switch_module('Skills',sid);app.skill_usage_refresh()
                index=next(i for i,use in enumerate(app.skill_usage_targets) if use.module=='Learning tables' and use.record==added)
                app.skill_usage_tree.selection_set(str(index));app.skill_usage_open()
                assert app.active_module=='Learning tables' and app.learning_row.pid==added
                # GLID and auxiliary edits share the same Growth export.
                assert app.switch_module('GLID progression','GLID_ディートリヒ');write(0x28,'ExpansionClass');assert app.apply()
                assert app.switch_module('Progression & Difficulty',source_file='Growth.bin',section='exp_curve')
                write(0x22,'1234');assert app.apply()
                assert app.switch_module('Learning tables',key)
                app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                growth=project['documents']['Growth.bin'];assert growth['format']=='fw-growth-edits-v3' and len(growth['new_entries'])==2
                target=temporary/'mod/romfs/GameData/Growth.bin';result=fw.Learning(target.read_bytes())
                assert len(result.rows_by_table[key])==58
                for row in result.rows_by_table[key][-2:]:assert result.original(row,result.by_offset[0x28])==sid
                assert result.progression.original(result.progression.rows_by_table['GLID_ディートリヒ'][0],result.progression.fields[1])=='ExpansionClass'
                assert len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                app.reset();assert len(d.rows_by_table[key])==56 and not d.added_count and d.changes
                app.load_project();assert app.doc.added_count==2 and len(app.learning_tree.get_children())==58
                app.save_project();assert app.open_last_project() and app.active_module=='Learning tables'
                assert app.doc.added_count==2 and len(app.learning_tree.get_children())==58
                app.learning_tree.selection_set(added);app.learning_tree.see(added);app.update()
                app.geometry('1000x680');app.update()
                for button in app.learning_actions.values():
                    assert button.winfo_rootx()+button.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'learning-additions.png')],check=True)
                # Empty source list, standalone loading and replacement confirmation.
                sys.path.insert(0,str(Path(__file__).resolve().parent))
                from fixture import growth_fixture
                from test_learning_entries import emptied
                standalone=temporary/'standalone';standalone.mkdir()
                (standalone/'Growth.bin').write_bytes(emptied(growth_fixture(),'LID_SYNTHETIC_B'))
                assert app.open_data(standalone/'Growth.bin') and app.switch_module('Learning tables','LID_SYNTHETIC_B')
                assert not app.learning_tree.get_children() and str(app.learning_actions['Duplicate entry'].cget('state'))=='disabled'
                action('Add entry');assert len(app.learning_tree.get_children())==1 and not app.doc.changes
                with patch.object(messagebox,'askyesno',return_value=False) as question:
                    app.load_project();assert question.call_count==1 and app.doc.added_count==1
                action('Undo last addition');assert not app.learning_tree.get_children() and not app.widgets
                assert not app.doc.modified
                assert hashlib.sha256((base/'Growth.bin').read_bytes()).digest()==source_hash
                assert not callbacks,callbacks
                print('PASS: real Add/Duplicate/Undo controls, empty lists, invalid input blocking, independent added values, live skill usages, shared GLID/auxiliary export, 204 files, v3 project/reopen/reset, standalone sources and unsaved-addition confirmation.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
