import os

import tools.archive
import tools.conversation
import tests


class TestConversation(tests.TestCase):
    def testRead(self):
        for name in ('CONVERSE.A', 'CONVERSE.B'):
            with self.subTest(name=name):
                for index, item in enumerate(tools.archive.unpack(os.path.join(self.script_path, 'original', name))):
                    if item is not None:
                        with self.subTest(index=index):
                            tools.conversation.decode(item)
