# coding: utf-8
import os
import requests

API_TOKEN = os.environ.get('CIRCLECI_API_KEY')
EMOJI_SUCCESS = u'✅'
EMOJI_FAIL = u'❌'
EMOJI_QUEUE = u'⏳'

def status_to_emoji(status):
    return {
        'success': EMOJI_SUCCESS,
        'failed': EMOJI_FAIL,
        'queued': EMOJI_QUEUE
    }.get(status, status)

builds_response = requests.get(
    'https://circleci.com/api/v1/project/%s/%s'
    '?circle-token=%s&limit=20&offset=5&filter=completed' % (
        'fastmonkeys',
        'pelsu',
        API_TOKEN
    ),
    headers={
        'Accept': 'application/json'
    }
)
data = builds_response.json()
print 'Your test builds on %s/%s:' % (
    'fastmonkeys',
    'pelsu'
)
print
for build in data:
    print build['branch']
    print '%s  %s' % (
        status_to_emoji(build['status']),
        build['subject']
    )

    if build['status'] == 'failed':
        build_response = requests.get(
            'https://circleci.com/api/v1/project/'
            '%s/%s/%s?circle-token=%s' % (
                'fastmonkeys',
                'pelsu',
                build['build_num'],
                API_TOKEN
            ),
            headers={
                'Accept': 'application/json'
            }
        )
        one_build_data = build_response.json()
        for step in one_build_data['steps']:
            for action in step['actions']:
                if action['exit_code'] > 0:
                    output_response = requests.get(action['output_url'])
                    print "\n"*10
                    message = output_response.json()[0]['message']
                    lines = message.split("\n")
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if line.startswith('_') and line.endswith('_'):
                            next_line = lines[i+1].strip()
                            # tests/rescue_plan/document/test_03_kohteen_perustiedot.py:683: in test_renders_heating_types
                            filename, line, method = next_line.split(':')
                            method = method.split(' ')[-1]
                            print "Filename: %r" % filename
                            print "Line: %r" % line
                            print "Method: %r" % method

                    #print action
            #print step['name']
        #import pprint
        #pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(one_build_data)
        #print build_response.json()
        break


#print build_response.json()


# Usage:
#
# amiokay status
# amiokay prioritize
# amiokay cancel

# amiokay status
# 1.
