# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr, flt
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
			
	def update_landed_cost(self):
		"""
			Add extra cost and recalculate all values in pr, 
			Recalculate valuation rate in all sle after pr posting date
		"""
		purchase_receipts = [row.purchase_receipt for row in 
			self.doclist.get({"parentfield": "lc_pr_details"})]
			
		self.validate_purchase_receipts(purchase_receipts)
		self.cancel_pr(purchase_receipts)
		self.add_charges_in_pr(purchase_receipts)
		self.submit_pr(purchase_receipts)
		msgprint("Landed Cost updated successfully")

	def validate_purchase_receipts(self, purchase_receipts):
		for pr in purchase_receipts:
			if webnotes.conn.get_value("Purchase Receipt", pr, "docstatus") != 1:
				webnotes.throw(_("Purchase Receipt") + ": " + pr + _(" is not submitted document"))

	def add_charges_in_pr(self, purchase_receipts):
		""" Add additional charges in selected pr proportionately"""
		total_amt = self.get_total_pr_amt(purchase_receipts)
		
		for pr in purchase_receipts:
			pr_bean = webnotes.bean('Purchase Receipt', pr)
			idx = max([d.idx for d in pr_bean.doclist.get({"parentfield": "purchase_tax_details"})])
			
			for lc in self.doclist.get({"parentfield": "landed_cost_details"}):
				amt = flt(lc.amount) * flt(pr_bean.doc.net_total)/ flt(total_amt)
				
				matched_row = pr_bean.doclist.get({
					"parentfield": "purchase_tax_details", 
					"category": "Valuation",
					"add_deduct_tax": "Add",
					"charge_type": "Actual",
					"account_head": lc.account_head
				})
				
				if not matched_row:	# add if not exists
					ch = addchild(pr_bean.doc, 'purchase_tax_details', 'Purchase Taxes and Charges')
					ch.category = 'Valuation'
					ch.add_deduct_tax = 'Add'
					ch.charge_type = 'Actual'
					ch.description = lc.description
					ch.account_head = lc.account_head
					ch.cost_center = lc.cost_center
					ch.rate = amt
					ch.tax_amount = amt
					ch.docstatus = 1
					ch.idx = idx
					ch.save(1)
					idx += 1
				else:	# overwrite if exists
					matched_row[0].rate = amt
					matched_row[0].tax_amount = amt
					matched_row[0].cost_center = lc.cost_center
					
			pr_bean.run_method("validate")
			for d in pr_bean.doclist:
				d.save()
	
	def get_total_pr_amt(self, purchase_receipts):
		return webnotes.conn.sql("""SELECT SUM(net_total) FROM `tabPurchase Receipt` 
			WHERE name in (%s)""" % ', '.join(['%s']*len(purchase_receipts)), 
			tuple(purchase_receipts))[0][0]
			
	def cancel_pr(self, purchase_receipts):
		for pr in purchase_receipts:
			pr_bean = webnotes.bean("Purchase Receipt", pr)
			
			pr_bean.run_method("update_ordered_qty")
			
			webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
				where voucher_type='Purchase Receipt' and voucher_no=%s""", pr)
			webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type='Purchase Receipt' 
				and voucher_no=%s""", pr)
			
	def submit_pr(self, purchase_receipts):
		for pr in purchase_receipts:
			pr_bean = webnotes.bean("Purchase Receipt", pr)
			pr_bean.run_method("update_ordered_qty")
			pr_bean.run_method("update_stock")
			pr_bean.run_method("make_gl_entries")