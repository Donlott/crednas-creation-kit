"""Restart the actual GUI and reopen the remembered project without file dialogs."""
from pathlib import Path
import json
import os
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog,messagebox
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fw_editor as fw

base=Path(os.environ['FW_GAME_DATA']);english=Path(os.environ['FW_MESSAGES'])
original_loop=tk.Tk.mainloop;failures=[];errors=[];opened_dialogs=[];session=[0]
with tempfile.TemporaryDirectory() as temporary:
    temporary=Path(temporary);os.environ['FW_EDITOR_CONFIG']=str(temporary/'config')
    def loop(app,*args,**kwargs):
        def exercise():
            try:
                if session[0]==0:
                    assert str(app.open_last_button.cget('state'))=='disabled'
                    app.read_names(english);app.switch_module('Classes','JID_闘士')
                    hp=app.widgets[0x120][1];hp.delete(0,'end');hp.insert(0,'47')
                    app.save_project();app.export()
                    assert app.preferences.values['last_export']==str(temporary/'mod')
                    assert app.preferences.values['last_project']['module']=='Classes'
                    assert str(app.open_last_button.cget('state'))=='normal'
                else:
                    assert not app.documents
                    assert str(app.open_last_button.cget('state'))=='normal'
                    assert app.open_last_project()
                    assert app.active_module=='Classes'
                    assert app.names_directory==english.resolve()
                    assert app.widgets[0x120][1].get()=='47'
                    assert app.heading.get()=='Gladiator'
                    assert app.project_path==temporary/'project.json'
                    # Each dialog uses the matching remembered directory.
                    app.open_data()
                    assert opened_dialogs[-1]['initialdir']==str(base.resolve())
                    app.load_names()
                    assert opened_dialogs[-1]['initialdir']==str(english.resolve())
                    # A mismatched project is refused before changing the current workspace.
                    before=app.session_state();file=temporary/'project.json';valid=file.read_text(encoding='utf8')
                    damaged=json.loads(valid);damaged['documents']['Job.bin']['source_sha256']='mismatch';file.write_text(json.dumps(damaged))
                    assert not app.open_last_project();assert app.session_state()==before
                    assert 'different source' in errors[-1]
                    file.write_text(valid,encoding='utf8');file.rename(temporary/'moved.json')
                    assert not app.open_last_project();assert app.session_state()==before
                    assert 'not found' in errors[-1]
                    print('PASS: path persistence, startup reopen button, restored game/English/project state, remembered dialogs, and failed reopen preserving the active workspace.')
            except Exception as exc:
                failures.append(exc)
                import traceback;traceback.print_exc()
            finally:app.destroy()
        app.after(350,exercise);original_loop(app,*args,**kwargs)
    def directory(**kw):opened_dialogs.append(kw);return ''
    with patch.object(tk.Tk,'mainloop',loop), \
         patch.object(filedialog,'asksaveasfilename',return_value=str(temporary/'project.json')), \
         patch.object(filedialog,'askdirectory',return_value=str(temporary/'mod')), \
         patch.object(messagebox,'showinfo'), \
         patch.object(messagebox,'showerror',side_effect=lambda title,message,**kw:errors.append(str(message))), \
         patch.object(messagebox,'askyesno',return_value=True):
        sys.argv=['fw_editor.py',str(base)];fw.main()
        if failures:raise failures[0]
        session[0]=1;sys.argv=['fw_editor.py']
        with patch.object(filedialog,'askdirectory',side_effect=directory):fw.main()
    if failures:raise failures[0]
