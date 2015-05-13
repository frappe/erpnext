# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class LandedCostVoucher(Document):
	def get_items_from_purchase_receipts(self):
		self.set("items", [])
		for pr in self.get("purchase_receipts"):
			pr_items = frappe.db.sql("""select pr_item.item_code, pr_item.description,
				pr_item.qty, pr_item.base_rate, pr_item.base_amount, pr_item.name
				from `tabPurchase Receipt Item` pr_item where parent = %s
				and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 'Yes')""",
				pr.purchase_receipt, as_dict=True)

			for d in pr_items:
				item = self.append("items")
				item.item_code = d.item_code
				item.description = d.description
				item.qty = d.qty
				item.rate = d.base_rate
				item.amount = d.base_amount
				item.purchase_receipt = pr.purchase_receipt
				item.purchase_receipt_item = d.name

		if self.get("taxes"):
			self.set_applicable_charges_for_item()


	def validate(self):
		self.check_mandatory()
		self.validate_purchase_receipts()
		self.set_total_taxes_and_charges()
		if not self.get("items"):
			self.get_items_from_purchase_receipts()
		else:
			self.set_applicable_charges_for_item()

	def check_mandatory(self):
		if not self.get("purchase_receipts"):
			frappe.throw(_("Please enter Purchase Receipts"))

		if not self.get("taxes"):
			frappe.throw(_("Please enter Taxes and Charges"))

	def validate_purchase_receipts(self):
		purchase_receipts = []
		for d in self.get("purchase_receipts"):
			if frappe.db.get_value("Purchase Receipt", d.purchase_receipt, "docstatus") != 1:
				frappe.throw(_("Purchase Receipt must be submitted"))
			else:
				purchase_receipts.append(d.purchase_receipt)

		for item in self.get("items"):
			if not item.purchase_receipt:
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))
			elif item.purchase_receipt not in purchase_receipts:
				frappe.throw(_("Item Row {0}: Purchase Receipt {1} does not exist in above 'Purchase Receipts' table")
					.format(item.idx, item.purchase_receipt))

	def set_total_taxes_and_charges(self):
		self.total_taxes_and_charges = sum([flt(d.amount) for d in self.get("taxes")])

	def set_applicable_charges_for_item(self):
		based_on = self.distribute_charges_based_on.lower()
		total = sum([flt(d.get(based_on)) for d in self.get("items")])
		
		if not total:
			frappe.throw(_("Total {0} for all items is zero, may you should change 'Distribute Charges Based On'").format(based_on))

		for item in self.get("items"):
			item.applicable_charges = flt(item.get(based_on)) *  flt(self.total_taxes_and_charges) / flt(total)

	def on_submit(self):
		self.update_landed_cost()

	def on_cancel(self):
		self.update_landed_cost()

	def update_landed_cost(self):
		purchase_receipts = list(set([d.purchase_receipt for d in self.get("items")]))
		for purchase_receipt in purchase_receipts:
			pr = frappe.get_doc("Purchase Receipt", purchase_receipt)

			# set landed cost voucher amount in pr item
			pr.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			pr.update_valuation_rate("items")

			# save will update landed_cost_voucher_amount and voucher_amount in PR,
			# as those fields are allowed to edit after submit
			pr.save()

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no(pr)

			# update stock & gl entries for cancelled state of PR
			pr.docstatus = 2
			pr.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			pr.make_gl_entries_on_cancel()


			# update stock & gl entries for submit state of PR
			pr.docstatus = 1
			pr.update_stock_ledger(via_landed_cost_voucher=True)
			pr.make_gl_entries()

	def update_rate_in_serial_no(self, purchase_receipt):
		for item in purchase_receipt.get("items"):
			if item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql("update `tabSerial No` set purchase_rate=%s where name in ({0})"
						.format(", ".join(["%s"]*len(serial_nos))), tuple([item.valuation_rate] + serial_nos))
