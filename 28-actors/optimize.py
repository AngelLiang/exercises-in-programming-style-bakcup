#!/usr/bin/env python
# coding=utf-8
"""
tf-28.py优化
    1、使Python2和Python3都可以运行；
    2、修改被调度的方法的名称，使之拥有`on_`前缀；
    3、修改调度方式，使用`getattr`获取当前类的接口。
"""

import sys
import re
import operator
import string
from threading import Thread, Event

import six
from six.moves.queue import Queue


class ActiveWFObject(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = str(type(self))
        self.queue = Queue()
        # self._stop_evt = False
        self._stop_evt = Event()
        self.start()

    def run(self):
        # while not self._stop_evt:
        while not self._stop_evt.is_set():
            message = self.queue.get()
            self._dispatch(message)
            if message[0] == 'die':
                # self._stop_evt = True
                self._stop_evt.set()

    def send(self, message):
        self.queue.put(message)


class DataStorageManager(ActiveWFObject):
    """ Models the contents of the file """
    _data = ''

    _dispatch_functions = ["init", "send_word_freqs"]

    def _dispatch(self, message):
        # if message[0] == 'init':
        #     self.on_init(message[1:])
        # elif message[0] == 'send_word_freqs':
        #     self.on_process_words(message[1:])
        # else:
        #     # forward
        #     self._stop_word_manager.send(message)

        if message[0] in self._dispatch_functions:
            getattr(self, 'on_' + message[0])(message[1:])
        else:
            # forward
            self._stop_word_manager.send(message)

    def on_init(self, message):
        path_to_file = message[0]
        self._stop_word_manager = message[1]
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def on_process_words(self, message):
        recipient = message[0]
        data_str = ''.join(self._data)
        words = data_str.split()
        for w in words:
            self._stop_word_manager.send(['filter', w])
        self._stop_word_manager.send(['top25', recipient])

    def on_send_word_freqs(self, message):
        self.on_process_words(message)


class StopWordManager(ActiveWFObject):
    """ Models the stop word filter """
    _stop_words = []

    _dispatch_functions = ["init", "filter"]

    def _dispatch(self, message):
        # if message[0] == 'init':
        #     self.on_init(message[1:])
        # elif message[0] == 'filter':
        #     return self.on_filter(message[1:])
        # else:
        #     # forward
        #     self._word_freqs_manager.send(message)

        if message[0] in self._dispatch_functions:
            getattr(self, 'on_' + message[0])(message[1:])
        else:
            # forward
            self._word_freqs_manager.send(message)

    def on_init(self, message):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))
        self._word_freqs_manager = message[0]

    def on_filter(self, message):
        word = message[0]
        if word not in self._stop_words:
            self._word_freqs_manager.send(['word', word])


class WordFrequencyManager(ActiveWFObject):
    """ Keeps the word frequency data """
    _word_freqs = {}

    _dispatch_functions = ["word", "top25"]

    def _dispatch(self, message):
        # if message[0] == 'word':
        #     self.on_increment_count(message[1:])
        # elif message[0] == 'top25':
        #     self.on_top25(message[1:])

        if message[0] in self._dispatch_functions:
            getattr(self, 'on_' + message[0])(message[1:])

    def on_increment_count(self, message):
        word = message[0]
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def on_word(self, message):
        self.on_increment_count(message)

    def on_top25(self, message):
        recipient = message[0]

        # freqs_sorted = sorted(self._word_freqs.iteritems(),
        #                       key=operator.itemgetter(1), reverse=True)
        freqs_sorted = sorted(six.iteritems(self._word_freqs),
                              key=operator.itemgetter(1), reverse=True)
        recipient.send(['top25', freqs_sorted])


class WordFrequencyController(ActiveWFObject):

    _dispatch_functions = ["run", "top25"]

    def _dispatch(self, message):
        # if message[0] == 'run':
        #     self.on_run(message[1:])
        # elif message[0] == 'top25':
        #     self.on_display(message[1:])
        # else:
        #     raise Exception("Message not understood " + message[0])

        if message[0] in self._dispatch_functions:
            getattr(self, 'on_' + message[0])(message[1:])
        else:
            raise Exception("Message not understood " + message[0])

    def on_run(self, message):
        self._storage_manager = message[0]
        self._storage_manager.send(['send_word_freqs', self])

    def on_display(self, message):
        word_freqs = message[0]
        for (w, f) in word_freqs[0:25]:
            print(str(w)+' - '+str(f))
        self._storage_manager.send(['die'])
        # self._stop_evt = True
        self._stop_evt.set()

    def on_top25(self, message):
        self.on_display(message)


def main():
    #
    # The main function
    #
    word_freq_manager = WordFrequencyManager()

    stop_word_manager = StopWordManager()
    stop_word_manager.send(['init', word_freq_manager])

    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        arg = "../input.txt"
    print("arg = '%s'" % arg)

    storage_manager = DataStorageManager()
    storage_manager.send(['init', arg, stop_word_manager])

    wfcontroller = WordFrequencyController()
    wfcontroller.send(['run', storage_manager])

    # Wait for the active objects to finish
    [t.join() for t in [word_freq_manager, stop_word_manager,
                        storage_manager, wfcontroller]]


if __name__ == '__main__':
    main()
