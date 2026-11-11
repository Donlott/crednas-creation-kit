"""Actual GLID navigation, English choices, mixed LID edits, export and reopening."""
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
from progression_ui import select_level

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('GLID progression','GLID_ディートリヒ')
                assert len(app.tree.get_children())==206 and len(app.progression_tree.get_children())==80
                assert app.heading.get()=='Dietrich' and app.doc is app.documents['Learning tables'].progression
                assert len(app.doc.rows_by_table['GLID_ディートリヒ'])==1
                app.search.set('Majide');app.update();assert len(app.tree.get_children())==1
                app.switch_module('GLID progression','GLID_マジーデ');assert len(app.doc.rows_by_table[app.current.pid])==9
                # Category row 1 is unverified and empty. Levels remain editable.
                app.progression_rows.current(1);app.progression_rows.event_generate('<<ComboboxSelected>>');app.update()
                assert app.learning_row.index==1 and app.doc.value(app.learning_row,app.doc.by_offset[0x20])==1
                assert app.progression_tree.item('1','values')[2]==''
                app.switch_module('GLID progression','GLID_ディートリヒ')
                def level(number):
                    app.progression_tree.selection_set(str(number));select_level(app);app.update()
                    assert app.progression_level==number
                def write(offset,value):
                    widget=app.widgets[offset][1];widget.delete(0,'end');widget.insert(0,value)
                level(20);offset=0x28+19*8
                field,widget=app.widgets[offset];app.pick(field,widget)
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry))
                app.setvar(entry.cget('textvariable'),'JID_闘士'.removeprefix('JID_'))
                listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                assert listing.get_children();listing.selection_set(listing.get_children()[0])
                chosen=listing.item(listing.selection()[0],'values');assert chosen[1]=='闘士'
                assert chosen[0] not in ('No translation yet','闘士')
                next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                app.update();app.after(180,app.quit);original_loop(app)
                assert app.previews[offset][0].cget('text')==app.translator.resolve('JID_闘士').text
                # Selecting another level applies this field without losing it.
                level(80);write(0x2a0,'テスト最終');assert app.apply()
                assert app.doc.value(app.doc.rows_by_table['GLID_ディートリヒ'][0],app.doc.by_offset[offset])=='闘士'
                actions={w.cget('text'):w for w in app.progression_tools.winfo_children() if isinstance(w,ttk.Button)}
                toggle=next(w for w in app.progression_rows.master.winfo_children() if isinstance(w,ttk.Checkbutton))
                toggle.invoke();app.update();assert len(app.progression_tree.get_children())<80 and app.progression_tree.exists('80')
                toggle.invoke();app.update();assert len(app.progression_tree.get_children())==80
                actions['Copy row'].invoke()
                app.switch_module('GLID progression','GLID_マジーデ')
                actions={w.cget('text'):w for w in app.progression_tools.winfo_children() if isinstance(w,ttk.Button)}
                actions['Paste row'].invoke();assert app.doc.value(app.learning_row,app.doc.by_offset[0x2a0])=='テスト最終'
                level(80);actions['Reset level'].invoke();assert app.doc.value(app.learning_row,app.doc.by_offset[0x2a0])==''
                level(20);actions['Clear level'].invoke();assert app.doc.value(app.learning_row,app.doc.by_offset[offset])==''
                # Invalid category blocks module navigation and preserves form edits.
                write(0x20,'999');assert not app.switch_module('Classes');assert app.active_module=='GLID progression'
                field,widget=app.widgets[offset];app.pick(field,widget)
                assert not any(isinstance(w,tk.Toplevel) for w in app.winfo_children())
                write(0x20,'invalid');app.pick(field,widget)
                assert not any(isinstance(w,tk.Toplevel) for w in app.winfo_children())
                write(0x20,'0');assert app.apply()
                assert app.switch_module('Learning tables','LID_ディートリヒ')
                learning=app.doc;widget=app.widgets[0x20][1];widget.delete(0,'end');widget.insert(0,'19');assert app.apply()
                assert app.switch_module('GLID progression','GLID_ディートリヒ')
                assert any(k[0].startswith('LID_') for k in app.doc.changes) and any(k[0].startswith('GLID_') for k in app.doc.changes)
                assert learning.changes is app.doc.changes
                # English item picker returns bare values and uses the category's namespace.
                app.switch_module('GLID progression','GLID_マジーデ');app.progression_rows.current(3)
                app.progression_rows.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc.value(app.learning_row,app.doc.by_offset[0x20])==4
                assert '青銅の斧' in app.suggestions(app.doc.by_offset[0x28])
                assert app.translate_value('青銅の斧').text==app.translator.resolve('IID_青銅の斧').text
                app.switch_module('GLID progression','GLID_ディートリヒ')
                app.geometry('1000x680');app.update()
                assert app.progression_form.winfo_rooty()+app.progression_form.winfo_height()<app.winfo_rooty()+app.winfo_height()-25
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'progression.png')],check=True)
                app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert set(project['documents'])=={d.filename for d in app.documents.values()}
                result=fw.Learning((temporary/'mod/romfs/GameData/Growth.bin').read_bytes())
                r=result.progression.rows_by_table['GLID_ディートリヒ'][0]
                assert result.progression.value(r,result.progression.by_offset[0x2a0])=='テスト最終'
                r=result.rows_by_table['LID_ディートリヒ'][0];assert result.value(r,result.by_offset[0x20])==19
                app.reset();assert not app.doc.table_changed('GLID_ディートリヒ')
                assert any(k[0].startswith('LID_') for k in app.doc.changes)
                app.load_project();assert app.doc.table_changed('GLID_ディートリヒ')
                app.notebook.select(1);app.update();users=app.progression_users_tree
                target=next(i for i in users.get_children() if users.item(i,'values')[2]=='PID_ディートリヒ');users.selection_set(target)
                tab=app.nametowidget(app.notebook.tabs()[1]);next(w for w in tab.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.active_module=='Characters' and app.current.pid=='PID_ディートリヒ'
                app.switch_module('Characters','PID_マジーデ')
                widget=app.widgets[0x128][1];widget.delete(0,'end');widget.insert(0,'GLID_ディートリヒ')
                app.switch_module('GLID progression','GLID_ディートリヒ')
                assert any(app.progression_users_tree.item(i,'values')[2]=='PID_マジーデ' for i in app.progression_users_tree.get_children())
                app.save_project();assert app.open_last_project()
                assert app.active_module=='GLID progression' and app.doc.changes
                # No Person/Job data is required to use the standalone GLID module.
                standalone=temporary/'growth-only';standalone.mkdir();(standalone/'Growth.bin').write_bytes((base/'Growth.bin').read_bytes())
                app.open_data(standalone);assert app.switch_module('GLID progression') and not app.progression_users_tree.get_children()
                assert len(errors)==3 and '255' in errors[0] and '255' in errors[1] and 'whole number' in errors[2],errors
                print('PASS: GLID names/search, category/level navigation, live English/bare-name choices, 80+ edits, row copy/paste, clear/reset, validation, mixed LID save/export, usage navigation and project reopening.')
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
