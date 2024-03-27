import os
import re

import tools.archive
import tools.conversation
import tests


class TestConversation(tests.TestCase):
    @staticmethod
    def fixScript(script):
        return script.replace("'Dr. Cat'", "'Dr_ Cat'").replace("'english': 'Ed'", "'english': 'ed'")

    def testOriginal(self):
        for name in ('CONVERSE.A', 'CONVERSE.B'):
            with self.subTest(name=name):
                for index, expected in enumerate(tools.archive.unpack(os.path.join(self.script_path, 'original', name))):
                    if expected is not None:
                        with self.subTest(index=index):
                            script = self.fixScript(tools.conversation.decode(expected, name, index))
                            extracted_name, extracted_index, english = tools.conversation.encode(script, 'english', 1)
                            self.assertEqual(english, expected)
                            self.assertEqual(extracted_name, name)
                            self.assertEqual(extracted_index, index)

    def testUser(self):
        expected = {}
        for name in ('CONVERSE.A', 'CONVERSE.B'):
            expected[name] = tools.archive.unpack(f'{self.script_path}/original/{name}')

        conversations_path = os.path.join(self.script_path, 'conversations')
        for script_name in os.listdir(conversations_path):
            with self.subTest(name=os.path.splitext(script_name)[0]):
                script_path = os.path.join(conversations_path, script_name)
                with open(script_path) as f:
                    script = f.read()

                with self.subTest(language='russian'):
                    tools.conversation.encode(script, 'russian', 2)

                with self.subTest(language='english'):
                    name, index, english = tools.conversation.encode(self.fixScript(script), 'english', 1)
                    self.assertEqual(english, expected[name][index], 'Conversation does not match')
