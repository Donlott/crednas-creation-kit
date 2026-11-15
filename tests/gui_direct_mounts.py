"""Actual Linux-style script entry, folder-only opening and lazy mount sources."""
from pathlib import Path
import json,os,runpy,sys,tempfile,tkinter as tk
from tkinter import filedialog,messagebox
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES']);main=Path(os.environ['FW_MOUNTS_MAIN'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory);os.environ['FW_EDITOR_CONFIG']=str(temp/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                import fw_editor as fw
                from mount_ui import open_editor
                from mount_data import source_tables,MODULE
                assert fw.__name__=='__main__'
                assert type(app.documents['Items']) is fw.Item
                app.read_names(english)
                # The real direct entry and folder loader already have all sources.
                before={name:doc for name,doc in app.documents.items()}
                window=open_editor(app);app.update();assert window is not None and len(window.offers)==41
                assert all(app.documents[key] is doc for key,doc in before.items());window.destroy()
                # A partial session should fill missing tables without replacing edits.
                item,job,skill=source_tables(app.documents);item.set(item.records[0],item.by_offset[0x4c],1234)
                for key in [k for k,d in app.documents.items() if d is job or d is skill]:app.documents.pop(key);app.sources.pop(key)
                window=open_editor(app);app.update();assert window is not None and len(window.offers)==41
                assert source_tables(app.documents)[0] is item and item.value(item.records[0],item.by_offset[0x4c])==1234
                window.main_path.set(str(main));window.message_path.set(str(english/'Item.msbt.zst'));window.enabled.set(True)
                assert window.apply();window.action(app.save_project);window.action(app.export)
                assert MODULE in app.documents
                assert (temp/'mod/romfs/GameData/Item.bin').is_file()
                assert len(list((temp/'mod/exefs').glob('*.ips')))==1
                window.destroy();app.load_project();assert app.documents[MODULE].enabled
                assert not errors,errors
                assert not callbacks,callbacks
                print('PASS direct fw_editor.py entry: folder finds tables, tools share models, lazy loads preserve edits, catalog enables, project reopens and export succeeds.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(300,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=[str(root/'fw_editor.py'),str(base)];runpy.run_path(str(root/'fw_editor.py'),run_name='__main__')
    if failures:raise failures[0]
