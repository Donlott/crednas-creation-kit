"""Private-source GUI flow: configure, save, reopen, combine, disable, export."""
import hashlib,os,sys,tempfile,subprocess,tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
import battalion_data as bat
from battalion_ui import open_editor
import mount_data as mount

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES']);main=Path(os.environ['FW_MOUNTS_MAIN'])
paths=[main,*[base/n for n in ('Item.bin','Legion.bin','Skill.bin')],*[english/(n+'.msbt.zst') for n in ('Item','Legion','Skill')]]
hashes={p:hashlib.sha256(p.read_bytes()).digest() for p in paths}
original_loop=tk.Tk.mainloop;errors=[];failures=[];callbacks=[]
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory);os.environ['FW_EDITOR_CONFIG']=str(temp/'config')
    def loop(app,*args,**kwargs):
        app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
        def exercise():
            try:
                app.read_names(english)
                menu=app.nametowidget(app.cget('menu'));tools=app.nametowidget(menu.entrycget(2,'menu'))
                at=next(i for i in range(tools.index('end')+1) if tools.entrycget(i,'label')=='Buyable battalions…')
                tools.invoke(at);window=app.battalion_window;app.update();assert open_editor(app) is window
                window.main_path.set(str(main));window.message_path.set(str(english/'Item.msbt.zst'));window.enabled.set(True)
                assert len(window.offers)==99
                first,second=list(window.offers)[:2];window.tree.selection_set(first);window.select();app.update()
                window.gold.set('0');assert not window.apply() and len(errors)==1 and bat.MODULE not in app.documents
                window.gold.set('1234');window.limit.set('2');assert window.set_offer()
                window.tree.selection_set(second);window.select();window.available.set(False);assert window.set_offer()
                assert window.apply();saved=app.documents[bat.MODULE];assert saved.limits[first]==2 and second in saved.disabled
                window.search.set('Springers');app.update();assert window.tree.get_children();window.search.set('');app.update()
                # Joint export must produce one bank and one compatible code patch.
                mounts=mount.MountPatch(main,english/'Item.msbt.zst');mounts.configure(True,1000)
                app.documents[mount.MODULE]=mounts;app.sources[mount.MODULE]=main
                window.action(app.save_project);window.action(app.export)
                names=fw.messages((temp/'mod'/bat.BANK_OUTPUT).read_bytes())
                assert names[mount.NAME]=='Horse (Dodge)' and names[window.offers[first].name_key].startswith('Battalion: ')
                assert len(bat.decode_ips((temp/'mod'/bat.IPS_PATH).read_bytes()))==4
                window.destroy();app.load_project();assert app.documents[bat.MODULE].limits[first]==2
                assert second in app.documents[bat.MODULE].disabled and app.documents[mount.MODULE].enabled
                for module in ('Legion','Items','Shop & Loot','Characters'):assert app.switch_module(module)
                window=open_editor(app);app.update();assert window.tree.set(first,'limit')=='2' and window.tree.set(second,'available')=='No'
                previews=Path(os.environ.get('FW_PREVIEW_DIR',temp));previews.mkdir(parents=True,exist_ok=True)
                if sys.platform!='win32':subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(window.winfo_id()),str(previews/'buyable-battalions.png')],check=True)
                window.enabled.set(False);assert window.apply();window.action(app.export)
                assert len(bat.decode_ips((temp/'mod'/bat.IPS_PATH).read_bytes()))==3
                assert not any(key.startswith('MIID_CCK_BuyBattalion_') for key in fw.messages((temp/'mod'/bat.BANK_OUTPUT).read_bytes()))
                app.documents[mount.MODULE].configure(False,1000);window.action(app.export)
                assert not (temp/'mod'/bat.IPS_PATH).exists() and not (temp/'mod'/bat.BANK_OUTPUT).exists()
                assert not list((temp/'mod').rglob('*.backup-*'))
                assert not callbacks,callbacks
                for p,sha in hashes.items():assert hashlib.sha256(p.read_bytes()).digest()==sha
                print('PASS battalion catalog, guards, stock, hiding, project reopen, joint mount export, independent disable, modules and original preservation.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(250,exercise);original_loop(app,*args,**kwargs)
    with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
    if failures:raise failures[0]
