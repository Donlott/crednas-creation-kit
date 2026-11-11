"""Exercise class editing and module transitions using the actual Tk widgets."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw

data=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        def exercise():
            try:
                app.read_names(english)
                assert app.switch_module('Classes')
                assert len(app.tree.get_children())==137
                assert len(app.widgets)==134
                assert app.heading.get()=='Gladiator'
                # Direct-pointer class links use English-searchable choices.
                field,widget=app.widgets[0x48];app.pick(field,widget)
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry))
                app.setvar(entry.cget('textvariable'),'Myrmidon')
                choices=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                found=next(i for i in choices.get_children() if choices.item(i,'values')[1]=='JID_剣士')
                choices.selection_set(found);next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert widget.get()=='JID_剣士'
                # Movement type is editable and must not inherit the character serial lock.
                app.widgets[0x30][1].delete(0,'end');app.widgets[0x30][1].insert(0,'2')
                app.widgets[0x120][1].delete(0,'end');app.widgets[0x120][1].insert(0,'38')
                conditions=app.widgets[0x1b8][1]
                conditions.delete('1.0','end');conditions.insert('1.0','["共有_兵種解放_ソードマスター", "3部"]\n[]')
                # Edit nested groups through the dedicated UI without changing their structure.
                app.edit_conditions(app.doc.by_offset[0x1b8],conditions)
                modal=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                frames=[w for w in modal.winfo_children() if isinstance(w,ttk.Frame)]
                tools,area,bottom=frames
                raw=next(w for w in area.winfo_children() if isinstance(w,tk.Text))
                assert raw.get('1.0','end-1c')=='共有_兵種解放_ソードマスター\n3部'
                combo=next(w for w in tools.winfo_children() if isinstance(w,ttk.Combobox))
                combo.current(1);combo.event_generate('<<ComboboxSelected>>');app.update()
                assert raw.get('1.0','end-1c')==''
                buttons=[w for w in tools.winfo_children() if isinstance(w,ttk.Button)]
                buttons[0].invoke();raw.insert('1.0','temporary group');buttons[1].invoke()
                next(w for w in bottom.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Use groups').invoke()
                skills=app.widgets[0x90][1];skills.delete('1.0','end');skills.insert('1.0','SID_主人公用輸送隊')
                app.update();app.after(180,app.quit);original_loop(app)
                assert json.loads(app.previews[0x1b8][0].get('1.0','end-1c').splitlines()[0])[1]=='Part 3'
                assert app.apply()
                assert len(app.doc.changes)==5
                app.notebook.select(1);app.update()
                # At the minimum supported size, all stat input columns remain inside the window.
                app.geometry('1000x680');app.update()
                boundary=app.winfo_rootx()+app.winfo_width()-15
                for off,(field,widget) in app.widgets.items():
                    if 0x120<=off<=0x19a or 0x1a4<=off<=0x1b0 or 0x219<=off<=0x223:
                        assert widget.winfo_rootx()+widget.winfo_width()<=boundary,('clipped class stat',hex(off))
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                for index,name in ((0,'class-overview'),(1,'class-stats'),(3,'class-promotion')):
                    app.notebook.select(index);app.update()
                    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/(name+'.png'))],check=True)
                # Nested text is strictly JSON; invalid input must not apply or change modules.
                old=conditions.get('1.0','end-1c');conditions.delete('1.0','end');conditions.insert('1.0','not JSON')
                assert not app.switch_module('Characters')
                assert app.active_module=='Classes'
                conditions.delete('1.0','end');conditions.insert('1.0',old)
                assert app.switch_module('Characters','PID_ディートリヒ')
                app.widgets[0x1c2][1].delete(0,'end');app.widgets[0x1c2][1].insert(0,'41')
                assert app.switch_module('Classes','JID_闘士')
                assert app.notebook.index('current')==3
                assert app.widgets[0x48][1].get()=='JID_剣士'
                assert app.widgets[0x120][1].get()=='38'
                assert app.documents['Characters'].changes
                app.save_project();saved=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert set(saved['documents'])=={d.filename for d in app.documents.values()}
                app.export()
                p=fw.Person((temporary/'mod/romfs/GameData/Person.bin').read_bytes())
                j=fw.Job((temporary/'mod/romfs/GameData/Job.bin').read_bytes())
                assert p.original(p.by_pid['PID_ディートリヒ'],p.by_offset[0x1c2])==41
                assert j.original(j.by_pid['JID_闘士'],j.by_offset[0x48])=='JID_剣士'
                assert j.original(j.by_pid['JID_闘士'],j.by_offset[0x1b8])==[['共有_兵種解放_ソードマスター','3部'],[]]
                app.reset();assert not app.doc.changes;assert app.documents['Characters'].changes
                app.load_project();assert len(app.doc.changes)==5
                # Reverse class references and navigation use the current in-memory Person table.
                app.notebook.select(5);app.update();usage=app.class_usage_tree
                first=usage.get_children()[0];pid=usage.item(first,'values')[2]
                usage.selection_set(first)
                used_body=usage.master.master
                next(w for w in used_body.winfo_children() if isinstance(w,ttk.Button)).invoke();app.update()
                assert app.active_module=='Characters' and app.current.pid==pid
                # A legacy character-only project remains loadable and replaces the workspace.
                (temporary/'project.json').write_text(json.dumps(app.documents['Characters'].project()))
                app.load_project();assert not app.documents['Classes'].changes
                # An isolated Job.bin can be opened without requiring a character table.
                isolated=temporary/'class-only';isolated.mkdir();(isolated/'Job.bin').write_bytes((data/'Job.bin').read_bytes())
                app.open_data(isolated)
                assert set(app.documents)=={'Classes'} and app.active_module=='Classes'
                assert len(app.widgets)==134
                app.open_data(data/'Job.bin')
                assert app.active_module=='Classes' and len(app.documents)==204
                print('PASS: class GUI, all 134 fields, direct links, nested conditions, translations, minimum layout, project migration, module retention, combined export, reset and reverse-use navigation.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    sys.argv=['fw_editor.py',str(data)]
    with patch.object(tk.Tk,'mainloop',loop), \
         patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')), \
         patch.object(messagebox,'showinfo'), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(message)), \
         patch.object(messagebox,'askyesno',return_value=True):
        fw.main()
    if failures:raise failures[0]
