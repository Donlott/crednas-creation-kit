"""Actual appearance editing, copy/paste boundaries and live AID browser navigation."""
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
                app.read_names(english);assert app.switch_module('AIDs');app.search.set('Majide');app.update()
                app.select_aid('AID_マジーデ');app.notebook.select(1);app.update()
                # Browser-to-editor navigation selects the exact source and native row.
                aid_rows=app.asset_index.rows_by_aid['AID_マジーデ']
                i=next(i for i,row in enumerate(aid_rows) if row.source=='AssetTable.bin' and row.group=='アセットテーブル' and row.values[0x30])
                native=aid_rows[i];app.aid_rules_tree.selection_set(str(i));app.aid_edit_rule()
                assert app.active_module=='Appearance rules' and app.doc.filename=='AssetTable.bin' and app.current.index==native.index
                owner=app.doc.owner;rules=owner.views['rules'];source=app.current
                assert len(app.widgets)==49 and len(app.appearance_section_choice.cget('values'))==5
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or app.multiline_text(field):widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(label):
                    next(w for w in app.appearance_tools.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==label).invoke()
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                # Copy rules' settings across characters, preserving destination condition/ID.
                action('Copy settings');clipboard=app.appearance_clipboard[1];assert 0x20 not in clipboard and len(clipboard)==48
                target_row=next(row for row in app.asset_index.rows_by_aid['AID_ディートリヒ'] if row.source=='AssetTable.bin' and row.group=='アセットテーブル' and row.values[0x30])
                dest=rules.records[target_row.index];conditions=rules.value(dest,rules.by_offset[0x20]);name=rules.names[dest.pid]
                app.switch_module('Appearance rules',dest.pid,source_file='AssetTable.bin');action('Paste settings')
                assert rules.value(dest,rules.by_offset[0x30])==clipboard[0x30]
                assert rules.value(dest,rules.by_offset[0x20])==conditions and rules.names[dest.pid]==name
                # Every supported data kind edits through actual widgets.
                write(0xc0,'1234abcd');write(0xf8,'0.73');write(0x38,'2');write(0x114,'4294967295')
                write(0x80,'AB_TEST\nAE_TEST');choose(0x158,'Majide','マジーデ')
                app.update();app.after(180,app.quit);original_loop(app)
                assert 'Majide' in app.previews[0x158][0].cget('text')
                assert app.apply() and not app.dirty_widgets()
                assert rules.value(dest,rules.by_offset[0xc0])=='#1234ABCD'
                write(0xc0,'#bad');assert not app.switch_module('Characters');write(0xc0,'#1234ABCD')
                write(0xf8,'nan');app.appearance_source.set('AssetTable_P0.bin');app.appearance_source_choice.event_generate('<<ComboboxSelected>>');app.update()
                assert app.doc.filename=='AssetTable.bin' and app.appearance_source.get()=='AssetTable.bin';write(0xf8,'0.73')
                assert app.apply()
                # Rule-linked bare FID opens voice/portrait and copy keeps native FID names.
                action('Open linked voice / portrait');assert app.doc.key=='voices' and app.doc.names[app.current.pid]=='FID_マジーデ'
                assert len(app.widgets)==11
                action('Copy settings');voice_copy=app.appearance_clipboard[1]
                voices=owner.views['voices'];dit=next(r for r in voices.records if voices.names[r.pid]=='FID_ディートリヒ')
                app.switch_module('Appearance rules',dit.pid,source_file='AssetTable.bin');action('Paste settings')
                assert voices.names[dit.pid]=='FID_ディートリヒ' and voices.value(dit,voices.by_offset[0x20])==voice_copy[0x20]
                write(0x20,'VoiceLive_TEST');write(0x28,'095');write(0x34,'0.7');write(0x4c,'1');assert app.apply()
                # Live browser FID details expose current unsaved voice changes and jump back.
                app.switch_module('AIDs');app.search.set('Dietrich');app.update();app.select_aid('AID_ディートリヒ');app.notebook.select(2);app.update()
                linked=app.asset_index.linked_rows('AID_ディートリヒ')
                index=next(i for i,row in enumerate(linked) if row.source=='AssetTable.bin' and row.label=='FID_ディートリヒ')
                assert linked[index].values[0x20]=='VoiceLive_TEST'
                app.aid_linked_tree.selection_set(str(index));app.aid_edit_linked();assert app.current.pid==dit.pid and app.doc.key=='voices'
                # Multiline effect strings preserve exact line endings, without array conversion.
                app.switch_module('Appearance rules','info:1',source_file='AssetTable.bin');assert len(app.widgets)==12
                assert isinstance(app.widgets[0x40][1],tk.Text)
                original=app.doc.original(app.current,app.doc.by_offset[0x40]);assert '\n' in original
                assert app.widgets[0x40][1].get('1.0','end-1c')==original
                block='EffectA (BoneA)\nEffectB (BoneB)\r\n'
                write(0x40,block);write(0x78,'0.7');assert app.apply()
                assert app.doc.value(app.current,app.doc.by_offset[0x40])==block
                app.switch_module('Appearance rules','variations:0',source_file='AssetTable.bin');assert len(app.widgets)==10
                write(0x20,'AID_VARIANT_TEST');assert app.apply()
                app.switch_module('Appearance rules','conditions:0',source_file='AssetTable.bin');assert len(app.widgets)==2
                write(0x20,'["AID_CONDITION_TEST"]\n[]');write(0x30,'extra_flag');assert app.apply()
                # Side files expose only their actual sections, and new rule flags are live.
                app.switch_module('Appearance rules','rules:0',source_file='AssetTable_P0.bin')
                assert len(app.appearance_section_choice.cget('values'))==1 and len(app.tree.get_children())==13
                write(0x20,'["AID_LIVE_ONLY_TEST"]');write(0x30,'CD_SIDE_LIVE');assert app.apply()
                side=app.doc
                app.switch_module('Appearance rules','rules:0',source_file='AssetTable_P1.bin');assert len(app.tree.get_children())==10
                write(0x30,'CD_P1_LIVE');assert app.apply()
                app.switch_module('AIDs');app.search.set('AID_LIVE_ONLY_TEST');app.update()
                assert app.current_aid=='AID_LIVE_ONLY_TEST' and app.asset_index.sources_for(app.current_aid)==('AssetTable_P0.bin',)
                assert app.asset_index.rows_by_aid[app.current_aid][0].values[0x30]=='CD_SIDE_LIVE'
                app.save_project();project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==len(app.documents)
                app.export()
                for kind in fw.APPEARANCE_TABLES:
                    document=next(d for d in app.documents.values() if type(d) is kind)
                    result=kind((temporary/'mod/romfs/GameData'/kind.filename).read_bytes())
                    for (pid,offset),value in document.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                # Loading a project while browsing the same AID must refresh its detail panes.
                app.switch_module('Appearance rules','rules:0',source_file='AssetTable_P0.bin');write(0x30,'CD_CHANGED_AGAIN');assert app.apply()
                app.switch_module('AIDs');app.search.set('AID_LIVE_ONLY_TEST');app.update();app.load_project();app.update()
                assert app.asset_index.rows_by_aid['AID_LIVE_ONLY_TEST'][0].values[0x30]=='CD_SIDE_LIVE'
                assert any('CD_SIDE_LIVE' in app.aid_rules_tree.item(i,'values')[-1] for i in app.aid_rules_tree.get_children())
                # Reset removes live-only flags and preserves edits in other files/sections.
                app.switch_module('Appearance rules','rules:0',source_file='AssetTable_P0.bin');app.reset()
                app.switch_module('AIDs');app.search.set('AID_LIVE_ONLY_TEST');app.update();assert 'AID_LIVE_ONLY_TEST' not in app.asset_index.aids
                app.load_project();assert 'AID_LIVE_ONLY_TEST' in app.asset_index.aids
                # Live item flag owners navigate to their actual side file.
                app.switch_module('Items','IID_試作品１号|||',source_file='Item_P1.bin');write(0x1b8,'AID_ITEM_OWNER_TEST')
                app.switch_module('AIDs');app.search.set('AID_ITEM_OWNER_TEST');app.update();app.select_aid('AID_ITEM_OWNER_TEST')
                listing=app.aid_users_tree;listing.selection_set(listing.get_children()[0])
                tab=app.nametowidget(app.notebook.tabs()[0]);next(w for w in tab.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.active_module=='Items' and app.doc.filename=='Item_P1.bin'
                # Last project restores both appearance file and section; sources stay original.
                app.switch_module('Appearance rules',dit.pid,source_file='AssetTable.bin');app.save_project();assert app.open_last_project()
                assert app.active_module=='Appearance rules' and app.doc.filename=='AssetTable.bin' and app.doc.key=='voices'
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.switch_module('Appearance rules',dest.pid,source_file='AssetTable.bin');app.notebook.select(1);app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'appearance-models.png')],check=True)
                app.switch_module('Appearance rules',dit.pid,source_file='AssetTable.bin');app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'appearance-voice.png')],check=True)
                standalone=temporary/'standalone';standalone.mkdir();(standalone/'AssetTable_P1.bin').write_bytes((base/'AssetTable_P1.bin').read_bytes())
                app.open_data(standalone/'AssetTable_P1.bin');assert app.active_module=='Appearance rules' and len(app.documents)==1 and app.doc.key=='rules'
                assert len(errors)==2,errors
                assert not callbacks,callbacks
                print('PASS: five appearance sections, all field kinds/multiline blocks, settings copy without target-condition/ID changes, live AID/FID editing/navigation, side files, reset/load refresh, item owners, combined export and saved file/section restoration.')
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
