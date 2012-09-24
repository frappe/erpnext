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
import webnotes
from webnotes.modules import reload_doc

def execute():
	delete_fields_dn_detail()
	deploy_packing_slip()
	del_packing_slip_pf()


def delete_fields_dn_detail():
	"""
		Delete old fields related to packing slip
	"""
	from webnotes.model import delete_fields
	delete_fields({
		'Delivery Note': [
			'print_packing_slip', 'shipping_mark', 'packed_by',
			'packing_checked_by', 'Text', 'pack_size'
		],
		'Delivery Note Item': [
			'pack_no', 'pack_gross_wt', 'weight_uom', 
			'pack_nett_wt', 'no_of_packs', 'pack_unit', 'pack_size', 
			'packed_by', 'packing_checked_by'
		]
	}, delete=1)
	delete_fields({'Item': ['nett_weight', 'gross_weight']}, delete=1)
	reload_doc('stock', 'doctype', 'delivery_note')
	reload_doc('stock', 'doctype', 'delivery_note_detail')
	reload_doc('stock', 'doctype', 'item')


def deploy_packing_slip():
	reload_doc('stock', 'doctype', 'packing_slip')
	reload_doc('stock', 'doctype', 'packing_slip_detail')
	reload_doc('stock', 'Module Def', 'Stock')
	reload_doc('stock', 'DocType Mapper', 'Delivery Note-Packing Slip')


def del_packing_slip_pf():
	"""
		Delete Print Format: 'Delivery Note Packing List Wise'
	"""
	webnotes.conn.sql("""\
		DELETE FROM `tabDocFormat`
		WHERE parent='Delivery Note'
		AND format='Delivery Note Packing List Wise'""")
	from webnotes.model import delete_doc
	delete_doc('Print Format', 'Delivery Note Packing List Wise')
