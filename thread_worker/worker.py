from threading import Thread
import time


class Worker(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        #print(type(self._target))
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
    """

    #args transposition
    A = len(args)
    args_tr = zip(*args, *kwargs.values())
    th = [Worker(target=function, args=arg[:A],
                 kwargs=dict(zip(kwargs, arg[A:]))) for arg in args_tr]

#    args_trans_position = list(zip(*args))
#    #kwargs transposition
#    kwargs_collect = [[{key: k} for k in kwargs[key]]
#                      for key in kwargs.keys()]
#    kwarg_list = []
#    kwargs_transposition = list(zip(*kwargs_collect))
#    for tup in kwargs_transposition:
#        kw_dic = {}
#        [kw_dic.update(i) for i in tup]
#        kwarg_list.append(kw_dic)
#
#    #threads list build up
#    th = []
#    for arg in args_trans_position:
#        th.append(Worker(target=function, args=arg,
#                         kwargs=(kwarg_list[args_trans_position.index(arg)]
#                                 if kwargs else None)))
    for t in th:
        t.start()
        time.sleep(delay)
    # return result
    return [i.join() for i in th]


def thread_it(output=False):
    """
    thread_it decorator
    Carefull not killing threads.
    """
    def wrapper(function):
        def inner(*args, **kwargs):

            th = Worker(target=function, args=args,
                        kwargs=kwargs)

            if not output:
                th.start()
                return
            elif output == 'thread':
                return th
            elif output == True:
                th.start()
                return th.join()
        return inner
    return wrapper


