# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

from erpnext.stock.utils import get_valuation_method
from erpnext.stock.stock_ledger import get_previous_sle

class LandedCostVoucher(Document):
	def get_items_from_purchase_receipts(self):
		self.set("landed_cost_items", [])
		for pr in self.get("landed_cost_purchase_receipts"):
			pr_items = frappe.db.sql("""select pr_item.item_code, pr_item.description,
				pr_item.qty, pr_item.rate, pr_item.amount, pr_item.name
				from `tabPurchase Receipt Item` pr_item where parent = %s
				and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 'Yes')""",
				pr.purchase_receipt, as_dict=True)

			for d in pr_items:
				item = self.append("landed_cost_items")
				item.item_code = d.item_code
				item.description = d.description
				item.qty = d.qty
				item.rate = d.rate
				item.amount = d.amount
				item.purchase_receipt = pr.purchase_receipt
				item.purchase_receipt_item = d.name

		if self.get("landed_cost_taxes_and_charges"):
			self.set_applicable_charges_for_item()


	def validate(self):
		self.check_mandatory()
		self.validate_purchase_receipts()
		self.set_total_taxes_and_charges()
		if not self.get("landed_cost_items"):
			self.get_items_from_purchase_receipts()
		else:
			self.set_applicable_charges_for_item()

	def check_mandatory(self):
		if not self.get("landed_cost_purchase_receipts"):
			frappe.throw(_("Please enter Purchase Receipts"))

		if not self.get("landed_cost_taxes_and_charges"):
			frappe.throw(_("Please enter Taxes and Charges"))

	def validate_purchase_receipts(self):
		purchase_receipts = []
		for d in self.get("landed_cost_purchase_receipts"):
			if frappe.db.get_value("Purchase Receipt", d.purchase_receipt, "docstatus") != 1:
				frappe.throw(_("Purchase Receipt must be submitted"))
			else:
				purchase_receipts.append(d.purchase_receipt)

		for item in self.get("landed_cost_items"):
			if not item.purchase_receipt:
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))
			elif item.purchase_receipt not in purchase_receipts:
				frappe.throw(_("Item Row {0}: Purchase Receipt {1} does not exist in above 'Purchase Receipts' table")
					.format(item.idx, item.purchase_receipt))

	def set_total_taxes_and_charges(self):
		self.total_taxes_and_charges = sum([flt(d.amount) for d in self.get("landed_cost_taxes_and_charges")])

	def set_applicable_charges_for_item(self):
		total_item_cost = sum([flt(d.amount) for d in self.get("landed_cost_items")])

		for item in self.get("landed_cost_items"):
			item.applicable_charges = flt(item.amount) *  flt(self.total_taxes_and_charges) / flt(total_item_cost)

	def on_submit(self):
		self.update_landed_cost()

	def on_cancel(self):
		self.update_landed_cost()

	def update_landed_cost(self):
		purchase_receipts = list(set([d.purchase_receipt for d in self.get("landed_cost_items")]))
		for purchase_receipt in purchase_receipts:
			pr = frappe.get_doc("Purchase Receipt", purchase_receipt)

			# set landed cost voucher amount in pr item
			pr.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			pr.update_valuation_rate("purchase_receipt_details")

			# save will update landed_cost_voucher_amount and voucher_amount in PR,
			# as those fields are ellowed to edit after submit
			pr.save()

			# update stock & gl entries for cancelled state of PR
			pr.docstatus = 2
			pr.update_stock()
			pr.make_gl_entries_on_cancel()

			# update stock & gl entries for submit state of PR
			pr.docstatus = 1
			pr.update_stock()
			pr.make_gl_entries()
