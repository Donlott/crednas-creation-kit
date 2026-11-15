"""Direct script launches must share model classes with imported tool modules."""
from pathlib import Path
import subprocess
import sys
import unittest


class DirectEntryPointTests(unittest.TestCase):
    def test_direct_script_and_tool_imports_share_models_without_starting_tk(self):
        root=Path(__file__).resolve().parents[1]
        script=r'''
from pathlib import Path
import runpy,sys
entry=Path(sys.argv[1]).resolve();sys.path.insert(0,str(entry.parent));sys.path.insert(0,str(entry.parent/'tests'))
class Checked(Exception):pass

def trace(frame,event,arg):
    if event=='call' and frame.f_code.co_name=='main' and Path(frame.f_code.co_filename).resolve()==entry:
        sys.settrace(None)
        import fw_editor
        assert fw_editor.__dict__ is frame.f_globals, 'Direct entry created a duplicate fw_editor module'
        from fixture import item_fixture,job_fixture,skill_fixture
        from mount_data import source_tables
        docs={'Items':frame.f_globals['Item'](item_fixture()),'Classes':frame.f_globals['Job'](job_fixture()),'Skills':frame.f_globals['Skill'](skill_fixture())}
        assert source_tables(docs)==(docs['Items'],docs['Classes'],docs['Skills'])
        print('PASS direct launch shares table identities and mount dependencies')
        raise Checked()
    return trace
sys.settrace(trace)
try:runpy.run_path(str(entry),run_name='__main__')
except Checked:pass
finally:sys.settrace(None)
'''
        result=subprocess.run([sys.executable,'-c',script,str(root/'fw_editor.py')],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('PASS direct launch',result.stdout)


if __name__=='__main__':unittest.main()
