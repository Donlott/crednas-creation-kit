"""Exercise the read-only AID browser, live references and editor transitions."""
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

source=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        def exercise():
            try:
                app.read_names(english)
                original_state=app.session_state()
                hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('AssetTable*.bin')}
                assert app.switch_module('AIDs')
                assert len({aid for aid,_ in app.aid_tree_map.values()})==1093
                assert not app.widgets and app.doc is None
                # Default file groups and file filtering retain all provenance.
                roots=app.tree.get_children()
                assert all(item.startswith('file:') for item in roots)
                assert [item.removeprefix('file:') for item in roots]==sorted([item.removeprefix('file:') for item in roots],key=str.casefold)
                app.aid_source.set('AssetTable_P0.bin');app.filter_aids();app.update()
                assert set(file for aid,file in app.aid_tree_map.values())=={'AssetTable_P0.bin'}
                expected={aid for aid in app.asset_index.aids if 'AssetTable_P0.bin' in app.asset_index.sources_for(aid)}
                assert {aid for aid,_ in app.aid_tree_map.values()}==expected
                for root in app.tree.get_children():
                    names=[app.tree.item(item,'text').casefold() for item in app.tree.get_children(root)]
                    assert names==sorted(names)
                app.aid_group_files.set(False);app.filter_aids();app.update()
                assert set(app.tree.get_children())==expected
                app.aid_source.set('All files');app.aid_group_files.set(True);app.filter_aids()
                app.search.set('Majide');app.update()
                assert app.aid_item('AID_マジーデ')
                assert app.select_aid('AID_マジーデ','Person.bin');app.update()
                assert 'Person.bin' in app.details.get()
                assert app.current_aid=='AID_マジーデ'
                assert any('Maj0' in app.aid_linked_tree.item(i,'values')[-1] for i in app.aid_linked_tree.get_children())
                voice=next(i for i in app.aid_linked_tree.get_children() if 'Maj0' in app.aid_linked_tree.item(i,'values')[-1])
                app.aid_linked_tree.selection_set(voice);app.update()
                assert 'Maj0' in app.aid_linked_detail.get('1.0','end-1c')
                assert app.aid_source_tree.get_children()
                app.copy_aid();assert app.clipboard_get()=='AID_マジーデ'
                assert app.session_state()==original_state
                app.geometry('1000x680');app.update()
                assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                for tab,name in ((0,'aid-users'),(1,'aid-rules'),(2,'aid-linked')):
                    app.notebook.select(tab);app.update()
                    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/(name+'.png'))],check=True)
                # The user list opens the correct record in the existing editor.
                app.notebook.select(0);app.update();listing=app.aid_users_tree
                selected=next(i for i in listing.get_children() if listing.item(i,'values')[-1]=='PID_マジーデ' and listing.item(i,'values')[1]=='Direct flag')
                listing.selection_set(selected)
                tab=app.nametowidget(app.notebook.tabs()[0])
                next(w for w in tab.winfo_children() if isinstance(w,ttk.Button)).invoke()
                assert app.active_module=='Characters' and app.current.pid=='PID_マジーデ'
                raw=app.widgets[0x278][1];raw.delete(0,'end');raw.insert(0,'AID_BROWSER_NEW')
                assert app.switch_module('AIDs')
                assert 'AID_BROWSER_NEW' in app.asset_index.aids
                assert app.asset_index.direct_count('AID_BROWSER_NEW')==1
                assert app.asset_index.direct_count('AID_マジーデ')==1
                app.search.set('AID_BROWSER_NEW');app.update()
                assert app.current_aid=='AID_BROWSER_NEW'
                app.save_project();project=json.loads((temporary/'project.json').read_text(encoding='utf8'))
                assert set(project['documents'])=={d.filename for d in app.documents.values()}
                app.export();assert len(list((temporary/'mod').rglob('AssetTable*.bin')))==3
                app.load_project();assert app.current_aid=='AID_BROWSER_NEW'
                assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('AssetTable*.bin')}
                # Negated conditions stay visibly distinct from direct flag assignment.
                app.search.set('');assert app.select_aid('AID_モブ');app.update()
                assert any(app.aid_rules_tree.item(i,'values')[2] in ('Negated','Mixed') for i in app.aid_rules_tree.get_children())
                # Appearance-only folders load editable documents; the AID browser remains available.
                standalone=temporary/'assets-only';standalone.mkdir();(standalone/'AssetTable.bin').write_bytes((source/'AssetTable.bin').read_bytes())
                app.open_data(standalone/'AssetTable.bin')
                assert app.active_module=='Appearance rules' and set(app.documents)=={'Appearance rules'} and app.asset_index.tables
                app.switch_module('AIDs')
                app.read_names(english);app.filter()
                assert app.tree.get_children()
                assert 'AssetTable_P0.bin' not in app.aid_source_choice.cget('values')
                print('PASS: AID UI file grouping/filtering/sorting, search/copy, unnamed and negated rules, voice/portrait links, current unsaved owners, character navigation, combined appearance export, source immutability and asset-only loading.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    sys.argv=['fw_editor.py',str(source)]
    with patch.object(tk.Tk,'mainloop',loop), \
         patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')), \
         patch.object(messagebox,'showinfo'), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(message)), \
         patch.object(messagebox,'askyesno',return_value=True):fw.main()
    if failures:raise failures[0]
