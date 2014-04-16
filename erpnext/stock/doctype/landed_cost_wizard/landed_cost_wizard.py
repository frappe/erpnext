# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

from frappe.model.document import Document

class LandedCostWizard(Document):

	def update_landed_cost(self):
		"""
			Add extra cost and recalculate all values in pr,
			Recalculate valuation rate in all sle after pr posting date
		"""
		purchase_receipts = [row.purchase_receipt for row in
			self.get("lc_pr_details")]

		self.validate_purchase_receipts(purchase_receipts)
		self.cancel_pr(purchase_receipts)
		self.add_charges_in_pr(purchase_receipts)
		self.submit_pr(purchase_receipts)
		msgprint(_("Landed Cost updated successfully"))

	def validate_purchase_receipts(self, purchase_receipts):
		for pr in purchase_receipts:
			if frappe.db.get_value("Purchase Receipt", pr, "docstatus") != 1:
				frappe.throw(_("Purchase Receipt {0} is not submitted").format(pr))

	def add_charges_in_pr(self, purchase_receipts):
		""" Add additional charges in selected pr proportionately"""
		total_amt = self.get_total_pr_amt(purchase_receipts)

		for pr in purchase_receipts:
			pr_doc = frappe.get_doc('Purchase Receipt', pr)
			pr_items = pr_doc.get("purchase_tax_details")

			for lc in self.get("landed_cost_details"):
				amt = flt(lc.amount) * flt(pr_doc.net_total)/ flt(total_amt)

				matched_row = pr_doc.get("other_charges", {
					"category": "Valuation",
					"add_deduct_tax": "Add",
					"charge_type": "Actual",
					"account_head": lc.account_head
				})

				if not matched_row:	# add if not exists
					ch = pr_doc.append("other_charges")
					ch.category = 'Valuation'
					ch.add_deduct_tax = 'Add'
					ch.charge_type = 'Actual'
					ch.description = lc.description
					ch.account_head = lc.account_head
					ch.cost_center = lc.cost_center
					ch.rate = amt
					ch.tax_amount = amt
					ch.docstatus = 1
					ch.db_insert()
				else:	# overwrite if exists
					matched_row[0].rate = amt
					matched_row[0].tax_amount = amt
					matched_row[0].cost_center = lc.cost_center

			pr_doc.run_method("validate")
			pr_doc._validate_mandatory()
			for d in pr_doc.get_all_children():
				d.db_update()

	def get_total_pr_amt(self, purchase_receipts):
		return frappe.db.sql("""SELECT SUM(net_total) FROM `tabPurchase Receipt`
			WHERE name in (%s)""" % ', '.join(['%s']*len(purchase_receipts)),
			tuple(purchase_receipts))[0][0]

	def cancel_pr(self, purchase_receipts):
		for pr in purchase_receipts:
			pr_doc = frappe.get_doc("Purchase Receipt", pr)

			pr_doc.run_method("update_ordered_qty")

			frappe.db.sql("""delete from `tabStock Ledger Entry`
				where voucher_type='Purchase Receipt' and voucher_no=%s""", pr)
			frappe.db.sql("""delete from `tabGL Entry` where voucher_type='Purchase Receipt'
				and voucher_no=%s""", pr)

	def submit_pr(self, purchase_receipts):
		for pr in purchase_receipts:
			pr_doc = frappe.get_doc("Purchase Receipt", pr)
			pr_doc.run_method("update_ordered_qty")
			pr_doc.run_method("update_stock")
			pr_doc.run_method("make_gl_entries")
