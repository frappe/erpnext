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
				from `tab{doctype} Item` pr_item where parent = %s
				and exists(select name from tabItem where name = pr_item.item_code and is_stock_item = 1)
				""".format(doctype=pr.receipt_document_type), pr.receipt_document, as_dict=True)

			for d in pr_items:
				item = self.append("items")
				item.item_code = d.item_code
				item.description = d.description
				item.qty = d.qty
				item.rate = d.base_rate
				item.amount = d.base_amount
				item.receipt_document_type = pr.receipt_document_type
				item.receipt_document = pr.receipt_document
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
			frappe.throw(_("Please enter Receipt Document"))

		if not self.get("taxes"):
			frappe.throw(_("Please enter Taxes and Charges"))

	def validate_purchase_receipts(self):
		receipt_documents = []
		
		for d in self.get("purchase_receipts"):
			if frappe.db.get_value(d.receipt_document_type, d.receipt_document, "docstatus") != 1:
				frappe.throw(_("Receipt document must be submitted"))
			else:
				receipt_documents.append(d.receipt_document)

		for item in self.get("items"):
			if not item.receipt_document:
				frappe.throw(_("Item must be added using 'Get Items from Purchase Receipts' button"))
			elif item.receipt_document not in receipt_documents:
				frappe.throw(_("Item Row {idx}: {doctype} {docname} does not exist in above '{doctype}' table")
					.format(idx=item.idx, doctype=item.receipt_document_type, docname=item.receipt_document))

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
		for d in self.get("items"):
			doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)

			# set landed cost voucher amount in pr item
			doc.set_landed_cost_voucher_amount()

			# set valuation amount in pr item
			doc.update_valuation_rate("items")

			# save will update landed_cost_voucher_amount and voucher_amount in PR,
			# as those fields are allowed to edit after submit
			doc.save()

			# update latest valuation rate in serial no
			self.update_rate_in_serial_no(doc)

			# update stock & gl entries for cancelled state of PR
			doc.docstatus = 2
			doc.update_stock_ledger(allow_negative_stock=True, via_landed_cost_voucher=True)
			doc.make_gl_entries_on_cancel()


			# update stock & gl entries for submit state of PR
			doc.docstatus = 1
			doc.update_stock_ledger(via_landed_cost_voucher=True)
			doc.make_gl_entries()

	def update_rate_in_serial_no(self, receipt_document):
		for item in receipt_document.get("items"):
			if item.serial_no:
				serial_nos = get_serial_nos(item.serial_no)
				if serial_nos:
					frappe.db.sql("update `tabSerial No` set purchase_rate=%s where name in ({0})"
						.format(", ".join(["%s"]*len(serial_nos))), tuple([item.valuation_rate] + serial_nos))
