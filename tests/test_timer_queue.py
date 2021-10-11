# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

import math
import numbers
import os.path as op
import random
import sys
import time

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import timer_queue

n = 100
t = 5

# [start, end, interval, count]
count = []
for i in range(n):
    count.append([0, 0, 0, 0])


def fun(i, interval):
    count[i][0] = time.time() + interval
    count[i][2] = interval

    def do_fun():
        count[i][1] = time.time()
        count[i][-1] += 1

    return do_fun


def test_timer_queue():
    tq = timer_queue.TimerQueue()
    tq.start()
    timers = []
    r = random.Random()
    for i in range(n):
        interval = r.randint(1, t)
        timer = tq.add_timer(fun(i, interval), time.time() + interval, interval)
        timers.append(timer)

    time.sleep(t * 2)
    tq.stop()

    for start, end, interval, c in count:
        if isinstance((end - start), numbers.Integral) and isinstance(
            interval, numbers.Integral
        ):
            diff = int(math.fabs(c - (end - start) // interval - 1))
        else:
            diff = int(math.fabs(c - (end - start) / interval - 1))
        assert 0 <= diff <= 1
