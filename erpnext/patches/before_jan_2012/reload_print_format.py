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
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	from webnotes.model.doc import addchild
	from webnotes.model.code import get_obj
	reload_doc('stock', 'Print Format', 'Delivery Note Packing List Wise')
	reload_doc('stock', 'Print Format', 'Purchase Receipt Format')
	reload_doc('accounts', 'Print Format', 'Payment Receipt Voucher')
	reload_doc('accounts', 'Print Format', 'POS Invoice')
	reload_doc('accounts', 'Print Format', 'Form 16A Print Format')
	reload_doc('accounts', 'Print Format', 'Cheque Printing Format')
	
	if not webnotes.conn.sql("select format from `tabDocFormat` where name = 'POS Invoice' and parent = 'Sales Invoice'"):		
		dt_obj = get_obj('DocType', 'Sales Invoice', with_children = 1)
		ch = addchild(dt_obj.doc, 'formats', 'DocFormat', 1)
		ch.format = 'POS Invoice'
		ch.save(1)
