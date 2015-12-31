# -*- coding: utf-8 -*-
"""
##################
Timing test module
##################

Requires ``httplib2``. Then requests a given URL n times and calculates
average and standard deviation.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import argparse
import httplib2
import math
import time

parser = argparse.ArgumentParser()
parser.add_argument('--iterations', default=50)
parser.add_argument('-l', '--login')
parser.add_argument('-e', '--email')
parser.add_argument('-p' , '--password')
parser.add_argument('uri')
args = parser.parse_args()

http = httplib2.Http()
http.follow_redirects=False
if args.login and args.email and args.password:
    response, data = http.request(args.login,
                                  method='POST',
                                  headers={'Accept': '*/*',
                                           'Content-type': 'application/x-www-form-urlencoded'},
                                  body='email=%s&password=%s' % (args.email, args.password))
    cookie = response['set-cookie']
else:
    cookie = None
http.follow_redirects=True
timings = []
for _ in range(0, args.iterations):
    start = time.time()
    headers = {'Accept': '*/*'}
    if cookie:
        headers['Cookie'] = cookie
    http.request(args.uri, headers=headers)
    end = time.time()
    timings.append(end - start)
    time.sleep(0.1)

avg = sum(timings) / len(timings)
stdevs = [math.pow(t - avg, 2) for t in timings]
stdev = math.sqrt(sum(stdevs) / len(stdevs))
print('%.4f - %.6f' % (avg, stdev))
