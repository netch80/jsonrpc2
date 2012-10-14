# This file is part of Json-RPC2.
#
# Copyright (C) 2012 Marcin Lyko
# All rights reserved.
#
# Json-RPC2 is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Json-RPC2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Json-RPC2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
Defintion of a logger for Json-RPC classes and functions.
'''

import logging

LOG_FORMAT = '%(asctime)s [%(name)s] %(filename)s:%(lineno)d - %(message)s'

_logger = None

def debug(*args, **kwargs):
    '''
    Logs a message with severity 'DEBUG' on the logger.
    '''
    if _logger is None:
        return
    _logger.debug(*args, **kwargs)

def info(*args, **kwargs):
    '''
    Logs a message with severity 'INFO' on the logger.
    '''
    if _logger is None:
        return
    _logger.info(*args, **kwargs)

def warning(*args, **kwargs):
    '''
    Logs a message with severity 'WARNING' on the logger.
    '''
    if _logger is None:
        return
    _logger.warning(*args, **kwargs)

def error(*args, **kwargs):
    '''
    Logs a message with severity 'ERROR' on the logger.
    '''
    if _logger is None:
        return
    _logger.error(*args, **kwargs)

def exception(*args, **kwargs):
    '''
    Logs a message with severity 'ERROR' on the logger, with current exception
    information.
    '''
    if _logger is None:
        return
    _logger.exception(*args, **kwargs)

def critical(*args, **kwargs):
    '''
    Logs a message with severity 'CRITICAL' on the logger.
    '''
    if _logger is None:
        return
    _logger.critical(*args, **kwargs)


def setup(level=None):
    '''
    Sets up a logger instance with the given logging level.
    '''
    global _logger

    if _logger:
        return

    if level is None:
        level = logging.INFO

    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    _logger = logging.getLogger('Json-RPC2')
    _logger.addHandler(handler)
    _logger.setLevel(level)

