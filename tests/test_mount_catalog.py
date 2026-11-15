"""Synthetic mount discovery and configurable catalog/native-table validation."""
from types import SimpleNamespace
import struct
import unittest
from fixture import grouped_fixture
from fw_editor import Binary,DataError
from mount_catalog import catalog,variant_seeds,default_price
from mount_skills import skill_roll
import mount_native as native


def fixture(first=None,second=None):
    a='SID_CCK_TestA';b='SID_CCK_TestB';ap=a+'＋';bp=b+'＋'
    fields=[('種類','u8',1,0x20),('名前','string',8,0x28),('固有','u8',1,0x6c),('価値','u8',1,0x6e),
            ('騎乗スキル1段階','data[]',16,0x70),('騎乗スキル2段階','data[]',16,0x80)]
    used={off+i for n,k,size,off in fields for i in range(size)}
    for at in range(0x21,336):
        if len(fields)==131:break
        if at not in used:fields.append(('CCK Test '+str(at),'u8',1,at))
    rows=[('RID_CCK_None',{}),('RID_CCK_Synthetic',{0x20:1,0x28:'CCK_TEST_MOUNT',0x6e:2,0x70:first or [a,b],0x80:second or [ap,bp]}),
          ('RID_CCK_Unique',{0x20:5,0x28:'CCK_TEST_UNIQUE',0x6c:1,0x6e:4,0x70:[a],0x80:[ap]})]
    job=Binary(grouped_fixture([('乗り物',336,fields,rows)]));names={'CCK_TEST_MOUNT':'Test Mount','CCK_TEST_UNIQUE':'Test Unique','TEST_A':'Test A','TEST_B':'Test B'}
    records={sid:SimpleNamespace(name='TEST_A' if sid in (a,ap) else 'TEST_B',suffix='MID_Plus' if sid.endswith('＋') else '') for sid in (a,b,ap,bp)}
    skills=SimpleNamespace(by_pid=records,by_offset={0x20:'name',0x28:'suffix'},value=lambda row,field:getattr(row,field))
    return job,skills,names


class CatalogTests(unittest.TestCase):
    def test_discovers_real_mounts_and_traits_excludes_placeholder(self):
        job,skills,names=fixture();rows=catalog(job,skills,names)
        self.assertEqual(len(rows),3);self.assertEqual([r.mount_name for r in rows],['Test Mount','Test Mount','Test Unique'])
        self.assertEqual([r.unique for r in rows],[False,False,True]);self.assertEqual(rows[0].upgrade_name,'Test A+')
        self.assertEqual(len({r.iid for r in rows}),3)
        for row in rows:
            self.assertTrue(row.iid.startswith('IID_CCK_BuyMount_'));self.assertIn(row.skill_name,row.label)

    def test_stable_ids_survive_skill_order_changes(self):
        original=catalog(*fixture());changed=catalog(*fixture(['SID_CCK_TestB','SID_CCK_TestA'],['SID_CCK_TestB＋','SID_CCK_TestA＋']))
        self.assertEqual({(r.rid,r.skill,r.upgrade):r.iid for r in original},{(r.rid,r.skill,r.upgrade):r.iid for r in changed})

    def test_missing_names_or_skills_refused(self):
        job,skills,names=fixture();names.pop('CCK_TEST_MOUNT')
        with self.assertRaises(DataError):catalog(job,skills,names)
        job,skills,names=fixture();skills.by_pid.pop('SID_CCK_TestA')
        with self.assertRaises(DataError):catalog(job,skills,names)

    def test_only_reachable_pairs_and_one_stage_lists(self):
        for first,second in [(['a','b','c'],['a+','b+','c+']),(['a','b'],['x','y','z']),([],['a+']),(['a'],[])]:
            rows=variant_seeds(first,second);expected={(first[skill_roll(s)%len(first)] if first else '',second[skill_roll(s)%len(second)] if second else '') for s in range(256)}
            self.assertEqual({(a,b) for a,b,s in rows},expected)
        self.assertEqual(variant_seeds([],[]),[])

    def test_default_movement_and_canto_prices(self):
        self.assertEqual(default_price(1,'SID_共なる喚起'),1000)
        self.assertEqual(default_price(1,'SID_共なる疾走'),3000)
        self.assertEqual(default_price(3,'SID_飛行再移動'),12000)
        self.assertEqual(default_price(255,'SID_再移動'),65535)


class NativeCatalogValidationTests(unittest.TestCase):
    def test_count_limit_duplicate_indexes_and_invalid_rows(self):
        for rows in [[],[(1,6,0,False)]*2,[(1,0,0,False)],[(1,6,256,False)],[(1,6,0,2)],[(1,6,0,False)]*257]:
            with self.subTest(rows=rows[:2]),self.assertRaises(ValueError):native.catalog_records(rows)
        records=native.catalog_records([(i+1,1+i%255,i,False) for i in range(256)])
        self.assertLess(native.CAVE+len(records[-1][1]),0x1a46000)
        table=records[-1][1][native.TABLE-native.CAVE:]
        self.assertEqual(struct.unpack_from('<HBBI',table,255*8),(256,1,255,0))


if __name__=='__main__':unittest.main()
