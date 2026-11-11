"""Actual event forms, cape chain, source restoration, scripts and 204-file exports."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
from event_ui import RECEIVED,LOST,EQUIPPED,CAPE
base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
hashes={f:hashlib.sha256((base/f).read_bytes()).digest() for f in fw.EVENT_FILES}
with tempfile.TemporaryDirectory() as temporary:
 temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
 def loop(app,*args,**kwargs):
  app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
  def exercise():
   try:
    app.read_names(english);assert len(app.documents)==204 and len(app.module_choice.cget('values'))==16
    assert app.switch_module('Events','variables:1216:0',source_file='Variable.bin')
    owner=app.doc.owner;assert len(app.widgets)==12 and 0x20 not in app.widgets
    assert len(app.event_source_choice.cget('values'))==13 and app.learning_row.pid=='variables:1216:0'
    assert 'Majide' in app.heading.get()
    def write(off,value):
     f,w=app.widgets[off]
     if f.kind in fw.LIST_TYPES:w.delete('1.0','end');w.insert('1.0',value)
     else:w.delete(0,'end');w.insert(0,value)
    def button(parent,text):return next(w for w in parent.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')==text)
    # Typed conditions are event logic, with raw identifiers preserved.
    write(0x50,json.dumps([RECEIVED],ensure_ascii=False));assert app.apply()
    assert owner.views['variables'].value(app.learning_row,app.doc.by_offset[0x50])==[[RECEIVED]]
    app.update();app.after(170,app.quit);original_loop(app)
    assert 'received' in app.previews[0x50][0].get('1.0','end-1c').lower()
    # A broken condition blocks switching and restores the source dropdown.
    write(0x50,'invalid JSON');app.event_source.set('Timeline_Com.bin')
    assert not app.switch_module('Events',source_file='Timeline_Com.bin')
    assert app.event_source.get()=='Variable.bin' and len(errors)==1
    write(0x50,json.dumps([RECEIVED],ensure_ascii=False));assert app.apply()
    # Existing-row copy/paste excludes locked names; reset clears only the pasted row.
    form=app.event_form.master;tools=next(w for w in form.winfo_children() if isinstance(w,ttk.Frame))
    button(tools,'Copy editable values').invoke()
    assert app.switch_module('Events','variables:0:0',source_file='Variable_P0.bin')
    name=app.doc.value(app.learning_row,app.doc.by_offset[0x20])
    form=app.event_form.master;tools=next(w for w in form.winfo_children() if isinstance(w,ttk.Frame))
    button(tools,'Paste editable values').invoke();assert app.doc.value(app.learning_row,app.doc.by_offset[0x50])==[[RECEIVED]]
    assert app.doc.value(app.learning_row,app.doc.by_offset[0x20])==name
    button(tools,'Reset row').invoke();assert not app.doc.owner.modified
    # All 13 source files and their four schemas can be selected.
    for filename in fw.EVENT_FILES:
     assert app.switch_module('Events',source_file=filename),filename
     expected=12 if filename.startswith('Variable') else 20 if filename.startswith('Timeline') else 7 if filename=='Chapter.bin' else 8
     assert len(app.widgets)==expected,(filename,len(app.widgets))
    assert app.switch_module('Events','timeline:0:82',source_file='Timeline_Part1_Dit.bin')
    assert app.widgets[0x28][1].get('1.0','end-1c')=='BD12_04' and 0xd0 not in app.widgets
    write(0x5e,'-32768');assert app.apply();app.reset();assert not app.doc.owner.modified
    # The cape shortcuts resolve the exact event by name/argument and open its source.
    app.event_cape_tree.selection_set('1');app.event_cape_open();app.update()
    assert app.doc.filename=='Variable.bin' and app.learning_row.pid=='variables:1216:0'
    app.event_cape_tree.selection_set('5');app.event_cape_open();assert app.doc.filename=='Timeline_Part1_Dit.bin' and app.learning_row.pid=='timeline:0:82'
    app.notebook.select(3);app.event_script_choice.set('cmdbtl/BD12_04.bin.zst');app.event_script_show()
    text=app.event_script_output.get('1.0','end-1c');assert 'CmdBtlCommon.bin' in text and 'CmdBtlUtil.bin' in text and '0x2010' in text
    assert str(app.event_script_output.cget('state'))=='disabled'
    # Connections follow current variable dependencies, including the edited cape rule.
    app.switch_module('Events','variables:871:0',source_file='Variable.bin');app.event_connections_refresh()
    tree=app.event_connections_tree
    key=next(k for k in tree.get_children() if tree.item(k,'values')[2]=='variables:1216:0')
    tree.selection_set(key);app.event_connections_open();assert app.learning_row.pid=='variables:1216:0'
    # New character references in event conditions participate in removal guards.
    person=app.documents['Characters'];person.create_character('PID_Event_Test')
    assert 'PID_Event_Test' in app.suggestions(app.doc.by_offset[0x50])
    write(0x50,json.dumps([RECEIVED,'PID_Event_Test'],ensure_ascii=False));assert app.apply()
    app.switch_module('Characters','PID_Event_Test');app.character_creation_actions['Remove new character'].invoke();app.update()
    assert 'PID_Event_Test' in person.new_characters and len(errors)==2
    app.switch_module('Events','variables:1216:0',source_file='Variable.bin');write(0x50,json.dumps([RECEIVED],ensure_ascii=False));assert app.apply()
    app.switch_module('Characters','PID_Event_Test');app.character_creation_actions['Remove new character'].invoke();app.update();assert not person.new_characters
    app.switch_module('Events','variables:1216:0',source_file='Variable.bin');app.save_project();app.export()
    project=json.loads((temporary/'project.json').read_text(encoding='utf8'));assert len(project['documents'])==204
    assert project['documents']['Variable.bin']['format']=='fw-event-edits-v1'
    out=temporary/'mod/romfs/GameData';assert len(list(out.rglob('*.bin')))==204
    result=fw.EventData((out/'Variable.bin').read_bytes(),'Variable.bin');v=result.views['variables']
    assert v.value(v.by_pid['variables:1216:0'],v.by_offset[0x50])==[[RECEIVED]]
    for filename in fw.EVENT_FILES:
     if filename!='Variable.bin':assert (out/filename).read_bytes()==(base/filename).read_bytes(),filename
    assert person.build()==person.raw
    # Source/module restoration, failed reopen protection and standalone event data.
    app.reset();assert not owner.modified;app.load_project();assert owner.modified
    app.save_project();assert app.open_last_project() and app.active_module=='Events' and app.doc.filename=='Variable.bin'
    app.switch_module('Events','variables:1216:0',source_file='Variable.bin');app.notebook.select(0);app.geometry('1000x680');app.update()
    assert app.event_form.winfo_width()>500
    app.geometry('1180x780');app.update();previews=Path(os.environ.get('FW_PREVIEW_DIR',temporary));previews.mkdir(parents=True,exist_ok=True)
    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(app.winfo_id()),str(previews/'events.png')],check=True)
    isolated=temporary/'event-only';isolated.mkdir();(isolated/'Timeline_Com.bin').write_bytes((base/'Timeline_Com.bin').read_bytes())
    app.open_data(isolated/'Timeline_Com.bin');assert app.active_module=='Events' and len(app.documents)==1
    assert 'No adjacent Script folder' in app.event_script_output.get('1.0','end-1c')
    for file,digest in hashes.items():assert hashlib.sha256((base/file).read_bytes()).digest()==digest
    assert not callbacks,callbacks
    print('PASS: 13 event sources/4 schemas, English/raw previews, cape conditions/duel shortcuts, ordered arguments/dates, identity-preserving copy/reset, invalid source restoration, exact connections, current PID guards, read-only ASF imports, v1/suite/reopen/204-file export, source immutability, compact and standalone layouts.')
   except Exception as exc:
    failures.append(exc)
    import traceback;traceback.print_exc()
   finally:app.destroy()
  app.after(350,exercise);original_loop(app,*args,**kwargs)
 with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
  sys.argv=['fw_editor.py',str(base)];fw.main()
 if failures:raise failures[0]
