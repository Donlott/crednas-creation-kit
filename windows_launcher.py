"""Windowed executable entry point and a non-destructive build health check."""
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

from branding import APP_NAME, APP_SLUG
from platform_support import config_directory


def self_test(report):
    """Check frozen imports, native decompression and the actual startup window."""
    import tkinter as tk
    import fw_editor as fw
    import expanded_ui, expanded_data
    import legion_ui, legion_data
    import deployment_ui, deployment_data
    import shop_ui, shop_data
    import facility_ui, facility_data
    import profile_ui, profile_data
    import aid_ui, appearance_ui, item_ui, learning_ui, progression_ui, skill_ui, supports_ui
    import class_ui, class_creation, class_index, record_expansion
    import person_ui, person_creation, person_index
    import event_ui, event_data, script_inspector, script_ui, script_data, script_bytecode, script_opcodes
    import tutorial_ui, tutorial_data, tutorial_catalog
    import asset_index, appearance_data, item_index, skill_index, reliance_data, localization
    frame = bytes.fromhex('28b52ffd202a510100437265646e612773204372656174696f6e204b69743a20456e676c697368202f20e697a5e69cace8aa9e')
    assert fw.decompress(frame) == (APP_NAME+': English / 日本語').encode('utf8')
    result = {'app_name':APP_NAME, 'version': fw.VERSION, 'platform': sys.platform,
              'frozen': bool(getattr(sys, 'frozen', False)), 'zstandard': True}
    original_loop, original_argv = tk.Tk.mainloop, sys.argv
    previous_config = os.environ.get('FW_EDITOR_CONFIG')
    with tempfile.TemporaryDirectory(prefix='fw-selftest-') as temporary:
        os.environ['FW_EDITOR_CONFIG'] = temporary
        def inspect(app, *args, **kwargs):
            try:
                app.update()
                assert app.title() == f'{APP_NAME} {fw.VERSION}'
                modules = list(app.module_choice.cget('values'))
                assert len(modules) == 16 and 'Shop & Loot' in modules and 'Battle deployment' in modules and 'Legion' in modules and 'Progression & Difficulty' in modules
                result.update(tk=app.tk.call('info', 'patchlevel'), modules=modules)
            finally:
                app.destroy()
        try:
            tk.Tk.mainloop = inspect
            sys.argv = [sys.argv[0]]
            fw.main()
        finally:
            tk.Tk.mainloop, sys.argv = original_loop, original_argv
            if previous_config is None:
                os.environ.pop('FW_EDITOR_CONFIG', None)
            else:
                os.environ['FW_EDITOR_CONFIG'] = previous_config
    Path(report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')


def run():
    # PyInstaller's windowed bootloader has no stdout/stderr. Retain tracebacks.
    log = None
    if sys.stderr is None:
        try:
            directory = config_directory()
            directory.mkdir(parents=True, exist_ok=True)
            log = directory/'application.log'
            sys.stderr = log.open('a', encoding='utf8', buffering=1)
        except OSError:
            log = Path(tempfile.gettempdir())/'crednas-creation-kit-error.log'
            sys.stderr = log.open('a', encoding='utf8', buffering=1)
    if sys.stdout is None:
        sys.stdout = sys.stderr
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
            if len(sys.argv) != 3:
                raise ValueError(f'Usage: {APP_SLUG}.exe --self-test report.json')
            self_test(sys.argv[2])
        else:
            from fw_editor import main
            main()
    except Exception:
        traceback.print_exc()
        if log is not None and '--self-test' not in sys.argv[1:]:
            sys.stderr.flush()
            import tkinter.messagebox
            tkinter.messagebox.showerror(APP_NAME+' could not start',
                                        'Details were saved to:\n'+str(log))
        raise SystemExit(1)


if __name__ == '__main__':
    run()
