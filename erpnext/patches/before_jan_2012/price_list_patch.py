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

	reload_doc('accounts', 'doctype', 'receivable_voucher')
	reload_doc('stock', 'doctype', 'delivery_note')
	reload_doc('selling', 'doctype', 'sales_order')
	reload_doc('selling', 'doctype', 'quotation')
	reload_doc('setup', 'doctype', 'manage_account')


	for d in ['Sales Invoice', 'Delivery Note', 'Sales Order', 'Quotation']:
		webnotes.conn.sql("update `tab%s` set price_list_currency = currency, plc_conversion_rate = conversion_rate" % d)
