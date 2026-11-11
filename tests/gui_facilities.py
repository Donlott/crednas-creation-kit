"""Facility/reward source controls, grouped leaves, links and full export in Tk."""
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
source_hashes={p.name:hashlib.sha256(p.read_bytes()).digest() for p in [*(base/k.filename for k in fw.FACILITY_TABLES),base/'FacilityScene.bin']}
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                assert app.switch_module('Facilities & Rewards');owner=app.doc.owner
                assert app.doc.key=='cooking' and len(app.tree.get_children())==12 and len(app.widgets)==8
                namekey=app.doc.value(app.current,app.doc.by_offset[0x20]);food_name=app.names[namekey];food_native=app.doc.names[app.current.pid]
                assert app.previews[0x20][0].cget('text')==food_name
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
                write(0x34,'900');assert app.apply()
                # Every primary section renders all of its stored fields.
                for key,view in owner.views.items():
                    assert app.switch_module('Facilities & Rewards',source_file='Facility.bin',section=key)
                    assert len(app.widgets)==len(view.fields) and len(app.tree.get_children())==len(view.records)
                app.switch_module('Facilities & Rewards',section='cooking');app.facility_links_refresh()
                i=next(i for i,x in enumerate(app.facility_links) if x[0]=='Profiles & Affiliations')
                app.facility_links_tree.selection_set(str(i));target=app.facility_links[i][2];app.facility_links_open()
                assert app.active_module=='Profiles & Affiliations' and app.current.pid==target
                assert app.translator.resolve(food_native).text==food_name
                # Learned skills / weight vectors are paired, and the SID usage browser navigates back.
                app.switch_module('Facilities & Rewards',source_file='Facility.bin',section='baths');bath=app.current
                sid=app.doc.value(bath,app.doc.by_offset[0x48])[0];write(0x48,sid);write(0x58,'[7]');assert app.apply()
                write(0x58,'[]');assert not app.switch_module('AIDs');write(0x58,'[7]');assert app.apply()
                app.switch_module('Skills',sid);app.skill_usage_refresh()
                i=next(i for i,x in enumerate(app.skill_usage_targets) if x.module=='Facilities & Rewards' and x.record==bath.pid)
                app.skill_usage_tree.selection_set(str(i));app.skill_usage_open();assert app.doc.key=='baths' and app.current.pid==bath.pid
                # Weapon/class references are current and open their correct editors.
                app.switch_module('Facilities & Rewards',source_file='Facility.bin',section='training');training=app.current
                choose(0x68,'IID_青銅の剣','IID_青銅の剣');assert app.apply();app.facility_links_refresh()
                i=next(i for i,x in enumerate(app.facility_links) if x[0]=='Classes');app.facility_links_tree.selection_set(str(i));jid=app.facility_links[i][2];app.facility_links_open()
                assert app.active_module=='Classes' and app.current.pid==jid
                app.switch_module('Items','IID_青銅の剣');app.item_usage_refresh()
                i=next(i for i,x in enumerate(app.item_usage_targets) if x.module=='Facilities & Rewards' and x.record==training.pid)
                app.item_usage_tree.selection_set(str(i));app.item_usage_open();assert app.doc.key=='training'
                app.switch_module('Facilities & Rewards',section='theater');write(0x38,'0.625');assert app.apply()
                write(0x38,'nan');app.facility_source.set('Reward.bin');app.facility_source_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc.filename=='Facility.bin' and app.facility_source.get()=='Facility.bin';write(0x38,'0.625');assert app.apply()
                # Grouped headers stay fixed while the Group filter selects native leaf rows.
                app.switch_module('Facilities & Rewards',section='hours');assert len(app.tree.get_children())==21
                assert "Anna's shop" in app.facility_group_choice.cget('values')[16]
                app.facility_group_choice.current(16);app.facility_group_choice.event_generate('<<ComboboxSelected>>');app.update();assert len(app.tree.get_children())==2
                r=app.doc.records[int(app.tree.get_children()[1])];app.tree.selection_set(str(r.index));app.select();assert app.doc.locations[r.pid]==(15,1)
                write(0x38,'256');app.facility_group_choice.current(1);app.facility_group_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.facility_group_index==15 and app.facility_group_choice.current()==16;write(0x38,'3');write(0x28,'hours_TEST');assert app.apply()
                app.switch_module('Facilities & Rewards',section='statuses');app.facility_group_choice.current(3);app.facility_group_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert len(app.tree.get_children())==7;write(0x20,'Status_TEST');assert app.apply();app.reset()
                # These two references store bare names; the chooser retains the native format.
                app.switch_module('Facilities & Rewards',section='exspots');choose(0x30,'力の効能','力の効能');assert app.apply()
                assert app.doc.value(app.current,app.doc.by_offset[0x30])=='力の効能'
                app.switch_module('Facilities & Rewards',section='questions');choose(0x40,'うなずく','うなずく');assert app.apply();app.facility_links_refresh()
                assert any(x[2].startswith('answers:') for x in app.facility_links)
                # Main reward sections and source-isolated side notices are all editable.
                app.switch_module('Facilities & Rewards',source_file='Reward.bin');reward=app.doc.owner;assert len(reward.views)==4
                for key,view in reward.views.items():
                    app.switch_module('Facilities & Rewards',source_file='Reward.bin',section=key);assert len(app.widgets)==len(view.fields)
                app.switch_module('Facilities & Rewards',section='achievements');write(0x3c,'-2147483648');assert app.apply()
                app.switch_module('Facilities & Rewards',section='causality');write(0x3a,'255');assert app.apply()
                app.switch_module('Facilities & Rewards',section='renown');write(0x22,'999');write(0x68,'IID_青銅の剣');assert app.apply()
                for source,count in [('Reward_P0.bin',3),('Reward_P1.bin',4)]:
                    app.switch_module('Facilities & Rewards',source_file=source,section='notices')
                    assert len(app.facility_section_choice.cget('values'))==1 and len(app.tree.get_children())==count
                    write(0x20,'65535');write(0xa8,'IID_青銅の剣');assert app.apply()
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==len(app.documents)
                files={p.name for p in (temporary/'mod/romfs/GameData').glob('*.bin')};assert len(files)==33 and 'FacilityScene.bin' not in files
                for kind in fw.FACILITY_TABLES:
                    document=next(d for d in app.documents.values() if type(d) is kind);result=kind((temporary/'mod/romfs/GameData'/kind.filename).read_bytes())
                    for (pid,offset),value in document.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                app.reset();assert not any(pid==app.current.pid for pid,_ in app.doc.changes)
                app.load_project();assert app.doc.value(app.current,app.doc.by_offset[0x20])==65535
                app.switch_module('Facilities & Rewards',source_file='Reward.bin',section='renown');app.save_project();assert app.open_last_project()
                assert app.doc.filename=='Reward.bin' and app.doc.key=='renown' and app.active_module=='Facilities & Rewards'
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.switch_module('Facilities & Rewards',source_file='Facility.bin',section='cooking');app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'facilities-cooking.png')],check=True)
                app.switch_module('Facilities & Rewards',source_file='Reward.bin',section='renown');app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'rewards-renown.png')],check=True)
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Reward_P1.bin').write_bytes((base/'Reward_P1.bin').read_bytes())
                app.open_data(standalone/'Reward_P1.bin');assert app.active_module=='Facilities & Rewards' and len(app.documents)==1 and app.doc.filename=='Reward_P1.bin'
                for name,digest in source_hashes.items():assert hashlib.sha256((base/name).read_bytes()).digest()==digest
                assert len(errors)==3,errors
                assert not callbacks,callbacks
                print('PASS: 20 facility sections, four reward sections and side files; readable names, paired weights, native group filtering, raw float/bounds validation, direct class/profile links, SID/IID-to-facility navigation, combined export, reset/reload, saved source/section and standalone side loading.')
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
