"""Actual inventory creation, exact navigation, project reopen, and safe reset."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys,tempfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import fw_editor as fw

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
source_hash=hashlib.sha256((base/'Item.bin').read_bytes()).digest()
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
with tempfile.TemporaryDirectory() as temporary:
    temp=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temp/'settings')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english);owner=app.documents['Items'];v=owner.views['shops']
                owner.create_item('IID_New_Shop_GUI',owner.records[1].pid);app.rebuild_translator()
                table=v.collections[0].pid;other=v.collections[1].pid;original=len(v.rows_by_table[table])
                assert app.switch_module('Shop & Loot',table)
                assert str(app.shop_entry_actions['Undo last addition'].cget('state'))=='disabled'
                def action(label):app.shop_entry_actions[label].invoke();app.update()
                def write(offset,value):
                    field,widget=app.widgets[offset]
                    if field.kind in fw.LIST_TYPES or field.kind in fw.NUMERIC_ARRAYS:widget.delete('1.0','end');widget.insert('1.0',value)
                    else:widget.delete(0,'end');widget.insert(0,value)
                def pick_new_item():
                    field,widget=app.widgets[0x28];app.pick(field,widget)
                    dialog=next(w for w in app.winfo_children() if isinstance(w,tk.Toplevel))
                    tree=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Treeview))
                    tree.selection_set(next(i for i in tree.get_children() if tree.item(i,'values')[1]=='IID_New_Shop_GUI'))
                    next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button)).invoke()
                action('Add entry');first=app.learning_row.pid
                assert len(v.rows_by_table[table])==original+1 and len(app.shop_tree.get_children())==original+1
                assert app.learning_row.index==original and owner.modified and v.table_changed(table)
                assert int(app.tree.set(str(app.current.index),'serial'))==original+1
                pick_new_item();write(0x68,'245');write(0x38,'new_shop_condition');write(0x48,'IID_New_Shop_GUI');write(0x58,'[2]')
                assert app.apply();action('Duplicate entry');second=app.learning_row.pid
                assert app.widgets[0x28][1].get()=='IID_New_Shop_GUI' and app.widgets[0x68][1].get()=='245'
                write(0x68,'65536');before=owner.added_count;action('Add entry')
                assert owner.added_count==before and len(errors)==1
                write(0x68,'345');assert app.apply();action('Undo last addition')
                assert second not in v.by_pid and app.learning_row.pid==first and not app.shop_tree.exists(second)
                action('Duplicate entry');second=app.learning_row.pid
                assert app.switch_module('Shop & Loot',other);action('Add entry');other_row=app.learning_row.pid
                write(0x28,'IID_New_Shop_GUI');assert app.apply()
                # Live item usage finds and opens the newly appended inventory row.
                assert app.switch_module('Items','IID_New_Shop_GUI');app.item_usage_refresh()
                index=next(i for i,u in enumerate(app.item_usage_targets) if u.record==first and u.module=='Shop & Loot')
                app.item_usage_tree.selection_set(str(index));app.item_usage_open();app.update()
                assert app.current.pid==table and app.learning_row.pid==first
                # Save/export includes new definitions and inventory rows once, without backups.
                app.save_project();app.export();app.export()
                project=json.loads((temp/'project.json').read_text(encoding='utf8'))
                assert project['documents']['Item.bin']['format']=='fw-item-edits-v4'
                result=fw.Item((temp/'mod/romfs/GameData/Item.bin').read_bytes())
                assert len(result.views['shops'].rows_by_table[table])==original+2
                assert result.views['shops'].value(result.views['shops'].by_pid[first],result.views['shops'].by_offset[0x28])=='IID_New_Shop_GUI'
                assert 'IID_New_Shop_GUI' in result.by_pid and not list((temp/'mod').rglob('*.backup-*'))
                # Resetting one inventory preserves other inventories and item definitions.
                app.reset();assert owner.added_count==1 and first not in v.by_pid and other_row in v.by_pid
                assert 'IID_New_Shop_GUI' in owner.by_pid
                app.load_project();owner=app.documents['Items'];v=owner.views['shops'];assert owner.added_count==3
                app.switch_module('Shop & Loot',second);assert app.learning_row.pid==second
                app.save_project();assert app.open_last_project()
                owner=app.documents['Items'];v=owner.views['shops'];assert owner.added_count==3
                app.switch_module('Shop & Loot',first);app.geometry('1000x680');app.update()
                for button in app.shop_entry_actions.values():assert button.winfo_rootx()+button.winfo_width()<=app.winfo_rootx()+app.winfo_width()
                app.geometry('1180x780');app.lift();app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temp));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'shop-new-entries.png')],check=True)
                # An empty inventory can receive a first row, then return to empty.
                empty_source=temp/'empty-source';empty_source.mkdir()
                raw=bytearray((base/'Item.bin').read_bytes());native=fw.Item(bytes(raw));empty=native.views['shops'].collections[-1]
                struct.pack_into('<H',raw,empty.offset+18,0);(empty_source/'Item.bin').write_bytes(raw)
                assert app.open_data(empty_source)
                app.switch_module('Shop & Loot',empty.pid);app.update()
                assert not app.shop_tree.get_children() and not app.learning_row
                assert str(app.shop_entry_actions['Duplicate entry'].cget('state'))=='disabled'
                action('Add entry');assert app.learning_row.index==0 and len(app.widgets)==9
                write(0x28,'IID_青銅の剣');assert app.apply();action('Undo last addition')
                assert not app.shop_tree.get_children() and not app.learning_row
                assert not app.doc.owner.modified and str(app.shop_entry_actions['Undo last addition'].cget('state'))=='disabled'
                app.switch_module('Shop & Loot',section='loot');assert not app.shop_entry_actions
                assert hashlib.sha256((base/'Item.bin').read_bytes()).digest()==source_hash
                assert len(errors)==1 and not callbacks,(errors,callbacks)
                print('PASS: Add/Duplicate/Undo; empty shops; paired fields; validation; live new-item picker/usage navigation; v4 save/export/reopen; isolated reset; no backups; source immutability; compact controls.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')), \
         patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')), \
         patch.object(messagebox,'showinfo'),patch.object(messagebox,'askyesno',return_value=True), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
