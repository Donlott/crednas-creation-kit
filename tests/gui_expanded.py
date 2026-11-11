"""Actual shared progression/difficulty UI, source guards and exact links."""
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
fingerprints={n:hashlib.sha256((base/n).read_bytes()).digest() for n in ['Person.bin','Growth.bin','Growth_P0.bin']}
MODULE='Progression & Difficulty';dit='PID_ディートリヒ';convoy='SID_主人公用輸送隊';pipe='IID_試作品１号|||'
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or field.kind in fw.NUMERIC_ARRAYS:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(text):next(w for w in app.expanded_tools.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==text).invoke()
                def switch(source,section,record=None):return app.switch_module(MODULE,record,source_file=source,section=section)
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                app.switch_module('Characters',dit);write(0x1c2,'101');write(0x138,'DID_アトラスベア');assert app.apply();person=app.doc
                did=person.value(person.by_pid[dit],person.by_offset[0x138])
                app.switch_module('Learning tables','LID_ディートリヒ');write(0x20,'19');assert app.apply();growth=app.doc
                app.switch_module('GLID progression','GLID_ディートリヒ');write(0x28,'SyntheticClass');assert app.apply()
                assert switch('Growth.bin','exp_curve') and app.doc.owner is growth
                assert len(app.tree.get_children())==4 and len(app.expanded_tree.get_children())==99 and len(app.widgets)==2
                assert set(app.expanded_source_choice.cget('values'))=={'Growth.bin','Person.bin','Growth_P0.bin'}
                curve=app.doc;first=app.learning_row;write(0x22,'2345');assert app.apply();action('Copy entry')
                write(0x22,'65536');app.expanded_source.set('Person.bin')
                assert not switch('Person.bin','difficulty') and app.expanded_source.get()=='Growth.bin'
                write(0x22,'2345');assert app.apply()
                from expanded_ui import show_entry
                show_entry(app,curve.records[1]);action('Paste values');assert curve.value(app.learning_row,curve.by_offset[0x22])==2345
                action('Reset entry');assert curve.value(app.learning_row,curve.by_offset[0x22])==curve.original(app.learning_row,curve.by_offset[0x22])
                # All ten main Growth sections expose every field.
                for key,view in growth.views.items():
                    assert switch('Growth.bin',key);assert len(app.widgets)==len(view.fields)
                switch('Growth.bin','auto_items');action('Paste values');assert 'same progression/difficulty section' in errors[-1]
                # Experience calculations link to their exact referenced curve/modifier.
                switch('Growth.bin','exp_calculation');app.expanded_links_refresh()
                from expanded_ui import collection_name
                normal=next(r for r in app.doc.collections if app.doc.names[r.pid]=='通常攻撃_レベル差補正')
                assert 'Normal attack' in collection_name(app,normal)
                i=next(i for i,t in enumerate(app.expanded_links) if t[3]=='Referenced experience table')
                app.expanded_links_tree.selection_set(str(i));app.expanded_links_open();assert app.doc.key in ('exp_curve','exp_modifiers')
                # Legion LIDs stay distinct from learning LIDs.
                switch('Growth.bin','auto_legions');from expanded_ui import suggestions
                assert 'LID_ダグザ戦士隊' in suggestions(app,app.doc.by_offset[0x20]) and 'LID_ディートリヒ' not in suggestions(app,app.doc.by_offset[0x20])
                choose(0x20,'Trap Springers','LID_ダグザ戦士隊');assert app.apply();app.expanded_links_refresh()
                i=next(i for i,t in enumerate(app.expanded_links) if t[0]=='Legion' and t[2]=='LID_ダグザ戦士隊')
                app.expanded_links_tree.selection_set(str(i));app.expanded_links_open();assert app.active_module=='Legion'
                switch('Growth_P0.bin','part2_items');side=app.doc.owner;side_row=app.learning_row
                choose(0x38,pipe,pipe);write(0x28,'[1,255]');write(0x48,'[2]');assert app.apply()
                assert len(app.doc.value(side_row,app.doc.by_offset[0x38]))!=len(app.doc.value(side_row,app.doc.by_offset[0x48]))
                app.switch_module('Items',pipe,source_file='Item_P1.bin');app.item_usage_refresh()
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module==MODULE and u.source=='Growth_P0.bin' and u.record==side_row.pid)
                app.item_usage_tree.selection_set(str(i));app.item_usage_open();assert app.doc.filename=='Growth_P0.bin' and app.learning_row.pid==side_row.pid
                # Difficulty block at0x30 is an item list, independent of the primary serial lock.
                assert switch('Person.bin','difficulty',did);diff=app.doc;diff_row=app.learning_row
                assert len(app.widgets)==9 and len(app.expanded_form.tabs())==3
                assert app.widgets[0x30][1].cget('state')=='normal'
                write(0x20,convoy);write(0x30,pipe);write(0x40,json.dumps([convoy],ensure_ascii=False)+'\n[]');assert app.apply()
                # The nested-skill dialog describes stored rows, not boolean conditions.
                field,widget=app.widgets[0x40];app.edit_conditions(field,widget,'Stored latent-skill rows; execution order is unverified.')
                dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                assert any(isinstance(w,ttk.Label) and 'latent-skill rows' in w.cget('text') for w in dialog.winfo_children())
                dialog.destroy();assert app.apply();app.expanded_links_refresh()
                i=next(i for i,t in enumerate(app.expanded_links) if t[0]=='Characters' and t[2]==dit)
                app.expanded_links_tree.selection_set(str(i));app.expanded_links_open();assert app.current.pid==dit and app.doc.value(app.current,app.doc.by_offset[0x1c2])==101
                app.switch_module('Skills',convoy);app.skill_usage_refresh()
                i=next(i for i,u in enumerate(app.skill_usage_targets) if u.module==MODULE and u.source=='Person.bin' and u.record==diff_row.pid)
                app.skill_usage_tree.selection_set(str(i));app.skill_usage_open();assert app.doc.key=='difficulty' and app.learning_row.pid==diff_row.pid
                # The second Person section exposes both fields without changing primary identities.
                switch('Person.bin','auto_gear');assert len(app.widgets)==2
                switch('Person.bin','difficulty',did);app.save_project();app.export()
                project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==204
                assert project['documents']['Person.bin']['format']=='fw-character-edits-v2'
                assert project['documents']['Growth.bin']['format']=='fw-growth-edits-v2'
                assert project['documents']['Growth_P0.bin']['format']=='fw-expanded-side-edits-v1'
                assert len(list((temporary/'mod/romfs/GameData').rglob('*.bin')))==204
                for owner in (person,growth,side):
                    result=owner.reparse((temporary/'mod/romfs/GameData'/owner.filename).read_bytes())
                    for key,value in owner.changes.items():assert result.original(*result.edit_target(*key))==value
                app.reset();assert any(key[0]==dit for key in person.changes)
                app.load_project();assert any(key[0]==diff_row.pid for key in person.changes)
                app.save_project();assert app.open_last_project() and app.active_module==MODULE and app.doc.key=='difficulty' and app.doc.filename=='Person.bin'
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');switch('Growth.bin','exp_curve');app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'expanded-experience.png')],check=True)
                switch('Person.bin','difficulty','DID_アトラスベア');app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'expanded-difficulty.png')],check=True)
                standalone=temporary/'side';standalone.mkdir();(standalone/'Growth_P0.bin').write_bytes((base/'Growth_P0.bin').read_bytes())
                assert app.open_data(standalone/'Growth_P0.bin') and len(app.documents)==1 and app.active_module==MODULE
                sys.path.insert(0,str(Path(__file__).resolve().parent));from fixture import expanded_fixture
                empty=temporary/'empty';empty.mkdir();(empty/'Growth.bin').write_bytes(expanded_fixture('Growth.bin'))
                assert app.open_data(empty/'Growth.bin');assert switch('Growth.bin','exp_curve','exp_curve:1')
                assert app.learning_row is None and not app.widgets and not app.expanded_tree.get_children()
                for name,digest in fingerprints.items():assert hashlib.sha256((base/name).read_bytes()).digest()==digest
                assert not callbacks,callbacks
                print('PASS: 13 expanded views, all fields, shared LID/GLID/character edits, unlocked difficulty barriers, nested skills, namespace-aware links, independent supplies, exact usage navigation, 204-file exports, v1/v2 formats, source preservation and remembered/standalone/empty data.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
