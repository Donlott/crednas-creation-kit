"""Exercise the real Tk UI under Xvfb; all writes go to a temporary mod folder."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fw_editor

root_path = Path(__file__).resolve().parents[1]
data = Path(os.environ['FW_GAME_DATA'])
english = Path(os.environ['FW_MESSAGES'])
original_loop = tk.Tk.mainloop
failures = []
errors = []

with tempfile.TemporaryDirectory() as temporary:
    temporary = Path(temporary)
    os.environ['FW_EDITOR_CONFIG'] = str(temporary/'config')
    def patched_loop(app, *args, **kwargs):
        def exercise():
            try:
                assert app.doc is not None
                app.read_names(english)
                app.filter()
                diet = app.doc.by_pid['PID_ディートリヒ']
                maj = app.doc.by_pid['PID_マジーデ']
                app.show(diet)
                assert app.heading.get() == 'Dietrich'
                app.variants.set(True); app.filter(); app.search.set('Dietrich')
                assert len(app.tree.get_children()) == 12
                app.variants.set(False); app.filter()
                app.search.set('Majide')
                app.update()
                assert len(app.tree.get_children()) == 1
                app.tree.selection_set(str(maj.index))
                app.select()
                assert app.heading.get() == 'Majide'
                app.search.set('')
                app.tree.selection_set(str(diet.index)); app.select()
                field, class_entry = app.widgets[0x38]
                original_class = class_entry.get()
                # Live single-reference and list translations, without applying raw changes.
                app.notebook.select(0)
                field, appearance = app.widgets[0x278]
                before = dict(app.doc.changes)
                appearance.delete(0,'end'); appearance.insert(0,'AID_マジーデ')
                app.update(); app.after(160,app.quit); original_loop(app)
                assert app.previews[0x278][0].cget('text') == 'Appearance: Majide'
                assert app.doc.changes == before
                appearance.delete(0,'end'); appearance.insert(0,'AID_ディートリヒ')
                field, skills = app.widgets[0x98]
                old_skills = skills.get('1.0','end-1c')
                skills.delete('1.0','end'); skills.insert('1.0','SID_ブレイズ可能_マジーデ\nSID_主人公用輸送隊')
                app.update(); app.after(160,app.quit); original_loop(app)
                english_lines = app.previews[0x98][0].get('1.0','end-1c').splitlines()
                assert english_lines == ['Skill: Blaze enabled / Majide','Skill: Protagonist convoy']
                skills.delete('1.0','end'); skills.insert('1.0',old_skills)
                app.update_preview(0x98)
                # A glossary edit refreshes live previews and persists separately from projects.
                app.glossary('AID_ディートリヒ')
                glossary = next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                form = next(w for w in glossary.winfo_children() if isinstance(w,ttk.Frame))
                entries = [w for w in form.winfo_children() if isinstance(w,ttk.Entry)]
                entries[1].insert(0,'Dietrich appearance override')
                buttons = [w for w in glossary.winfo_children() if isinstance(w,ttk.Frame)][-1]
                next(w for w in buttons.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.previews[0x278][0].cget('text') == 'Dietrich appearance override'
                assert json.loads(app.glossary_path.read_text(encoding='utf8'))['AID_ディートリヒ'] == 'Dietrich appearance override'
                assert app.doc.changes == before
                glossary.destroy()
                app.custom_translations={}; app.rebuild_translator()
                app.notebook.select(1)
                field, class_entry = app.widgets[0x38]
                app.pick(field, class_entry)
                dialog = next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                children = dialog.winfo_children()
                search_entry = next(w for w in children if isinstance(w,ttk.Entry))
                app.setvar(search_entry.cget('textvariable'),'JID_猟兵')
                # Search the same option by its in-game English name as well.
                wanted_name=app.translator.resolve('JID_猟兵').text
                app.setvar(search_entry.cget('textvariable'),wanted_name)
                class_list = next(w for w in children if isinstance(w,ttk.Treeview))
                matches=class_list.get_children()
                assert matches and any(class_list.item(i,'values')[1]=='JID_猟兵' for i in matches)
                app.setvar(search_entry.cget('textvariable'),'JID_猟兵')
                assert len(class_list.get_children()) == 1
                class_list.selection_set(class_list.get_children()[0])
                next(w for w in children if isinstance(w,ttk.Button)).invoke()
                assert class_entry.get() == 'JID_猟兵'
                class_entry.delete(0,'end');class_entry.insert(0,original_class)
                app.notebook.select(2)
                app.update()
                screenshot = root_path/'preview.png'
                subprocess.run(['import', '-display', os.environ['DISPLAY'], '-window',
                                str(app.winfo_id()), str(screenshot)], check=True)
                # Check compact-window layout and capture the translated forms for review.
                app.geometry('1000x680'); app.update()
                boundary=app.winfo_rootx()+app.winfo_width()-15
                for offset,(field,widget) in app.widgets.items():
                    if 0x1ba<=offset<=0x262:
                        assert widget.winfo_rootx()+widget.winfo_width() <= boundary, ('clipped stat',hex(offset))
                app.geometry('1180x780'); app.update()
                preview_dir=Path(os.environ.get('FW_PREVIEW_DIR',temporary))
                preview_dir.mkdir(parents=True,exist_ok=True)
                for index,name in ((0,'character'),(3,'skills')):
                    app.notebook.select(index); app.update()
                    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',
                                    str(app.winfo_id()),str(preview_dir/(name+'.png'))],check=True)
                app.tree.selection_set(str(maj.index)); app.select()
                assert app.notebook.index('current') == 3
                app.tree.selection_set(str(diet.index)); app.select()
                field, widget = app.widgets[0x1c2]
                widget.delete(0,'end');widget.insert(0,'44')
                assert app.apply()
                app.tree.selection_set(str(maj.index)); app.select()
                field, widget = app.widgets[0x98]
                widget.delete('1.0','end');widget.insert('1.0','SID_冥府値\nSID_ディートリヒ本人')
                assert app.apply()
                app.save_project()
                project = json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert len(project['documents']['Person.bin']['changes']) == 2
                app.export()
                result=fw_editor.Person((temporary/'mod/romfs/GameData/Person.bin').read_bytes())
                assert result.original(result.by_pid[diet.pid],result.by_offset[0x1c2]) == 44
                assert len(result.original(result.by_pid[maj.pid],result.by_offset[0x98])) == 2
                app.reset()
                assert len(app.doc.changes) == 1
                app.load_project()
                assert len(app.doc.changes) == 2
                app.tree.selection_set(str(diet.index)); app.select()
                field, widget = app.widgets[0x1c2]
                widget.delete(0,'end');widget.insert(0,'9999999')
                assert not app.apply()
                assert errors and 'between' in errors[-1]
                print('PASS: actual GUI load/search/navigation; numeric and array edits; project save/load; mod export; reset; invalid-value feedback; screenshot.')
            except Exception as exc:
                failures.append(exc)
                import traceback; traceback.print_exc()
            finally:
                app.destroy()
        app.after(350,exercise)
        original_loop(app,*args,**kwargs)

    sys.argv = ['fw_editor.py', str(data)]
    with patch.object(tk.Tk,'mainloop',patched_loop), \
         patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')), \
         patch.object(messagebox,'showinfo'), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(message)), \
         patch.object(messagebox,'askyesno',return_value=True):
        fw_editor.main()
    if failures: raise failures[0]
