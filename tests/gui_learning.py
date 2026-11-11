"""Exercise real LID editing, entry operations, navigation and combined export."""
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
                app.read_names(english);assert app.switch_module('Learning tables','LID_無し')
                assert not app.learning_tree.get_children() and not app.widgets and app.apply()
                assert app.switch_module('Learning tables','LID_ディートリヒ')
                assert len(app.tree.get_children())==96
                assert len(app.learning_tree.get_children())==56
                assert len(app.widgets)==5
                assert app.heading.get()=='Dietrich'
                app.search.set('Majide');app.update();assert len(app.tree.get_children())==1
                app.tree.selection_set(str(app.doc.tables_by_id['LID_マジーデ'].index));app.select()
                assert len(app.learning_tree.get_children())==44
                app.search.set('');app.switch_module('Learning tables','LID_ディートリヒ')
                # Edit all data kinds through actual form widgets.
                for offset,value in ((0x20,'19'),(0x21,'12'),(0x22,'9')):
                    widget=app.widgets[offset][1];widget.delete(0,'end');widget.insert(0,value)
                field,widget=app.widgets[0x28];app.pick(field,widget)
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry))
                app.setvar(entry.cget('textvariable'),'SID_主人公用輸送隊')
                listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                assert listing.get_children();listing.selection_set(listing.get_children()[0])
                next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                condition=app.widgets[0x38][1];condition.delete('1.0','end');condition.insert('1.0','3部\ntest_condition')
                app.update();app.after(180,app.quit);original_loop(app)
                assert 'convoy' in app.previews[0x28][0].cget('text').lower()
                assert app.apply();assert len(app.doc.changes)==5
                first=app.doc.rows_by_table['LID_ディートリヒ'][0]
                assert app.doc.value(first,app.doc.by_offset[0x20])==19
                # Copy/paste replaces values only, preserving entry identities/counts.
                entries=app.nametowidget(app.notebook.tabs()[0])
                tools=next(w for w in entries.winfo_children() if isinstance(w,ttk.Frame) and not isinstance(w,ttk.Panedwindow))
                actions={w.cget('text'):w for w in tools.winfo_children() if isinstance(w,ttk.Button)}
                actions['Copy entry'].invoke()
                second=app.doc.rows_by_table['LID_ディートリヒ'][1]
                app.learning_tree.selection_set(second.pid);app.update()
                actions['Paste values'].invoke()
                assert app.doc.value(second,app.doc.by_offset[0x20])==19
                actions['Swap ↓'].invoke();assert app.learning_row.index==2
                assert len(app.doc.rows_by_table['LID_ディートリヒ'])==56
                # Invalid input blocks leaving the module and retains form values.
                number=app.widgets[0x20][1];number.delete(0,'end');number.insert(0,'999')
                assert not app.switch_module('Characters');assert app.active_module=='Learning tables'
                number.delete(0,'end');number.insert(0,'19');assert app.apply()
                app.geometry('1000x680');app.update()
                assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'learning.png')],check=True)
                app.save_project();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert set(project['documents'])=={d.filename for d in app.documents.values()}
                app.export()
                exported=fw.Learning((temporary/'mod/romfs/GameData/Growth.bin').read_bytes())
                self_row=exported.rows_by_table['LID_ディートリヒ'][0]
                assert exported.value(self_row,exported.by_offset[0x28])=='SID_主人公用輸送隊'
                app.reset();assert not app.doc.changes
                app.load_project();assert app.doc.changes
                app.notebook.select(1);app.update();users=app.learning_users_tree
                target=next(i for i in users.get_children() if users.item(i,'values')[2]=='PID_ディートリヒ')
                users.selection_set(target)
                tab=app.nametowidget(app.notebook.tabs()[1])
                next(w for w in tab.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.active_module=='Characters' and app.current.pid=='PID_ディートリヒ'
                assert app.documents['Learning tables'].changes
                # The startup reopening path recognizes the new module/project table.
                app.switch_module('Learning tables','LID_ディートリヒ');app.save_project()
                assert app.open_last_project();assert app.active_module=='Learning tables'
                assert app.doc.changes
                standalone=temporary/'learning-only';standalone.mkdir();(standalone/'Growth.bin').write_bytes((base/'Growth.bin').read_bytes())
                app.open_data(standalone/'Growth.bin')
                assert app.active_module=='Learning tables' and set(app.documents)=={'Learning tables'}
                assert app.doc.collections and not app.learning_users_tree.get_children()
                print('PASS: LID GUI search, all five fields, English chooser/previews, copy/paste/swap, input blocking, saved projects, Growth export, reset, character navigation and project reopening.')
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
