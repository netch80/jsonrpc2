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
Provides the Json-RPC2 unit tests runner.
'''

import os
import re
import sys
import logging
import unittest

root_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(root_dir))

from jsonrpc2 import logger

# Turn off logging
logger.setup(logging.CRITICAL + 1)

TEST_MODULE_PREFIX = 'test_'
TEST_MODULE_PATTERN = '(%s.+?)\\.py$' % TEST_MODULE_PREFIX

def main():
    modules = []
    if len(sys.argv) > 1:
        for mdl in sys.argv[1:]:
            modules.append(mdl if mdl.startswith(TEST_MODULE_PREFIX)
                               else TEST_MODULE_PREFIX + mdl)
    else:
        p = re.compile(TEST_MODULE_PATTERN)
        for mdl in os.listdir(root_dir):
            m = p.match(mdl)
            if m:
                modules.append(m.group(1))

    loader = unittest.TestLoader()
    tests = loader.loadTestsFromNames(modules)
    runner = unittest.TextTestRunner()
    result = runner.run(tests)
    sys.exit(not result.wasSuccessful())

if __name__ == "__main__":
    main()
    
