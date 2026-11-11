"""Shared primary/shop editing, exact-entry navigation, conditions and safe empty tables."""
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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import fw_editor as fw
import struct

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
hashes={kind.filename:hashlib.sha256((base/kind.filename).read_bytes()).digest() for kind in fw.ITEM_TABLES}
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);assert len(app.documents)==204
                app.switch_module('Items','IID_青銅の剣')
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or field.kind in fw.NUMERIC_ARRAYS:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def action(text):next(w for w in app.shop_tools.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==text).invoke()
                def choose(offset,query,target):
                    field,widget=app.widgets[offset];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    entry=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Entry));app.setvar(entry.cget('textvariable'),query)
                    listing=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    listing.selection_set(next(i for i in listing.get_children() if listing.item(i,'values')[1]==target))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                write(0x4c,'12345');assert app.apply();owner=app.doc
                assert app.switch_module('Shop & Loot') and app.doc.owner is owner
                assert len(app.tree.get_children())==114 and len(app.shop_tree.get_children())==76 and len(app.widgets)==9
                assert app.shop_source_choice.cget('values')==('Item.bin',)
                source_table=app.current;source_row=app.learning_row;original_names=dict(app.doc.names)
                pipe='IID_試作品１号|||';choose(0x28,pipe,pipe);write(0x68,'999');write(0x6a,'-128');write(0x6b,'0');write(0x6c,'255')
                write(0x48,'IID_青銅の剣\nIID_鉄の剣');write(0x58,'[2, 255]');write(0x38,'shop_TEST\n!blocked_TEST');assert app.apply()
                # Invalid paired lists keep the selected entry and its pending form.
                write(0x58,'[2]');other=app.doc.rows_by_table[source_table.pid][1]
                app.shop_tree.selection_set(other.pid)
                from shop_ui import select_entry,show_entry
                select_entry(app);assert app.learning_row.pid==source_row.pid and app.shop_tree.selection()==(source_row.pid,)
                write(0x58,'[2, 255]');write(0x6a,'128');assert not app.switch_module('AIDs');write(0x6a,'-128');assert app.apply()
                # Clipboard replaces values, retaining destination collection/entry headers.
                action('Copy entry');app.switch_module('Shop & Loot','shops:1');target=app.learning_row
                action('Paste values');assert app.doc.value(target,app.doc.by_offset[0x28])==pipe and app.doc.names==original_names
                app.reset();assert app.doc.value(app.learning_row,app.doc.by_offset[0x28])!=pipe
                assert owner.value(owner.by_pid['IID_青銅の剣'],owner.by_offset[0x4c])==12345
                # The item usage map reflects changed slots and opens the exact entry.
                app.switch_module('Items','IID_青銅の剣');app.item_usage_refresh()
                assert not any(u.module=='Shop & Loot' and u.record==source_row.pid and u.field.endswith('0x28') for u in app.item_usage_targets)
                app.switch_module('Items',pipe,source_file='Item_P1.bin');app.item_usage_refresh()
                i=next(i for i,u in enumerate(app.item_usage_targets) if u.module=='Shop & Loot' and u.record==source_row.pid and u.field.endswith('0x28'))
                app.item_usage_tree.selection_set(str(i));app.item_usage_open()
                assert app.active_module=='Shop & Loot' and app.current.pid==source_table.pid and app.learning_row.pid==source_row.pid and app.notebook.index('current')==0
                action('Open item');assert app.active_module=='Items' and app.doc.filename=='Item_P1.bin' and app.current.pid==pipe
                # Lottery links go both ways between the facility editor and a native collection.
                app.switch_module('Shop & Loot',section='loot');assert len(app.tree.get_children())==136 and len(app.widgets)==3
                lottery=next(r for r in app.doc.collections if app.doc.names[r.pid]=='祝品箱');app.switch_module('Shop & Loot',lottery.pid)
                action('Paste values');assert errors[-1].startswith('Copy an entry from the same')
                i=next(i for i,x in enumerate(app.shop_links) if x[0]=='Facilities & Rewards')
                app.shop_links_tree.selection_set(str(i));app.shop_links_open();assert app.active_module=='Facilities & Rewards'
                app.facility_links_refresh();i=next(i for i,x in enumerate(app.facility_links) if x[0]=='Shop & Loot' and x[2]==lottery.pid)
                app.facility_links_tree.selection_set(str(i));app.facility_links_open();assert app.current.pid==lottery.pid and app.active_module=='Shop & Loot'
                row=app.doc.rows_by_table[lottery.pid][1];show_entry(app,row);choose(0x20,'IID_青銅の剣','IID_青銅の剣');write(0x30,'65535');write(0x38,'loot_TEST');assert app.apply()
                assert 'Stored weight sum:' in app.shop_summary.get()
                app.switch_module('Shop & Loot',section='values');assert len(app.shop_tree.get_children())==11 and len(app.widgets)==2
                write(0x20,'65535');write(0x22,'0');assert app.apply()
                # One item document contains primary and auxiliary edits, and exports exactly once.
                app.save_project();app.export();project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==len(app.documents)
                assert project['documents']['Item.bin']['format']=='fw-item-edits-v2'
                assert len(list((temporary/'mod/romfs/GameData').glob('*.bin')))==33
                result=fw.Item((temporary/'mod/romfs/GameData/Item.bin').read_bytes())
                for (pid,offset),value in owner.changes.items():assert result.original(*result.edit_target(pid,offset))==value
                app.reset();assert app.doc.value(app.learning_row,app.doc.by_offset[0x20])!=65535
                app.load_project();assert app.doc.value(app.learning_row,app.doc.by_offset[0x20])==65535
                app.switch_module('Shop & Loot',lottery.pid);app.save_project();assert app.open_last_project()
                assert app.active_module=='Shop & Loot' and app.doc.key=='loot' and app.doc.owner.filename=='Item.bin'
                app.geometry('1000x680');app.update();assert app.notebook.winfo_rootx()+app.notebook.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
                app.geometry('1180x780');app.switch_module('Shop & Loot',source_row.pid);app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'shops-inventory.png')],check=True)
                app.switch_module('Shop & Loot',row.pid);app.notebook.select(0);app.update()
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'shops-loot.png')],check=True)
                # Standalone item input and an empty existing collection remain usable.
                standalone=temporary/'standalone';standalone.mkdir()
                empty_raw=bytearray((base/'Item.bin').read_bytes());native=fw.Item(bytes(empty_raw));empty=native.views['shops'].collections[-1]
                struct.pack_into('<H',empty_raw,empty.offset+18,0);(standalone/'Item.bin').write_bytes(empty_raw)
                assert app.open_data(standalone/'Item.bin') and len(app.documents)==1
                app.switch_module('Shop & Loot',empty.pid);assert app.learning_row is None and not app.widgets and not app.shop_tree.get_children()
                assert app.doc.owner.build()==app.doc.owner.raw
                for name,digest in hashes.items():assert hashlib.sha256((base/name).read_bytes()).digest()==digest
                assert len(errors)==3,errors
                assert not callbacks,callbacks
                print('PASS: shop/loot/value tiers, shared item owner, paired exchange validation, signed discount, clipboard/reset with fixed headers, live IID-to-exact-entry and facility-lottery links, single Item.bin/combined export, v2 project/reopen, empty collection and source immutability.')
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
