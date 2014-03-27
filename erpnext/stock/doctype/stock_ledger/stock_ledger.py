# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cstr, flt, nowdate, cint, now
from frappe.model.bean import getlist
from frappe.model.code import get_obj
from frappe import session, msgprint
from erpnext.stock.utils import get_valid_serial_nos


from frappe.model.document import Document

class StockLedger(Document):
		
	def update_stock(self, values, is_amended = 'No'):
		for v in values:
			sle_id = ''
			
			# reverse quantities for cancel
			if v.get('is_cancelled') == 'Yes':
				v['actual_qty'] = -flt(v['actual_qty'])
				# cancel matching entry
				frappe.db.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
					modified=%s, modified_by=%s
					where voucher_no=%s and voucher_type=%s""", 
					(now(), frappe.session.user, v['voucher_no'], v['voucher_type']))

			if v.get("actual_qty"):
				sle_id = self.make_entry(v)
				
			args = v.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended
			})
			
			get_obj('Warehouse', v["warehouse"]).update_bin(args)


	def make_entry(self, args):
		args.update({"doctype": "Stock Ledger Entry"})
		sle = frappe.bean([args])
		sle.ignore_permissions = 1
		sle.insert()
		return sle.doc.name
	
	def repost(self):
		"""
		Repost everything!
		"""
		for wh in frappe.db.sql("select name from tabWarehouse"):
			get_obj('Warehouse', wh[0]).repost_stock()
