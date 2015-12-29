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
parser.add_argument('uri')
args = parser.parse_args()

http = httplib2.Http()
timings = []
for _ in range(0, args.iterations):
    start = time.time()
    http.request(args.uri, headers={'Accept': '*/*'})
    end = time.time()
    timings.append(end - start)
    time.sleep(0.1)

avg = sum(timings) / len(timings)
stdevs = [math.pow(t - avg, 2) for t in timings]
stdev = math.sqrt(sum(stdevs) / len(stdevs))
print('%.4f - %.6f' % (avg, stdev))
