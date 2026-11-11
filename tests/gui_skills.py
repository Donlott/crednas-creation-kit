"""Actual SID editor, all new data types, file separation and live-usage navigation."""
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
                app.read_names(english);assert app.switch_module('Skills','SID_主人公用輸送隊')
                assert len(app.tree.get_children())==2854 and len(app.widgets)==157
                assert 'convoy' in app.heading.get().lower()
                app.copy_skill_button.invoke();assert app.clipboard_get()=='SID_主人公用輸送隊'
                app.search.set('convoy');app.update();assert app.tree.get_children()
                main=app.doc;record=app.current
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or field.kind in fw.NUMERIC_ARRAYS:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                write(0x15c,'0.7');write(0x14a,'-30');write(0x100,'[-32768, 77, 32767]');write(0x120,'[0, 255, 3]')
                write(0x88,'["SID_主人公用輸送隊"]\n[]')
                app.edit_conditions(*app.widgets[0x88]);modal=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                frames=[w for w in modal.winfo_children() if isinstance(w,ttk.Frame)];tools,area,bottom=frames
                raw=next(w for w in area.winfo_children() if isinstance(w,tk.Text));assert raw.get('1.0','end-1c')=='SID_主人公用輸送隊'
                next(w for w in bottom.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Use groups').invoke()
                # English SID picker on a flat data[] field, with live preview.
                field,widget=app.widgets[0x1f0];app.pick(field,widget)
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),'convoy')
                listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview));assert listing.get_children()
                listing.selection_set(listing.get_children()[0]);next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                app.update();app.after(180,app.quit);original_loop(app)
                assert 'convoy' in app.previews[0x1f0][0].get('1.0','end-1c').lower()
                assert app.apply() and not app.dirty_widgets()
                assert main.value(record,main.by_offset[0x15c])==fw.float32(0.7)
                assert main.value(record,main.by_offset[0x88])==[['SID_主人公用輸送隊'],[]]
                # Invalid new types block switching and preserve both source and edits.
                write(0x120,'[256]');assert not app.switch_module('Classes');write(0x120,'[0,255,3]')
                write(0x15c,'nan');assert not app.switch_module('Characters');write(0x15c,'0.7')
                write(0x100,'not JSON');assert not app.switch_module('AIDs');write(0x100,'[-32768,77,32767]')
                write(0x120,'[256]');app.skill_source.set('Skill_P0.bin');app.skill_source_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc is main and app.skill_source.get()=='Skill.bin'
                write(0x120,'[0,255,3]');assert app.apply()
                # Separate source files retain different edits even for duplicate SID labels.
                duplicate='SID_[e]突撃体勢[効果]'
                assert app.switch_module('Skills',duplicate,source_file='Skill_P0.bin')
                assert len(app.tree.get_children())==28 and 'also in Skill.bin' in app.details.get()
                write(0x111,'7');write(0x1f0,'SID_主人公用輸送隊');assert app.apply();side=app.doc
                assert app.switch_module('Skills','SID_天帝の剣効果',source_file='Skill_P1.bin')
                assert len(app.tree.get_children())==3;write(0x15c,'0.65');assert app.apply()
                # A new unsaved Person assignment appears without altering original-file evidence.
                assert app.switch_module('Characters','PID_ディートリヒ')
                character=app.current;person=app.doc
                field,widget=app.widgets[0x98];old=widget.get('1.0','end-1c');widget.delete('1.0','end');widget.insert('1.0',old+'\nSID_>予約')
                name_key=person.value(person.by_pid['PID_マジーデ'],person.by_offset[0x20])
                widget=app.widgets[0x20][1];widget.delete(0,'end');widget.insert(0,name_key)
                assert app.switch_module('Skills','SID_>予約',source_file='Skill.bin')
                uses=app.skill_usage_targets
                owner=next(i for i,u in enumerate(uses) if u.record=='PID_ディートリヒ' and u.module=='Characters' and '0x98' in u.field)
                assert app.skill_usage_tree.item(str(owner),'values')[1]==app.names[name_key]
                app.skill_usage_tree.selection_set(str(owner));app.skill_usage_open()
                assert app.active_module=='Characters' and app.current.pid=='PID_ディートリヒ'
                # Navigate from a skill to the precise LID row that references it.
                growth=app.documents['Learning tables'];row=growth.rows_by_table['LID_ディートリヒ'][0]
                sid=growth.value(row,growth.by_offset[0x28]);assert sid in main.by_pid
                app.switch_module('Skills',sid,source_file='Skill.bin')
                i=next(i for i,u in enumerate(app.skill_usage_targets) if u.table=='LID_ディートリヒ' and u.row==0)
                app.skill_usage_tree.selection_set(str(i));app.skill_usage_open()
                assert app.active_module=='Learning tables' and app.current.pid=='LID_ディートリヒ' and app.learning_row.index==0
                # A skill-to-skill link navigates to its actual file, including side records.
                app.switch_module('Skills','SID_主人公用輸送隊',source_file='Skill.bin')
                target=next(i for i,u in enumerate(app.skill_usage_targets) if u.module=='Skills' and u.source=='Skill_P0.bin' and u.record==duplicate)
                app.skill_usage_tree.selection_set(str(target));app.skill_usage_open()
                assert app.doc.filename=='Skill_P0.bin' and app.current.pid==duplicate
                app.switch_module('Skills','SID_主人公用輸送隊',source_file='Skill.bin')
                assert app.skill_index.static_uses and 'Item.bin' in {s for s,_,_ in app.skill_index.link_tables}
                app.geometry('1000x680');app.notebook.select(3);app.update()
                assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                for tab,name in ((3,'skills-stats'),(6,'skills-usage')):
                    app.notebook.select(tab);app.update()
                    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/(name+'.png'))],check=True)
                app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==len(app.documents)
                for kind in fw.SKILL_TABLES:
                    source=next(d for d in app.documents.values() if type(d) is kind)
                    result=kind((temporary/'mod/romfs/GameData'/kind.filename).read_bytes())
                    for (pid,offset),value in source.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                app.reset();assert not any(pid==record.pid for pid,_ in main.changes);assert side.changes
                app.load_project();assert main.changes
                app.switch_module('Skills',duplicate,source_file='Skill_P0.bin');app.save_project();assert app.open_last_project()
                assert app.active_module=='Skills' and app.doc.filename=='Skill_P0.bin' and app.doc.changes
                # Standalone side-file loading and Skill-only English folders work.
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Skill_P1.bin').write_bytes((base/'Skill_P1.bin').read_bytes())
                app.open_data(standalone/'Skill_P1.bin');assert app.active_module=='Skills' and app.doc.filename=='Skill_P1.bin'
                assert len(app.documents)==1 and len(app.tree.get_children())==3
                assert len(errors)==4,errors
                print('PASS: all 157 SID fields, float/list/group edits, live English picker/previews, input blocking, separate side files, live owner/LID navigation, shared exports, reset and last-project source restoration.')
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
