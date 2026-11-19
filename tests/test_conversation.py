import os
import re

import tools.archive
import tools.conversation
import tools.file
import tests


class TestConversation(tests.TestCase):
    @staticmethod
    def fixScript(script):
        return script.replace("'Dr. Cat'", "'Dr_ Cat'").replace("'english': 'Ed'", "'english': 'ed'").replace('Snake Charmer', 'Snake_Charmer')

    def testOriginal(self):
        for name in ('CONVERSE.A', 'CONVERSE.B'):
            with self.subTest(name=name):
                for index, expected in enumerate(tools.archive.unpack(tools.file.read(os.path.join(self.script_path, 'original', name)))):
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
            expected[name] = tools.archive.unpack(tools.file.read(f'{self.script_path}/original/{name}'))

        conversations_path = os.path.join(self.script_path, 'conversations')
        for script_name in os.listdir(conversations_path):
            name = os.path.splitext(script_name)[0]
            with self.subTest(name=name):
                script_path = os.path.join(conversations_path, script_name)
                with open(script_path) as f:
                    script = f.read()

                with self.subTest(language='russian', version=2):
                    tools.conversation.encode(script, 'russian', 2)

                with self.subTest(language='english', version=2):
                    tools.conversation.encode(script, 'english', 2, ignore_flow_errors=name in ('Stivius', 'Ybarra'))

                with self.subTest(language='english', version=1):
                    name, index, english = tools.conversation.encode(self.fixScript(script), 'english', 1)
                    self.assertEqual(english, expected[name][index], 'Conversation does not match')

    def testKeywordPrefixes(self):
        # Игра сравнивает со словом из case столько первых букв ввода, сколько их в слове, и берёт первую подходящую
        # ветку после ask(): «кот» перехватывает «котёнок», если ветка «кот» раньше. Русские слова так перехватываться
        # не должны (в оригинале такое есть — run/runo, mu/music, n/name — и остаётся как было). Исправление —
        # ранняя ветка [russian] с длинным словом и переходом в её тело, см. «Dr. Cat.txt».
        case = re.compile(r"^(\s*)case (?:\{'russian': )?'((?:[^'\\]|\\.)*)'\}?:\s*$")
        cyrillic = re.compile('[а-яё]', re.IGNORECASE)
        conversations_path = os.path.join(self.script_path, 'conversations')
        for script_name in sorted(os.listdir(conversations_path)):
            with open(os.path.join(conversations_path, script_name)) as f:
                lines = f.read().split('\n')
            statements = [(n, line.strip()) for n, line in enumerate(lines, 1) if line.strip() and not line.strip().startswith('//')]
            # ask(), после которого сразу проверяются ветки (после choice() вводят одну клавишу).
            asks = [n for (n, s), (_, following) in zip(statements, statements[1:]) if s == 'ask()' and following.startswith('case ')]
            esacs = [n for n, s in statements if s == 'esac']
            blocks = {}
            previous_case = False
            conflicts = []
            for n, line in enumerate(lines, 1):
                match = case.match(line)
                if match:
                    groups = blocks.setdefault(len(match[1]), [])
                    if not previous_case or not groups:
                        groups.append([])
                    groups[-1].append((match[2], n))
                    previous_case = True
                    continue
                previous_case = previous_case and (not line.strip() or line.strip().startswith(('[', '//')))
                if line.strip() == 'esac':
                    groups = blocks.pop(len(line) - len(line.lstrip()), [])
                    for i, group in enumerate(groups):
                        for short, n1 in group:
                            before = [a for a in asks if a < n1]
                            for later in groups[i + 1 :]:
                                for long, n2 in later:
                                    if (
                                        cyrillic.search(long)
                                        and long != short
                                        and long.lower().startswith(short.lower())
                                        and before
                                        and not any(before[-1] < e < n2 for e in esacs)
                                        and not any(k == long for g in groups[: i + 1] for k, _ in g)
                                    ):
                                        conflicts.append(f'{short!r} ({n1}) перехватывает {long!r} ({n2})')
            with self.subTest(name=script_name):
                self.assertEqual(conflicts, [])
