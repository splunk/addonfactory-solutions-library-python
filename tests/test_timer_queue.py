import sys
import os.path as op
import time
import random
import json

sys.path.insert(0, op.dirname(op.dirname(op.abspath(__file__))))
from solnlib import timer_queue

n = 10000
count = [[0, 0]] * n


def fun(i, interval):
    count[i][1] = interval

    def do_fun():
        count[i][0] += 1
    return do_fun


def test_timer_queue():
    tq = timer_queue.TimerQueue()
    tq.start()
    timers = []
    for i in range(n):
        interval = random.randint(1, 300)
        timer = tq.add_timer(fun(i, interval), time.time() + interval, interval)
        timers.append(timer)

    print "done"
    time.sleep(300)
    tq.stop()

    with open("a.json", "w") as f:
        json.dump(count, f)


test_timer_queue()
