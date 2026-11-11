"""Display-only translation rules, independent of proprietary game files."""
import unittest

from localization import Translator


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.names = {'MPID_A': 'Alpha', 'MPID_B': 'Beta', 'MJID_A': 'Fighter',
                      'MSID_A': 'Named skill'}
        self.catalog = {'PID_アルファ': 'MPID_A', 'PID_ベータ': 'MPID_B',
                        'JID_闘士': 'MJID_A', 'SID_技能': 'MSID_A'}
        self.t = Translator(self.names, self.catalog)

    def test_exact_game_names_and_cross_table_aliases(self):
        self.assertEqual(self.t.resolve('PID_アルファ').text, 'Alpha')
        self.assertEqual(self.t.resolve('MPID_B').text, 'Beta')
        self.assertEqual(self.t.resolve('JID_闘士').source, 'English text')
        self.assertEqual(self.t.resolve('AID_ベータ').text, 'Appearance: Beta')
        self.assertEqual(self.t.resolve('LID_アルファ').text, 'Learning: Alpha')

    def test_identifier_explanations_and_unknowns_are_distinguished(self):
        result = self.t.resolve('SID_ブレイズ可能_アルファ')
        self.assertEqual(result.text, 'Skill: Blaze enabled / Alpha')
        self.assertEqual(result.source, 'Glossary')
        self.assertEqual(self.t.resolve('SID_未知語彙').source, 'Untranslated')
        self.assertEqual(self.t.resolve('AID_アルファ_未知語彙').source, 'Partial glossary')
        self.assertIn('未知語彙', self.t.resolve('AID_アルファ_未知語彙').text)
        self.assertEqual(self.t.resolve('AID_アルファ３部').text, 'Appearance: Alpha Part 3')
        self.assertEqual(self.t.resolve('Dit0').text, 'Dit0')
        self.assertEqual(self.t.resolve('').source, 'Empty')

    def test_custom_exact_and_word_glossary_refresh(self):
        self.t.resolve('AID_未知語彙')  # Cache a miss first.
        self.t.overrides = {'未知語彙': 'New appearance', 'PID_アルファ': 'Custom name'}
        self.t.rebuild()
        self.assertEqual(self.t.resolve('AID_未知語彙').text, 'Appearance: New appearance')
        self.assertEqual(self.t.resolve('PID_アルファ').text, 'Custom name')
        self.assertEqual(self.t.resolve('PID_アルファ').source, 'Custom')
        self.t.overrides = {}
        self.t.names['MPID_A'] = 'Renamed Alpha'
        self.t.rebuild()
        self.assertEqual(self.t.resolve('AID_アルファ').text, 'Appearance: Renamed Alpha')

    def test_conflicting_aliases_are_not_guessed(self):
        catalog = dict(self.catalog, JID_アルファ='MJID_A')
        t = Translator(self.names, catalog)
        self.assertEqual(t.resolve('PID_アルファ').text, 'Alpha')
        self.assertEqual(t.resolve('AID_アルファ').source, 'Untranslated')


if __name__ == '__main__':
    unittest.main()
