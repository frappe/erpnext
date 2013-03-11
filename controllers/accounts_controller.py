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
from webnotes import msgprint, _
from webnotes.utils import flt
from utilities.transaction_base import TransactionBase

class AccountsController(TransactionBase):
	def get_gl_dict(self, args, cancel=None):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = {
			'company': self.doc.company, 
			'posting_date': self.doc.posting_date,
			'voucher_type': self.doc.doctype,
			'voucher_no': self.doc.name,
			'aging_date': self.doc.fields.get("aging_date") or self.doc.posting_date,
			'remarks': self.doc.remarks,
			'is_cancelled': self.doc.docstatus == 2 and "Yes" or "No",
			'fiscal_year': self.doc.fiscal_year,
			'debit': 0,
			'credit': 0,
			'is_opening': self.doc.fields.get("is_opening") or "No",
		}
		gl_dict.update(args)
		return gl_dict
				
	def clear_unallocated_advances(self, childtype, parentfield):
		self.doclist.remove_items({"parentfield": parentfield, "allocated_amount": ["in", [0, None, ""]]})
			
		webnotes.conn.sql("""delete from `tab%s` where parentfield=%s and parent = %s 
			and ifnull(allocated_amount, 0) = 0""" % (childtype, '%s', '%s'), (parentfield, self.doc.name))
		
	def get_advances(self, account_head, child_doctype, parentfield, dr_or_cr):
		res = webnotes.conn.sql("""select t1.name as jv_no, t1.remark, 
			t2.%s as amount, t2.name as jv_detail_no
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
			where t1.name = t2.parent and t2.account = %s and t2.is_advance = 'Yes' 
			and (t2.against_voucher is null or t2.against_voucher = '')
			and (t2.against_invoice is null or t2.against_invoice = '') 
			and (t2.against_jv is null or t2.against_jv = '') 
			and t1.docstatus = 1 order by t1.posting_date""" % 
			(dr_or_cr, '%s'), account_head, as_dict=1)
			
		self.doclist = self.doc.clear_table(self.doclist, parentfield)
		for d in res:
			self.doclist.append({
				"doctype": child_doctype,
				"parentfield": parentfield,
				"journal_voucher": d.jv_no,
				"jv_detail_no": d.jv_detail_no,
				"remarks": d.remark,
				"advance_amount": flt(d.amount),
				"allocate_amount": 0
			})
			
	def get_stock_in_hand_account(self):
		stock_in_hand_account = webnotes.conn.get_value("Company", self.doc.company, "stock_in_hand_account")
		
		if not stock_in_hand_account:
			msgprint(_("Missing") + ": " 
				+ _(webnotes.get_doctype("company").get_label("stock_in_hand_account")
				+ " " + _("for Company") + " " + self.doc.company), raise_exception=True)
		
		return stock_in_hand_account
		
	@property
	def stock_items(self):
		if not hasattr(self, "_stock_items"):
			item_codes = list(set(item.item_code for item in self.doclist.get({"parentfield": self.fname})))
			self._stock_items = [r[0] for r in webnotes.conn.sql("""select name
				from `tabItem` where name in (%s) and is_stock_item='Yes'""" % \
				(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._stock_items
		
	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = webnotes.conn.get_value("Company", self.doc.company, "abbr")
			
		return self._abbr