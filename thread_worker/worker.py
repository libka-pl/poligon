from threading import Thread
import time

class Worker(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):        
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return


def thread_it_multi(function, delay: int, *args: list, **kwargs: dict[str, list]) -> list:

    """
    :param function: Function to be executed
    :param delay: Duration of delay between start each thread
    :param args: Optional arguments for the provided function [enter as List]
    :param kwargs: Optional arguments for the provided function [enter as key=[List of dictionaries]
    :return:  function return [List]

    Useful function for executing functions in threads
     - select function
     - choose delay when needed or enter 0
     - provide arguments as Lists
       ex. thread_it_multi(function, 0, [param], key=[Value list]
       a=[11,21,28,41]
       b=[12,22,30,42]
       d=[13,15,33,43]
       thread_it_multi(foo, 0, a, b, c=d)

    delay  must be provided - 0 if no delay required ]
    List of args and kwargs must be same lenght !
    args and kwargs are transpositioned before preparing threads to start

    Credits to rysson for advice
    """

    #args transposition
    A = len(args)
    args_tr = zip(*args, *kwargs.values())
    th = [Worker(target=function, args=arg[:A],
                 kwargs=dict(zip(kwargs, arg[A:]))) for arg in args_tr]


    for t in th:
        t.start()
        time.sleep(delay)    
    return [i.join() for i in th]


def thread_it(start=True):
    """
    thread_it decorator

    :param output: optional [False, 'thread', True]
    When no output arg provided - Runs function in background and continue main script
    worker is returned for optional further handling
    :return:  if output = True - returns thread worker for further handle

    ex.1
    @thread_it(True)
    def foo(x):
        time.sleep(1)   # long time work
        return x**2

    workers = [foo(x) for x in range(10)]
    results = [w.join() for w in workers]

    ex.2 - notice that no brackets are necessary
    @thread_it
    def bar(y):
        ...
        #do smth with y
        return y + 15

    bar(y)
    or
    result = bar(y)

    """
    def wrapper(function):
        def inner(*args, **kwargs):

            th = Worker(target=function, args=args,
                        kwargs=kwargs)

            if start:
                th.start()
                return th
            return th

        return inner
    if callable(start):
        func, start = start, True
        return wrapper(func)
    return wrapper


