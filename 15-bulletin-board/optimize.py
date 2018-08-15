#!/usr/bin/env python
# coding=utf-8
"""
usage:

python optimize.py ..\input.txt

"""

import sys
import re
import operator
import string
from functools import wraps

try:
    import six
except:
    print("please install six")
    print("pip install six")
    exit(1)

###############################################################################
# The event management substrate


class EventManager(object):
    """
    事件管理器
    """

    def __init__(self):
        # type: {'event_type': [handler1 ,handler2]}
        self._subscriptions = {}

    def subscribe(self, event_type, handler):
        """
        订阅
        @param event_type: 事件类型
        @param handler: 事件处理器
        """
        if event_type in self._subscriptions:
            self._subscriptions[event_type].append(handler)
        else:
            self._subscriptions[event_type] = [handler]

    def publish(self, event, args=None):
        """
        发布
        @param event: 事件
        @param args: 需要传递的参数
        """
        event_type = event   # 获取事件类型

        if event_type in self._subscriptions:
            for h in self._subscriptions[event_type]:
                h(event, args)


def event_handle(func):
    """
    event_handle装饰器，用于标识事件处理的函数
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        IS_EVENT_HANDLE = True
        return func(*args, **kwargs)
    return decorated_view

###############################################################################
# The application entities


class DataStorage(object):
    """ Models the contents of the file """

    def __init__(self, event_manager):
        self._event_manager = event_manager
        self._event_manager.subscribe('load', self.load)
        self._event_manager.subscribe('start', self.produce_words)

    @event_handle
    def load(self, event, args):
        path_to_file = args[0]
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    @event_handle
    def produce_words(self, event, args):
        data_str = ''.join(self._data)
        for w in data_str.split():
            self._event_manager.publish('word', args=(w,))
        self._event_manager.publish('eof')


class StopWordFilter(object):
    """ Models the stop word filter """

    def __init__(self, event_manager):
        self._stop_words = []
        self._event_manager = event_manager
        self._event_manager.subscribe('load', self.load)
        self._event_manager.subscribe('word', self.is_stop_word)

    @event_handle
    def load(self, event, args):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))

    @event_handle
    def is_stop_word(self, event, args):
        word = args[0]
        if word not in self._stop_words:
            self._event_manager.publish('valid_word', args=(word,))


class WordFrequencyCounter(object):
    """ Keeps the word frequency data """

    def __init__(self, event_manager):
        self._word_freqs = {}
        self._event_manager = event_manager
        self._event_manager.subscribe('valid_word', self.increment_count)
        self._event_manager.subscribe('print', self.print_freqs)

    @event_handle
    def increment_count(self, event, args):
        word = args[0]
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    @event_handle
    def print_freqs(self, event, args):
        # python2
        # word_freqs = sorted(self._word_freqs.iteritems(),
        #                     key=operator.itemgetter(1), reverse=True)

        # 兼容python2/3
        word_freqs = sorted(six.iteritems(self._word_freqs),
                            key=operator.itemgetter(1), reverse=True)
        for (w, c) in word_freqs[0:25]:
            print(str(w)+' - ' + str(c))


class WordFrequencyApplication(object):
    def __init__(self, event_manager):
        self._event_manager = event_manager
        self._event_manager.subscribe('run', self.run)
        self._event_manager.subscribe('eof', self.stop)

    @event_handle
    def run(self, event, args):
        path_to_file = args[0]
        self._event_manager.publish('load', args=(path_to_file,))
        self._event_manager.publish('start')

    @event_handle
    def stop(self, event, args):
        self._event_manager.publish('print')

###############################################################################
# main


def main():
    em = EventManager()
    DataStorage(em), StopWordFilter(em), WordFrequencyCounter(em)
    WordFrequencyApplication(em)
    em.publish('run', args=(sys.argv[1],))


if __name__ == '__main__':
    main()
