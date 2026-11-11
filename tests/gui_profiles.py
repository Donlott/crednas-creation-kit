"""Actual profile/affiliation editing, readable previews, usages and project restore."""
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
source_hash=hashlib.sha256((base/'Profile.bin').read_bytes()).digest()
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                assert app.names['MID_Roster_Position_Dit_001']=='Foreign Swordsman' and app.names['MID_Clan_Kai']=='Ribeira Winds'
                assert app.switch_module('Profiles & Affiliations');owner=app.doc.owner;v=app.doc
                dit=next(r for r in v.records if v.names[r.pid]=='PRF_ディートリヒ')
                maj=next(r for r in v.records if v.names[r.pid]=='PRF_マジーデ')
                assert app.switch_module('Profiles & Affiliations',dit.pid)
                assert len(app.widgets)==46 and len(app.tree.get_children())==313 and len(app.notebook.tabs())==4
                assert app.previews[0x50][0].cget('text')=='Foreign Swordsman'
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
                write(0x44,'200');write(0xa8,'255');write(0xc0,'[0, 2, 255]')
                write(0x68,'[-1, 1449]');write(0x78,'MID_Roster_Career_Dit_001\nMID_Roster_Career_Dit_002')
                write(0xf0,'IID_青銅の剣');choose(0x30,'Majide','PRF_マジーデ');assert app.apply()
                assert v.value(dit,v.by_offset[0x44])==200 and v.value(dit,v.by_offset[0x68])==[-1,1449]
                # A paired-history error blocks section navigation and restores the selector.
                write(0x68,'[1449]');app.profile_section_choice.current(1);app.profile_section_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc.key=='profiles' and app.profile_section_choice.get()=='Profiles';write(0x68,'[-1, 1449]')
                write(0x40,'65536');assert not app.switch_module('AIDs');write(0x40,'1426');assert app.apply()
                app.profile_links_refresh();target=next(i for i,x in enumerate(app.profile_links) if x.record==maj.pid and x.relation=='Outgoing profile group')
                app.profile_links_tree.selection_set(str(target));app.profile_links_open();assert app.current.pid==maj.pid
                # Live Person references move between profiles without editing the native profile ID.
                app.switch_module('Characters','PID_ディートリヒ');write(0x118,'PRF_マジーデ');app.switch_module('Profiles & Affiliations',maj.pid)
                assert any(x.raw=='PID_ディートリヒ' for x in app.profile_links)
                app.switch_module('Profiles & Affiliations',dit.pid);assert not any(x.raw=='PID_ディートリヒ' and x.module=='Characters' for x in app.profile_links)
                app.switch_module('Characters','PID_ディートリヒ');write(0x118,'PRF_ディートリヒ');assert app.apply()
                # Clan text previews and nested transition conditions remain separate from native slots.
                app.switch_module('Profiles & Affiliations',section='affiliations');a=app.doc
                row=next(r for r in a.records if a.names[r.pid]=='BID_ディートリヒ開始時');app.switch_module('Profiles & Affiliations',row.pid)
                assert len(app.widgets)==5 and len(app.tree.get_children())==97
                choose(0x20,'Ribeira','MID_Clan_Kai');write(0x28,'3');write(0x38,'["route_TEST"]\n[]\n["!event_TEST"]');choose(0x48,'Default','BID_デフォルト')
                assert app.previews[0x20][0].cget('text')=='Ribeira Winds' and app.apply()
                write(0x28,'256');assert not app.switch_module('Profiles & Affiliations',section='order');write(0x28,'3')
                app.profile_links_refresh();incoming=next(i for i,x in enumerate(app.profile_links) if x.module=='Characters')
                app.profile_links_tree.selection_set(str(incoming));pid=app.profile_links[incoming].record;app.profile_links_open();assert app.active_module=='Characters' and app.current.pid==pid
                # All remaining sections edit exact native field types.
                app.switch_module('Profiles & Affiliations',section='expressions');assert len(app.widgets)==6 and len(app.tree.get_children())==325
                write(0x20,'Expression_TEST');write(0x3c,'4294967295');assert app.apply()
                app.switch_module('Profiles & Affiliations',section='limits');assert len(app.widgets)==1;write(0x20,'test_restriction');assert app.apply()
                app.switch_module('Profiles & Affiliations',section='order');assert len(app.widgets)==9 and len(app.tree.get_children())==179
                write(0x22,'-32768');assert app.apply()
                # Gift usage opens the exact profile, rather than treating the multi-layout owner as a flat table.
                app.switch_module('Items','IID_青銅の剣');app.item_usage_refresh()
                i=next(i for i,x in enumerate(app.item_usage_targets) if x.module=='Profiles & Affiliations' and x.record==dit.pid)
                app.item_usage_tree.selection_set(str(i));app.item_usage_open();assert app.active_module=='Profiles & Affiliations' and app.current.pid==dit.pid
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==len(app.documents)
                result=fw.Profile((temporary/'mod/romfs/GameData/Profile.bin').read_bytes())
                for (rid,offset),value in owner.changes.items():assert result.original(*result.edit_target(rid,offset))==value
                assert len(list((temporary/'mod/romfs/GameData').glob('*.bin')))==33
                # Reset row keeps all other sections; project reload and recent section restore are stable.
                app.reset();assert v.value(dit,v.by_offset[0x44])==192 and owner.changes
                app.load_project();assert v.value(dit,v.by_offset[0x44])==200
                app.switch_module('Profiles & Affiliations',row.pid);app.save_project();assert app.open_last_project()
                assert app.active_module=='Profiles & Affiliations' and app.doc.key=='affiliations'
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.switch_module('Profiles & Affiliations',dit.pid);app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'profiles-bio.png')],check=True)
                app.switch_module('Profiles & Affiliations',row.pid);app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'profiles-affiliation.png')],check=True)
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'Profile.bin').write_bytes((base/'Profile.bin').read_bytes())
                app.open_data(standalone/'Profile.bin');assert app.active_module=='Profiles & Affiliations' and len(app.documents)==1
                assert hashlib.sha256((base/'Profile.bin').read_bytes()).digest()==source_hash
                assert len(errors)==3,errors
                assert not callbacks,callbacks
                print('PASS: five Profile sections, 46 profile fields, English biography/clan keys, paired history validation, live character/affiliation links, gift-to-profile navigation, combined export, reset, source preservation, saved section and standalone loading.')
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
