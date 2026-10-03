import unittest
from collections import Counter
from schedulers import schedule, POLICIES
class SchedulingTests(unittest.TestCase):
    def test_lecture_example(self):
        q=[98,183,37,122,14,124,65,67]
        for p,expected in zip(POLICIES,[640,236,236,386]):
            self.assertEqual(schedule(q,53,p)[0],expected)
    def test_empty_and_duplicates(self):
        for p in POLICIES:
            self.assertEqual(schedule([],53,p),(0,[53]))
            self.assertEqual(schedule([53,53],53,p)[0],0)
    def test_service_and_distance(self):
        q=[0,199,0,53,80]
        for p in POLICIES:
            cost,path=schedule(q,53,p)
            self.assertEqual(cost,sum(abs(a-b) for a,b in zip(path,path[1:])))
            self.assertTrue(Counter(q) <= Counter(path[1:]))
    def test_bounds(self):
        with self.assertRaises(ValueError): schedule([200])
if __name__=='__main__': unittest.main()
