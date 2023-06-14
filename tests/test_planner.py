import unittest

from spec import *

class Test(unittest.TestCase):
    def test_spec_from_scratch(self):
        s = Spec(spec_version=(1,0), actions=[])