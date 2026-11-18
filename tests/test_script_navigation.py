"""Regression checks for pending edits and displayed values, without requiring a display."""
from pathlib import Path
import tempfile
from types import MethodType,SimpleNamespace
import unittest
from unittest.mock import Mock

from script_data import ScriptDocument,script_paths
from script_ui import ScriptEditor
from test_script_editor import fixture


class Tree:
    def __init__(self,items,selected=()):
        self.items={str(i):None for i in items};self.selected=tuple(map(str,selected))
    def exists(self,key):return key in self.items
    def selection(self):return self.selected
    def selection_set(self,key):self.selected=(str(key),)
    def selection_remove(self,*keys):self.selected=tuple(k for k in self.selected if k not in keys)
    def see(self,key):pass
    def item(self,key,**kwargs):
        if 'values' in kwargs:self.items[key]=kwargs['values']
        return self.items[key]


class Value:
    def __init__(self,text):self.text=text
    def get(self):return self.text
    def set(self,text):self.text=text


def editor():
    doc=ScriptDocument(fixture(),'Script/cmdbtl/Test.bin')
    result=SimpleNamespace(doc=doc,fi=0,ii=None,ci=None,pending=None,
        value=Value(''),baseline='',translation=Value('translated'),mode=Value('Unsigned bits'),
        code_tree=Tree(range(7)),constant_tree=Tree(range(2)),function_tree=Tree(range(1)),
        error=Mock(),show_form=Mock(),update_notice=Mock(),filter_constants=Mock(),
        restore_selection=ScriptEditor.restore_selection)
    for name in ('commit','literal_bits','instruction_values','refresh_string_uses','restore','select_instruction','select_constant','select_function'):
        setattr(result,name,MethodType(getattr(ScriptEditor,name),result))
    return result


class ScriptNavigationTests(unittest.TestCase):
    def test_invalid_number_keeps_selection_and_edit_on_original_instruction(self):
        ui=editor();ui.ii=1;ui.pending=('instruction',0,1);ui.baseline='5';ui.value.set('not a number')
        ui.code_tree.selection_set('2');before=ui.doc.snapshot_edits()
        ui.select_instruction()
        self.assertEqual(ui.code_tree.selection(),('1',));self.assertEqual(ui.pending,('instruction',0,1))
        self.assertEqual(ui.doc.snapshot_edits(),before);ui.show_form.assert_not_called();ui.error.assert_called_once()
        ui.value.set('19');self.assertTrue(ui.commit())
        self.assertEqual(ui.doc.instruction(0,1)[1],(19,))
        self.assertNotIn((0,2),ui.doc.instructions)

    def test_invalid_string_keeps_selection_on_original_constant(self):
        ui=editor();ui.ci=0;ui.pending=('string',0);ui.baseline='SharedName';ui.value.set('bad\0text')
        ui.constant_tree.selection_set('1');ui.select_constant()
        self.assertEqual(ui.constant_tree.selection(),('0',));self.assertEqual(ui.pending,('string',0))
        self.assertFalse(ui.doc.modified);ui.show_form.assert_not_called();ui.error.assert_called_once()

    def test_invalid_edit_clears_other_pane_selection_without_changing_pending_value(self):
        ui=editor();ui.ii=1;ui.pending=('instruction',0,1);ui.baseline='5';ui.value.set('invalid')
        ui.constant_tree.selection_set('1');ui.select_constant()
        self.assertEqual(ui.constant_tree.selection(),());self.assertEqual(ui.pending,('instruction',0,1))

    def test_invalid_edit_does_not_highlight_a_different_filtered_function(self):
        ui=editor();ui.ii=1;ui.pending=('instruction',0,1);ui.baseline='5';ui.value.set('invalid')
        ui.function_tree=Tree([1],[1]);ui.select_function()
        self.assertEqual(ui.function_tree.selection(),());self.assertEqual(ui.fi,0)
        self.assertEqual(ui.pending,('instruction',0,1));ui.show_form.assert_not_called()

    def test_string_apply_and_restore_refresh_instruction_text_without_losing_selection(self):
        ui=editor();ui.ci=0;ui.pending=('string',0);ui.baseline='SharedName';ui.value.set('PID_Replacement')
        ui.code_tree.selection_set('0');ui.constant_tree.selection_set('0')
        self.assertTrue(ui.commit())
        self.assertEqual(ui.code_tree.item('0')[-1],'string[0]: PID_Replacement')
        self.assertEqual(ui.code_tree.selection(),('0',));self.assertEqual(ui.constant_tree.selection(),('0',))
        ui.restore()
        self.assertEqual(ui.code_tree.item('0')[-1],'string[0]: SharedName');self.assertFalse(ui.doc.modified)

    def test_inverted_condition_retains_displayed_branch_destination(self):
        ui=editor();ui.ii=3;ui.pending=('instruction',0,3);ui.baseline='JZ';ui.value.set('JNZ')
        before=ui.instruction_values(0,3)[-1];self.assertEqual(before,'branch → #5 (target fixed)')
        self.assertTrue(ui.commit())
        row=ui.code_tree.item('3');self.assertEqual(row[1],'JNZ');self.assertEqual(row[-1],before)

    def test_script_discovery_includes_raw_sources_and_prefers_compressed_counterparts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('cmdbtl/First.bin','cmdbtl/Both.bin','cmdbtl/Both.bin.zst','hub/Last.bin.zst'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
            (root/'not-a-file.bin').mkdir()
            self.assertEqual([p.relative_to(root).as_posix() for p in script_paths(root)],
                ['cmdbtl/Both.bin.zst','cmdbtl/First.bin','hub/Last.bin.zst'])
            self.assertEqual(script_paths(root/'missing'),())
