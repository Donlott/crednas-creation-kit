"""Actual seven-section support/recruitment GUI and directed-cell editing."""
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
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert app.switch_module('Supports & Recruitment')
                owner=app.documents['Supports & Recruitment'];matrix=owner.views['matrix']
                dietrich=next(r for r in matrix.records if matrix.names[r.pid]=='RID_ディートリヒ')
                majide=next(r for r in matrix.records if matrix.names[r.pid]=='RID_マジーデ')
                assert len(app.tree.get_children())==73
                app.search.set('Dietrich');app.update();assert len(app.tree.get_children())==1
                app.tree.selection_set(str(dietrich.index));app.select();app.update()
                app.support_matrix_tree.selection_set(str(majide.index));app.update()
                assert app.support_peer.pid==majide.pid
                reverse=matrix.value(majide,matrix.by_offset[0x20])[dietrich.index]
                app.support_cell.delete(0,'end');app.support_cell.insert(0,'2')
                assert app.dirty_widgets() and app.apply()
                assert matrix.value(dietrich,matrix.by_offset[0x20])[majide.index]==2
                assert matrix.value(majide,matrix.by_offset[0x20])[dietrich.index]==reverse
                app.support_cell.delete(0,'end');app.support_cell.insert(0,'999')
                assert not app.switch_module('Supports & Recruitment',section='scout') and app.doc.key=='matrix'
                assert app.support_section_choice.get()=='Compatibility'
                app.support_cell.delete(0,'end');app.support_cell.insert(0,'invalid');assert not app.switch_module('Characters')
                app.support_cell.delete(0,'end');app.support_cell.insert(0,'2');assert app.apply()
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or field.kind in fw.NUMERIC_ARRAYS:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.switch_module('Supports & Recruitment','special:0');assert len(app.widgets)==12
                choose(0x20,'Majide','PID_マジーデ');write(0x40,'-25');write(0x52,'2');assert app.apply()
                assert app.doc.value(app.current,app.doc.by_offset[0x20])=='PID_マジーデ'
                assert app.switch_module('Supports & Recruitment','talks:0');assert len(app.widgets)==24
                native=app.doc.names[app.current.pid]
                write(0x40,'4');write(0x41,'1');write(0x43,'3');write(0x48,'PID_ディートリヒ');write(0x58,'test_flag\n2部');assert app.apply()
                assert app.doc.names[app.current.pid]==native
                assert app.switch_module('Supports & Recruitment','scout:1');assert len(app.widgets)==14
                assert app.doc.names[app.current.pid]=='' and app.doc.anchors[app.current.pid]=='PID_ティアラ'
                person=app.documents['Characters'];key=person.value(person.by_pid['PID_ティアラ'],person.by_offset[0x20]);assert app.names[key] in app.heading.get()
                write(0x21,'0');write(0x22,'1');write(0x28,'required_flag');write(0x60,'3')
                pipe='IID_試作品１号|||';choose(0x50,pipe,pipe)
                app.update();app.after(180,app.quit);original_loop(app)
                assert app.previews[0x50][0].cget('text')==app.translator.resolve(pipe).text
                assert app.apply()
                # Item usage links to this exact unnamed scouting row.
                assert app.switch_module('Items',pipe,source_file='Item_P1.bin')
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Supports & Recruitment' and u.record=='scout:1')
                app.item_usage_tree.selection_set(str(i));app.item_usage_open()
                assert app.active_module=='Supports & Recruitment' and app.doc.key=='scout' and app.current.index==1
                assert app.widgets[0x21][1].get()=='0'
                assert app.switch_module('Supports & Recruitment','assist:0');assert len(app.widgets)==1
                write(0x20,'[0,10,20,30,40]');assert app.apply()
                write(0x20,'[1,2]');assert not app.switch_module('Items');write(0x20,'[0,10,20,30,40]');assert app.apply()
                assert app.switch_module('Supports & Recruitment','voices:0');assert len(app.widgets)==5
                write(0x40,'test_voice_label');write(0x48,'voice_switch_flag');assert app.apply()
                assert app.switch_module('Supports & Recruitment','drinks:0');assert len(app.widgets)==1
                write(0x20,'IID_傷薬');assert app.apply()
                # Matrix connected-character owners use current Person support references.
                app.switch_module('Supports & Recruitment',dietrich.pid)
                app.notebook.select(1);app.update()
                tree=app.support_connected_tree;i=next(i for i in tree.get_children() if tree.item(i,'values')[2]=='PID_ディートリヒ')
                tree.selection_set(i);app.support_connected_open()
                assert app.active_module=='Characters' and app.current.pid=='PID_ディートリヒ'
                # Save/export from a different module still includes all seven edited sections.
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert len(project['documents'])==len(app.documents)
                result=fw.Reliance((temporary/'mod/romfs/GameData/Reliance.bin').read_bytes())
                for (pid,offset),value in owner.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                app.switch_module('Supports & Recruitment','scout:1');app.reset()
                assert not any(pid=='scout:1' for pid,_ in owner.changes) and any(pid.startswith('matrix:') for pid,_ in owner.changes)
                app.load_project();assert any(pid=='scout:1' for pid,_ in owner.changes)
                app.switch_module('Supports & Recruitment','scout:1');app.save_project();assert app.open_last_project()
                assert app.active_module=='Supports & Recruitment' and app.doc.key=='scout' and app.doc.changes
                app.geometry('1000x680');app.update()
                assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.switch_module('Supports & Recruitment','scout:1');app.notebook.select(0);app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'supports-scouting.png')],check=True)
                app.switch_module('Supports & Recruitment',dietrich.pid);app.notebook.select(0)
                app.support_matrix_tree.selection_set(str(majide.index));app.update();app.support_matrix_tree.see(str(majide.index));app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'supports-matrix.png')],check=True)
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Reliance.bin').write_bytes((base/'Reliance.bin').read_bytes())
                app.open_data(standalone/'Reliance.bin');assert set(app.documents)=={'Supports & Recruitment'}
                assert app.active_module=='Supports & Recruitment' and app.doc.owner.filename=='Reliance.bin'
                assert len(errors)==3,errors
                assert not callbacks,callbacks
                print('PASS: seven Reliance sections, directed matrix cells, fixed vectors, English PID/IID choosers, unlabelled scout rows, exact item-to-scout navigation, connected owners, combined export/reset, source paths and saved section restoration.')
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
