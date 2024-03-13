import os
import unittest


class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.__script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        super().__init__(*args, **kwargs)

    @property
    def script_path(self):
        return self.__script_path
