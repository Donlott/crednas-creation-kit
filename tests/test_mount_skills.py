"""Deterministic per-offer traits and compatibility with edited skill lists."""
import unittest
from fw_editor import DataError
from mount_skills import DODGE,MOVE,skill_roll,choose_seeds


class MountSkillTests(unittest.TestCase):
    def test_reference_rolls(self):
        # Native-selector reference vectors, independently checked in CPU tests.
        self.assertEqual([skill_roll(s) for s in (0,1,2,127,255)],
                         [1900725608,128212549,2031342131,7755462,88550109])
        for seed in (-1,256,True,0.0,'0'):
            with self.assertRaises(ValueError):skill_roll(seed)

    def test_both_traits_and_matching_upgrades(self):
        first=[MOVE[0],DODGE[0]];second=[MOVE[1],DODGE[1]]
        seeds=choose_seeds(first,second);self.assertEqual(seeds,{'dodge':1,'move':0})
        for key,trait in [('dodge',DODGE),('move',MOVE)]:
            roll=skill_roll(seeds[key]);self.assertEqual(first[roll%len(first)],trait[0]);self.assertEqual(second[roll%len(second)],trait[1])

    def test_reordered_and_expanded_lists_are_resolved_from_current_data(self):
        for first,second in [([DODGE[0],MOVE[0]],[DODGE[1],MOVE[1]]),
                ([MOVE[0],DODGE[0],'SID_OwnTest'],[MOVE[1],DODGE[1],'SID_OwnTestPlus'])]:
            seeds=choose_seeds(first,second)
            for key,trait in [('dodge',DODGE),('move',MOVE)]:
                roll=skill_roll(seeds[key]);self.assertEqual(first[roll%len(first)],trait[0]);self.assertEqual(second[roll%len(second)],trait[1])

    def test_incompatible_upgrades_or_missing_traits_refused(self):
        for first,second in [([],[]),([MOVE[0]],[MOVE[1]]),([MOVE[0],DODGE[0]],[DODGE[1],MOVE[1]])]:
            with self.assertRaises(DataError):choose_seeds(first,second)


if __name__=='__main__':unittest.main()
