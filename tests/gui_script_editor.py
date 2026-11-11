"""Real Tk script editing, translations, references, compressed export and reopen."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
import tkinter as tk
from tkinter import filedialog,messagebox
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw
from script_ui import open_editor
from script_data import ScriptDocument
from script_bytecode import LITERALS,INVERSE,Module
from person_index import uses
base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];callbacks=[]
with tempfile.TemporaryDirectory() as temp:
 temp=Path(temp);os.environ['FW_EDITOR_CONFIG']=str(temp/'config')
 def loop(app,*args,**kwargs):
  app.report_callback_exception=lambda kind,error,tb:callbacks.append(error)
  def exercise():
   try:
    app.read_names(english);window=open_editor(app,'cmdbtl/BD12_04.bin.zst');app.update()
    assert len(window.paths)==183 and window.doc.filename=='Script/cmdbtl/BD12_04.bin.zst'
    doc=window.doc;source=window.paths[window.source.get()];digest=hashlib.sha256(source.read_bytes()).digest()
    assert len(app.documents)==205 and app.session_state()==app.saved_state
    assert len(window.function_tree.get_children())==51 and len(window.constant_tree.get_children())==53
    window.tabs.select(1);window.constant_tree.selection_set('0');window.select_constant()
    window.value.set('PID_Script_Editor_Test');assert window.commit()
    assert any(u.source==doc.filename for u in uses('PID_Script_Editor_Test',app.documents))
    assert window.uses_tree.get_children()
    window.value.set('マジーデ');app.update();assert window.translation.get()==app.translator.resolve('マジーデ').text
    window.value.set('PID_Script_Editor_Test');assert window.commit()
    # Double-clicking a use opens the exact instruction and its decoded function.
    window.uses_tree.selection_set(window.uses_tree.get_children()[0]);window.open_use();app.update()
    assert window.tabs.index('current')==0 and window.ii is not None
    window.open_constant_use();assert window.tabs.index('current')==1 and window.ci==0
    window.tabs.select(0)
    # Edit actual numeric code, interpreting the same bits as float then integer.
    found=next((fi,ii,ins) for fi,f in enumerate(doc.module.functions) for ii,ins in enumerate(f.instructions) if ins.name in LITERALS)
    fi,ii,ins=found;window.function_tree.selection_set(str(fi));window.select_function();window.code_tree.selection_set(str(ii));window.select_instruction()
    window.mode.set('Floating point');window.change_mode();window.value.set('2.5');assert window.commit()
    window.mode.set('Unsigned bits');window.change_mode();assert int(window.value.get())>100
    # Invalid numbers block script switching and preserve the previous source.
    before=doc.snapshot_edits();window.value.set('invalid-number');window.select_source('hub/Hub_000_DIT.bin.zst')
    assert window.source.get()=='cmdbtl/BD12_04.bin.zst' and doc.snapshot_edits()==before and len(errors)==1
    window.show_form(('instruction',fi,ii))
    # Restore only this instruction; keep the string edit.
    window.restore();assert (fi,ii) not in doc.instructions and doc.modified
    # The duel script delegates its flow; exercise branches in a hub script.
    window.select_source('hub/Hub_000_DIT.bin.zst');code_doc=window.doc
    # Invert one actual conditional without changing its target.
    fi,ii,ins=next((fi,ii,ins) for fi,f in enumerate(code_doc.module.functions) for ii,ins in enumerate(f.instructions) if ins.name in INVERSE)
    window.function_tree.selection_set(str(fi));window.select_function();window.code_tree.selection_set(str(ii));window.select_instruction()
    window.value.set(INVERSE[ins.name]);assert window.commit();assert code_doc.instruction(fi,ii)[1]==ins.arguments
    # Existing compatible command references are the only call choices.
    fi,ii,ins=next((fi,ii,ins) for fi,f in enumerate(code_doc.module.functions) for ii,ins in enumerate(f.instructions) if len(code_doc.module.call_options(ins))>1)
    window.function_tree.selection_set(str(fi));window.select_function();window.code_tree.selection_set(str(ii));window.select_instruction()
    alternative=next(k for k,v in window.call_values.items() if v!=ins.arguments[0]);window.value.set(alternative);assert window.commit()
    window.action(app.save_project);window.action(app.export)
    project=json.loads((temp/'project.json').read_text(encoding='utf8'));assert project['format']=='fw-hacking-suite-project-v2' and len(project['documents'])==206
    target=temp/'mod/romfs'/doc.filename;exported=ScriptDocument(target.read_bytes(),doc.filename)
    assert exported.module.constants[0].text=='PID_Script_Editor_Test'
    assert len(list((temp/'mod/romfs/GameData').rglob('*.bin')))==204
    assert not (temp/'mod/romfs/GameData/Script').exists()
    assert hashlib.sha256(source.read_bytes()).digest()==digest
    # Reference navigation reopens the exact script string, without switching main table state.
    window.close();key=next(k for k,d in app.documents.items() if d is doc)
    assert app.switch_module(key,'SCRIPT_STRING_0',source_file=doc.filename)
    window=app.script_window;assert window.ci==0 and window.tabs.index('current')==1;window.close()
    assert app.open_last_project();loaded=next(d for d in app.documents.values() if isinstance(d,ScriptDocument) and d.filename==doc.filename);assert loaded.snapshot_edits()==doc.snapshot_edits()
    window=open_editor(app,'cmdbtl/BD12_04.bin.zst');window.tabs.select(0)
    fi=next(i for i,f in enumerate(window.doc.module.functions) if f.signature.name and len(f.instructions)>20)
    window.function_tree.selection_set(str(fi));window.function_tree.see(str(fi));window.select_function()
    literal=next((i for i,ins in enumerate(window.doc.module.functions[fi].instructions) if ins.name in LITERALS),None)
    if literal is not None:window.code_tree.selection_set(str(literal));window.select_instruction()
    window.geometry('1140x760');app.update()
    assert window.code_tree.winfo_width()>500
    previews=Path(os.environ.get('FW_PREVIEW_DIR',temp));previews.mkdir(parents=True,exist_ok=True)
    subprocess.run(['import','-display',os.environ['DISPLAY'],'-window',str(window.winfo_id()),str(previews/'scripts.png')],check=True)
    window.geometry('970x650');app.update();assert window.input.winfo_width()>200
    window.close();assert not callbacks,callbacks
    print('PASS: 183-script browser, real instruction/constant edits, live translation, exact uses, invalid edit blocking, literal modes, condition inversion, compatible calls, reference navigation, source immutability, compressed romfs/Script export, suite v2 save/reopen and compact layouts.')
   except Exception as exc:
    failures.append(exc)
    import traceback;traceback.print_exc()
   finally:app.destroy()
  app.after(350,exercise);original_loop(app,*args,**kwargs)
 with patch.object(tk.Tk,'mainloop',loop),patch.object(filedialog,'askopenfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'asksaveasfilename',return_value=str(temp/'project.json')),patch.object(filedialog,'askdirectory',return_value=str(temp/'mod')),patch.object(messagebox,'showinfo'),patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))),patch.object(messagebox,'askyesno',return_value=True):
  sys.argv=['fw_editor.py',str(base)];fw.main()
 if failures:raise failures[0]
