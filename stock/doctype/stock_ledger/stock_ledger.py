# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, cstr, flt, nowdate, cint, now
from webnotes.model.doc import Document
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import session, msgprint
from stock.utils import get_valid_serial_nos


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def update_stock(self, values, is_amended = 'No'):
		for v in values:
			sle_id = ''
			
			# reverse quantities for cancel
			if v.get('is_cancelled') == 'Yes':
				v['actual_qty'] = -flt(v['actual_qty'])
				# cancel matching entry
				webnotes.conn.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
					modified=%s, modified_by=%s
					where voucher_no=%s and voucher_type=%s""", 
					(now(), webnotes.session.user, v['voucher_no'], v['voucher_type']))

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
		sle = webnotes.bean([args])
		sle.ignore_permissions = 1
		sle.insert()
		return sle.doc.name
	
	def repost(self):
		"""
		Repost everything!
		"""
		for wh in webnotes.conn.sql("select name from tabWarehouse"):
			get_obj('Warehouse', wh[0]).repost_stock()
