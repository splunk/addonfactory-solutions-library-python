"""
A simple thread safe timer queue implementation which
has O(logn) time complexity
"""


import threading
import Queue
import traceback
import logging
from time import time


class Timer(object):
    """
    Timer wraps the callback and timestamp related attributes
    """

    _ident = 0
    _lock = threading.Lock()

    def __init__(self, callback, when, interval, ident=None):
        self._callback = callback
        self._when = when
        self._interval = interval

        if ident is not None:
            self._id = ident
        else:
            with Timer._lock:
                self._id = Timer._ident + 1
                Timer._ident = Timer._ident + 1

    def get_interval(self):
        return self._interval

    def set_interval(self, interval):
        self._interval = interval

    def get_expiration(self):
        return self._when

    def set_initial_due_time(self, when):
        self._when = when

    def update_expiration(self):
        self._when += self._interval

    def __cmp__(self, other):
        if other is None:
            return 1

        self_k = (self.get_expiration(), self.ident())
        other_k = (other.get_expiration(), other.ident())

        if self_k == other_k:
            return 0
        elif self_k < other_k:
            return -1
        else:
            return 1

    def __eq__(self, other):
        return isinstance(other, Timer) and (self.ident() == other.ident())

    def __call__(self):
        self._callback()

    def ident(self):
        return self._id


TEARDOWN_SENTINEL = None


class TimerQueue(object):
    """
    A timer queue implementation, runs a separate thread to handle timers
    Note: to effectively use this timer queue, the timer callback should be
    short, otherwise it will cause other timers's delay execution.
    A typical use scenario in production is that the timers are just a simple
    functions which inject themselvies to a task queue and then they are
    picked up by a threading/process pool to execute, as shows below:

    Timers --enqueue---> TimerQueue --------expiration-----------
                                                                |
                                                                |
                                                               \|/
    Threading/Process Pool <---- TaskQueue <--enqueue-- Timers' callback (nonblocking)

    Usage::
           >>> from solnlib import time_queue
           >>> tq = time_queue.TimerQueue()
           >>> tq.start()
           >>> t = tq.add_timer(my_func, time.time(), 10)
           >>> # do other stuff
           >>> tq.stop()
    """

    import sortedcontainers as sc

    def __init__(self):
        self._timers = TimerQueue.sc.SortedSet()
        self._cancelling_timers = {}
        self._lock = threading.Lock()
        self._wakeup_queue = Queue.Queue()
        self._thr = threading.Thread(target=self._check_and_execute)
        self._thr.daemon = True
        self._started = False

    def start(self):
        """
        Start the timer queue
        """

        if self._started:
            return
        self._started = True

        self._thr.start()
        logging.info("TimerQueue started.")

    def stop(self):
        if not self._started:
            return
        self._started = True

        self._wakeup(TEARDOWN_SENTINEL)
        self._thr.join()

    def add_timer(self, callback, when, interval):
        """ Add timer to the queue

        :param callback: arbitrary callable
        :param when: the first expiration time, seconds since epoch
        :param interval: timer interval, if equals 0, one time timer, otherwise
            the timer will be periodically executed
        :returns: a Timer object which should not be manipulated directly by
            clients. Used to delete/update the timer
        """

        timer = Timer(callback, when, interval)
        with self._lock:
            self._timers.add(timer)
        self._wakeup()
        return timer

    def remove_timer(self, timer):
        """ Remove timer from the queue.

        :param timer: Timer object which is returned by ``TimerQueue.add_timer``
        """

        with self._lock:
            try:
                self._timers.remove(timer)
            except ValueError:
                logging.info("Timer=%s is not in queue, move it to cancelling "
                             "list", timer.ident())
            else:
                self._cancelling_timers[timer.ident()] = timer

    def _check_and_execute(self):
        wakeup_queue = self._wakeup_queue
        while 1:
            (next_expired_time, expired_timers) = self._get_expired_timers()
            for timer in expired_timers:
                try:
                    # Note, please make timer callback effective/short
                    timer()
                except Exception:
                    logging.error(traceback.format_exc())

            self._reset_timers(expired_timers)

            # Calc sleep time
            if next_expired_time:
                now = time()
                if now < next_expired_time:
                    sleep_time = next_expired_time - now
                else:
                    sleep_time = 0.1
            else:
                sleep_time = 1

            try:
                wakeup = wakeup_queue.get(timeout=sleep_time)
                if wakeup is TEARDOWN_SENTINEL:
                    break
            except Queue.Empty:
                pass
        logging.info("TimerQueue stopped.")

    def _get_expired_timers(self):
        next_expired_time = 0
        now = time()
        expired_timers = []
        with self._lock:
            for timer in self._timers:
                if timer.get_expiration() <= now:
                    expired_timers.append(timer)

            if expired_timers:
                del self._timers[:len(expired_timers)]

            if self._timers:
                next_expired_time = self._timers[0].get_expiration()
        return (next_expired_time, expired_timers)

    def _reset_timers(self, expired_timers):
        has_new_timer = False
        with self._lock:
            cancelling_timers = self._cancelling_timers
            for timer in expired_timers:
                if timer.ident() in cancelling_timers:
                    logging.INFO("Timer=%s has been cancelled", timer.ident())
                    continue
                elif timer.get_interval():
                    # Repeated timer
                    timer.update_expiration()
                    self._timers.add(timer)
                    has_new_timer = True
            cancelling_timers.clear()

        if has_new_timer:
            self._wakeup()

    def _wakeup(self, something="not_None"):
        self._wakeup_queue.put(something)
