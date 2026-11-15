"""Mount toggle, price validation, project reopen, normal modules and mod cleanup."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,tkinter as tk
from tkinter import filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
from mount_ui import open_editor
from mount_data import MODULE,NAME,BANK_OUTPUT,MountPatch,IID,MOVE_IID
from mount_native import IPS_PATH

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES']);main=Path(os.environ['FW_MOUNTS_MAIN'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
originals=[main,english/'Item.msbt.zst',base/'Item.bin',base/'Job.bin'];hashes={p:hashlib.sha256(p.read_bytes()).digest() for p in originals}
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory);os.environ['FW_EDITOR_CONFIG']=str(temp/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english)
                menu=app.nametowidget(app.cget('menu'));tools=app.nametowidget(menu.entrycget(2,'menu'))
                index=next(i for i in range(tools.index('end')+1) if tools.entrycget(i,'label')=='Buyable mounts…')
                tools.invoke(index);window=app.mount_window;app.update();assert open_editor(app) is window
                window.main_path.set(str(main));window.message_path.set(str(english/'Item.msbt.zst'));window.enabled.set(True)
                window.tree.selection_set(IID);window.select();app.update();window.gold.set('0');assert not window.apply() and MODULE not in app.documents and len(errors)==1
                window.gold.set('1000');assert window.set_price();window.tree.selection_set(MOVE_IID);window.select();window.gold.set('5000');assert window.set_price()
                assert len(window.offers)==41 and len({o.rid for o in window.offers.values()})==22
                canto=next(o for o in window.offers.values() if o.skill_name=='Canto');window.tree.selection_set(canto.iid);window.select();window.gold.set('9000');assert window.set_price()
                assert window.apply();doc=app.documents[MODULE];assert doc.prices[canto.iid]==9000
                assert doc.enabled and doc.price==1000 and doc.move_price==5000 and app.session_state()!=app.saved_state
                window.action(app.save_project);window.action(app.export)
                assert (temp/'mod'/IPS_PATH).is_file()
                assert fw.messages((temp/'mod'/BANK_OUTPUT).read_bytes())[NAME]=='Horse (Dodge)'
                window.destroy();app.load_project();assert app.documents[MODULE].enabled and app.documents[MODULE].price==1000 and app.documents[MODULE].move_price==5000
                for module in ('Characters','Classes','AIDs','Skills','Items','Shop & Loot','Events'):
                    assert app.switch_module(module),module
                app.rebuild_translator()
                window=open_editor(app);window.geometry('1040x740');app.update();assert window.pending_prices[canto.iid]==9000
                window.search.set('Canto');app.update();assert window.tree.get_children() and all('Canto' in window.tree.set(i,'skill') for i in window.tree.get_children())
                window.search.set('');app.update()
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temp));previews.mkdir(parents=True,exist_ok=True)
                subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(window.winfo_id()),str(previews/'buyable-mounts.png')],check=True)
                window.enabled.set(False);assert window.apply();window.action(app.export)
                assert not (temp/'mod'/IPS_PATH).exists() and not (temp/'mod'/BANK_OUTPUT).exists()
                assert (temp/'mod/romfs/GameData/Item.bin').read_bytes()==(base/'Item.bin').read_bytes()
                window.destroy()
                for path,sha in hashes.items():assert hashlib.sha256(path.read_bytes()).digest()==sha
                assert not callbacks,callbacks
                print('PASS mount menu, validation, project persistence, modules, export, disable cleanup and original-file preservation.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(250,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
