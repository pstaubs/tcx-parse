#!/usr/bin/env python
import unittest
import os, site
import numpy as np
site.addsitedir(os.path.join(os.getcwd(), os.pardir))
import tools

class Tests_for_comp(unittest.TestCase):

    def test_flatten_list(self):
        self.assertEqual(tools.closestPoint((10,10), np.array([[1,2],[9,9],[2,2],[5,3],[19,19]])), 1)



unittest.main(exit=False)
