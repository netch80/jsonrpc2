#!/usr/bin/env python
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
Provides the Json-RPC2 examples runner.
'''

import os
import sys
import imp
import logging
import optparse

root_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(root_dir))

import jsonrpc2

def run(client=None, server=None):
    '''
    Runs the given Json-RPC example client or server.
    '''
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s')

    example_dir = os.path.join(root_dir, client or server)
    module_name = 'client' if client else 'server'
    module = imp.load_module(module_name,
                             *imp.find_module(module_name, [example_dir]))

    logging.info('Run %s: %s' % (module_name, client or server))
    module.run()


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-c', '--client', dest='client', type=str, nargs=1,
                      help='runs the specified Json-RPC example client')
    parser.add_option('-s', '--server', dest='server', type=str, nargs=1,
                      help='runs the specified Json-RPC example server')

    opts, args = parser.parse_args()

    if opts.client is None and opts.server is None:
        parser.error('--client or --server option must be specified')

    example_dir = opts.client or opts.server
    if not os.path.isdir(os.path.join(root_dir, example_dir)):
        parser.error('example does not exist: %s' % example_dir)

    run(opts.client, opts.server)

