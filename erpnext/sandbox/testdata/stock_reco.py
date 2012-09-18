# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from webnotes.model.doc import Document

# Stock Reconciliation
#---------------------------

sreco = Document(
		fielddata = {
			'doctype': 'Stock Reconciliation',
			'name': 'sreco',
			'reconciliation_date': '2011-09-08',
			'reconciliation_time': '20:00',
		}
	)

# diff in both
csv_data1 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 20, 150]
]

# diff in qty, no rate
csv_data2 = [
	['Item', 'Warehouse', 'Quantity'],
	['it', 'wh1', 20]
]

# diff in rate, no qty
csv_data3 = [
	['Item', 'Warehouse', 'Rate'],
	['it', 'wh1', 200]
]

# diff in rate, same qty
csv_data4 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 5, 200]
]

# no diff
csv_data1 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 5, 100]
]
