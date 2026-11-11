"""AID token identity, evidence, live ownership and read-only appearance browsing."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from asset_index import AssetIndex, AssetTable, aid_tokens
from fw_editor import Binary,Person,Job,suite_project
from fixture import asset_fixture,person_fixture,job_fixture


class AssetTests(unittest.TestCase):
    def test_tokens_preserve_parentheses_negation_and_full_id(self):
        self.assertEqual(aid_tokens('AID_商人(店)受付, 腰の武器なし'),(('AID_商人(店)受付',False),))
        self.assertEqual(aid_tokens('!AID_A AID_A_CAPE'),(('AID_A',True),('AID_A_CAPE',False)))
        self.assertFalse(aid_tokens('NOT_AID_A'))

    def test_unnamed_rules_definitions_polarity_and_fid_links(self):
        raw=asset_fixture();table=AssetTable('AssetTable.bin',Binary(raw));index=AssetIndex();index.add_table(table);index.refresh_users({})
        self.assertEqual(len(table.groups['アセットテーブル']),3)
        self.assertEqual(index.aids,['AID_ALPHA','AID_ALPHA_CAPE'])
        self.assertEqual(len(index.rows_by_aid['AID_ALPHA']),3)
        self.assertEqual(len(index.definitions['AID_ALPHA']),1)
        self.assertIn(('AID_ALPHA',True),index.mentions_by_row[table.rows[1].key])
        self.assertEqual(table.rows[0].values[0xfc],1.25)
        self.assertEqual(table.rows[0].values[0x118],'#01020304')
        linked=index.linked_rows('AID_ALPHA')
        self.assertIn('FID_Alpha',[r.label for r in linked])
        self.assertEqual(next(r for r in linked if r.label=='FID_Alpha').values[0x20],'VoiceTest')
        self.assertEqual(table.binary.raw,raw)

    def test_directory_side_files_errors_and_source_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'AssetTable.bin').write_bytes(asset_fixture())
            (base/'AssetTable_P0.bin').write_bytes(asset_fixture('AID_PATCH'))
            (base/'Broken.bin').write_bytes(b'not a table')
            person=Person(person_fixture());person.set(person.records[0],person.by_offset[0x278],'AID_SOURCE_ONLY')
            (base/'Person.bin').write_bytes(person.build())
            before={p.name:hashlib.sha256(p.read_bytes()).digest() for p in base.iterdir()}
            index=AssetIndex.load(base,Binary)
            self.assertEqual(len(index.tables),2)
            self.assertIn('AID_SOURCE_ONLY',index.aids)
            self.assertEqual(index.evidence['AID_SOURCE_ONLY'][0].source,'Person.bin')
            self.assertIn('AID_PATCH',index.aids)
            self.assertIn('Broken.bin',[name for name,_ in index.errors])
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).digest() for p in base.iterdir()})

    def test_live_owners_are_separate_from_related_links_and_source_strings(self):
        person=Person(person_fixture());job=Job(job_fixture());a,b=person.records
        person.set(a,person.by_offset[0x278],'AID_ALPHA, other flag')
        person.set(b,person.by_offset[0x268],a.pid)
        job.set(job.records[0],job.by_offset[0x228],'!AID_ALPHA')
        docs={'Characters':person,'Classes':job};before=suite_project(docs)
        index=AssetIndex();index.add_table(AssetTable('AssetTable.bin',Binary(asset_fixture())))
        index.refresh_users(docs)
        self.assertEqual(index.direct_count('AID_ALPHA'),1)
        self.assertTrue(any(u.record==b.pid and u.relationship=='Linked character' for u in index.users['AID_ALPHA']))
        self.assertTrue(any(u.module=='Classes' and u.relationship=='Negated flag' for u in index.users['AID_ALPHA']))
        self.assertEqual(suite_project(docs),before)
        person.set(a,person.by_offset[0x278],'AID_NEW');index.refresh_users(docs)
        self.assertEqual(index.direct_count('AID_ALPHA'),0)
        self.assertEqual(index.direct_count('AID_NEW'),1)
        self.assertIn('AID_NEW',index.aids)
        # Cycles terminate and do not manufacture direct ownership.
        person.set(a,person.by_offset[0x268],b.pid);index.refresh_users(docs)
        self.assertEqual(index.direct_count('AID_NEW'),1)

    def test_source_membership_preserves_multiple_files_and_live_only_aids(self):
        index=AssetIndex()
        index.add_table(AssetTable('AssetTable.bin',Binary(asset_fixture())))
        index.add_table(AssetTable('AssetTable_P0.bin',Binary(asset_fixture())))
        person=Person(person_fixture());person.set(person.records[0],person.by_offset[0x278],'AID_ALPHA, AID_NEW_LIVE')
        docs={'Characters':person};before=suite_project(docs);index.refresh_users(docs)
        self.assertEqual(index.sources_for('AID_ALPHA'),('AssetTable.bin','AssetTable_P0.bin','Person.bin'))
        self.assertEqual(index.sources_for('AID_NEW_LIVE'),('Person.bin',))
        self.assertEqual(index.source_files(),['AssetTable.bin','AssetTable_P0.bin','Person.bin'])
        self.assertEqual(suite_project(docs),before)
        person.changes={};index.refresh_users(docs)
        self.assertFalse(index.sources_for('AID_NEW_LIVE'))
        self.assertEqual(index.sources_for('AID_ALPHA'),('AssetTable.bin','AssetTable_P0.bin'))


DATA=Path(os.environ.get('FW_GAME_DATA','/nonexistent/fw-game-data'))
@unittest.skipUnless((DATA/'AssetTable.bin').is_file(),'Set FW_GAME_DATA for real AID coverage tests.')
class RealAssetTests(unittest.TestCase):
    def test_complete_supplied_asset_layout_and_known_owner_voice_evidence(self):
        index=AssetIndex.load(DATA,Binary)
        docs={'Characters':Person((DATA/'Person.bin').read_bytes()),'Classes':Job((DATA/'Job.bin').read_bytes())}
        before=suite_project(docs);index.refresh_users(docs)
        self.assertEqual(len(index.aids),1093)
        self.assertEqual(len(index.tables),3)
        main=next(t for t in index.tables if t.source=='AssetTable.bin')
        self.assertEqual({group:len(rows) for group,rows in main.groups.items()},
                         {'アセットテーブル':6184,'アセット情報':307,'バリエーション':20,'容姿情報':612,'条件セット':182})
        aid='AID_マジーデ';self.assertEqual(index.direct_count(aid),2)
        self.assertTrue(any(u.record=='PID_マジーデ' and u.relationship=='Direct flag' for u in index.users[aid]))
        voices=[r for r in index.linked_rows(aid) if r.group=='容姿情報']
        self.assertTrue(any(r.values[0x20]=='Maj0' and r.values[0x28]=='095' for r in voices))
        self.assertEqual(suite_project(docs),before)
