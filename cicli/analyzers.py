import re


class PyTestErrorAnalyzer(object):
    def __call__(self, message):
        failed_tests = []
        sections = message.split("\r\n\r\n")
        for i, section in enumerate(sections):
            section = section.strip()
            if re.search(r':([0-9]+):', section):
                lines = section.split("\n")
                failfilename = sections[i-1].split("\n")[-1].split(" ")[0]
                filename, linenumber, _ = lines[1].strip().split(':')
                classname, method = re.findall(r'_* *([^ ]+) *_*', lines[0])[0].split('.')
                failed_tests.append({
                    'filename': failfilename,
                    'fail_filename': filename,
                    'fail_line': linenumber,
                    'class': classname,
                    'method': method
                })
        return failed_tests

    @staticmethod
    def check(data):
        return data['command'].split(' ')[0] == 'py.test'

    @staticmethod
    def run_command(data):
        return (
            data['command'].split(' ') +
            list(set([x['filename'] for x in data['failed_tests']])) +
            ['-k'] +
            [' or '.join(
                ['%(class)s and %(method)s' % x for x in data['failed_tests']]
            )]
        )
