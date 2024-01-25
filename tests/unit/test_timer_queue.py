#
# Copyright 2023 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import math
import numbers
import random
import time

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
