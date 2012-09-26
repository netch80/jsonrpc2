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
The main module of Json-RPC2 library.
'''

__version__ = '0.1.0'
__copyright__ = 'Copyright (C) 2012 Marcin Lyko'
__license__ = 'LGPL'

__author__ = 'Marcin Lyko'
__contact__ = 'marcin.g.lyko@gmail.com'

from base import loop
from client import JsonRpcClient
from server import JsonRpcIface, JsonRpcServer
from errors import JsonRpcError, JsonRpcInternalError

