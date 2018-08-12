#!/usr/bin/env python
# coding=utf-8
"""
练习 28.2 3+1线程
编写另一个版本，使之除出线程之外，只拥有三个主动对象。
"""

import sys
import re
import operator
import string
from threading import Thread
from Queue import Queue


class ActiveWFObject(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = str(type(self))
        self.queue = Queue()
        self._stop = False
        self.start()

    def run(self):
        while not self._stop:
            message = self.queue.get()
            self._dispatch(message)
            if message[0] == 'die':
                self._stop = True

    def send(self, message):
        self.queue.put(message)


class DataStorageManager(ActiveWFObject):
    """ Models the contents of the file """
    _data = ''

    def _dispatch(self, message):
        if message[0] == 'init':
            self._init(message[1:])
        elif message[0] == 'send_word_freqs':
            self._process_words(message[1:])
        else:
            # forward
            self._stop_word_manager.send(message)

    def _init(self, message):
        path_to_file = message[0]
        self._stop_word_manager = message[1]
        with open(path_to_file) as f:
            self._data = f.read()
        pattern = re.compile('[\W_]+')
        self._data = pattern.sub(' ', self._data).lower()

    def _process_words(self, message):
        recipient = message[0]
        data_str = ''.join(self._data)
        words = data_str.split()
        for w in words:
            self._stop_word_manager.send(['filter', w])
        self._stop_word_manager.send(['top25', recipient])


class StopWordManager(ActiveWFObject):
    """ Models the stop word filter """
    _stop_words = []

    def _dispatch(self, message):
        if message[0] == 'init':
            self._init(message[1:])
        elif message[0] == 'filter':
            return self._filter(message[1:])
        else:
            # forward
            self._word_freqs_manager.send(message)

    def _init(self, message):
        with open('../stop_words.txt') as f:
            self._stop_words = f.read().split(',')
        self._stop_words.extend(list(string.ascii_lowercase))
        self._word_freqs_manager = message[0]

    def _filter(self, message):
        word = message[0]
        if word not in self._stop_words:
            self._word_freqs_manager.send(['word', word])


class WordFrequencyManager(ActiveWFObject):
    """ Keeps the word frequency data """
    _word_freqs = {}

    def _dispatch(self, message):
        if message[0] == 'word':
            self._increment_count(message[1:])
        elif message[0] == 'top25':
            self._top25(message[1:])

    def _increment_count(self, message):
        word = message[0]
        if word in self._word_freqs:
            self._word_freqs[word] += 1
        else:
            self._word_freqs[word] = 1

    def _top25(self, message):
        recipient = message[0]
        freqs_sorted = sorted(self._word_freqs.iteritems(),
                              key=operator.itemgetter(1), reverse=True)
        recipient.send(['top25', freqs_sorted])


class WordFrequencyController(ActiveWFObject):

    def _dispatch(self, message):
        if message[0] == 'run':
            self._run(message[1:])
        elif message[0] == 'top25':
            self._display(message[1:])
        else:
            raise Exception("Message not understood " + message[0])

    def _run(self, message):
        self._storage_manager = message[0]
        self._storage_manager.send(['send_word_freqs', self])

    def _display(self, message):
        word_freqs = message[0]
        for (w, f) in word_freqs[0:25]:
            print w, ' - ', f
        self._storage_manager.send(['die'])
        self._stop = True


#
# The main function
#
word_freq_manager = WordFrequencyManager()

stop_word_manager = StopWordManager()
stop_word_manager.send(['init', word_freq_manager])

storage_manager = DataStorageManager()
storage_manager.send(['init', sys.argv[1], stop_word_manager])

wfcontroller = WordFrequencyController()
wfcontroller.send(['run', storage_manager])

# Wait for the active objects to finish
[t.join() for t in [word_freq_manager, stop_word_manager, storage_manager, wfcontroller]]
