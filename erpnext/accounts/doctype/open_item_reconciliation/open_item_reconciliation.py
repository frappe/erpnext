# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class OpenItemReconciliation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING: # pragma: no cover
		from erpnext.accounts.doctype.gl_entry_allocation.gl_entry_allocation import GLEntryAllocation
		from erpnext.accounts.doctype.gl_reconciliation_details.gl_reconciliation_details import GLReconciliationDetails
		from frappe.types import DF

		account: DF.Link
		allocation: DF.Table[GLEntryAllocation]
		amended_from: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		credit_amount: DF.Table[GLReconciliationDetails]
		debit_amount: DF.Table[GLReconciliationDetails]
		naming_series: DF.Literal["OIR.#####"]
		total_credit_amount: DF.Currency
		total_debit_amount: DF.Currency
	# end: auto-generated types
	pass

	def on_cancel(self):
		reconciled_entries, unwanted_lines =  self.get_linked_glr_rows()
		self.remove_current_glr_row(reconciled_entries,unwanted_lines)


	@frappe.whitelist()
	def fetch_unreconciled_gl_entries(self):
		credit_gle = self.debit_credit_gle("Credit")
		debit_gle = self.debit_credit_gle("Debit")

		self.set("allocation", [])
		self.set("credit_amount", [])
		if credit_gle:
			for cgle in credit_gle:
				row = self.append("credit_amount", {})
				row.update({
					"gl_entry":cgle.get("name"),
					"outstanding_amount":cgle.get("outstanding_amount"),
					"voucher_type":cgle.get("voucher_type"),
					"voucher_no":cgle.get("voucher_no")
				})

		self.set("debit_amount", [])
		if debit_gle:
			for dgle in debit_gle:
				row = self.append("debit_amount", {})
				row.update({
					"gl_entry":dgle.get("name"),
					"outstanding_amount":dgle.get("outstanding_amount"),
					"voucher_type":dgle.get("voucher_type"),
					"voucher_no":dgle.get("voucher_no")
				})
		
	
	def get_reconciled_entries(self):
		reconciled_entries = []
		if self.allocation:
			for i in self.allocation:
				reconciled_entries.append(i.get("credit_gl"))
				reconciled_entries.append(i.get("debit_gl"))
		return list(set(reconciled_entries))
	
	def get_linked_glr_rows(self):
		reconciled_entries = self.get_reconciled_entries()
		if reconciled_entries:
			unwanted_lines = []
			for i in reconciled_entries:
				if frappe.db.exists("GL Entry Reconciliation Details",{"parent":i,"glr_ref_id":self.name}):
					entries_to_be_deleted = frappe.db.get_all("GL Entry Reconciliation Details",{"parent":i,"glr_ref_id":self.name},["name"])
					if entries_to_be_deleted:
						for j in entries_to_be_deleted:
							unwanted_lines.append(j.get("name"))
			
			return reconciled_entries, unwanted_lines
			
	

	def remove_current_glr_row(self,reconciled_entries,unwanted_lines):        
		if unwanted_lines:
			for i in unwanted_lines:
				frappe.db.delete("GL Entry Reconciliation Details",{"name":i})
				frappe.db.commit()
		
		if reconciled_entries:
			for i in reconciled_entries:
				total_amt = 0.0
				gle_doc = frappe.get_doc("GL Entry",i)
				gle_doc.reload()
				if gle_doc.debit_in_account_currency > 0.0:
					total_amt = gle_doc.debit_in_account_currency
				elif gle_doc.credit_in_account_currency > 0.0:
					total_amt = gle_doc.credit_in_account_currency

				if gle_doc.gl_entry_reconciliation_details:
					total_reconciled_amount = 0.0
					for k in gle_doc.gl_entry_reconciliation_details:
						total_reconciled_amount += k.get("amount")
					if total_reconciled_amount and total_amt:
						frappe.db.set_value("GL Entry", gle_doc.name, "reconciled_amount", total_reconciled_amount)
						total_unreconciled_amount = total_amt - total_reconciled_amount
						frappe.db.set_value("GL Entry", gle_doc.name, "unreconciled_amount", total_unreconciled_amount)
						if total_unreconciled_amount == 0.0:
							frappe.db.set_value("GL Entry", gle_doc.name, "is_reconciled", 1)
						else:
							frappe.db.set_value("GL Entry", gle_doc.name, "is_reconciled", 0)
				else:
					total_reconciled_amount = 0.0
					if total_amt:
						frappe.db.set_value("GL Entry", gle_doc.name, "reconciled_amount", total_reconciled_amount) 
						total_unreconciled_amount = total_amt - total_reconciled_amount
						frappe.db.set_value("GL Entry", gle_doc.name, "unreconciled_amount", total_unreconciled_amount)
						if total_unreconciled_amount == 0.0:
							frappe.db.set_value("GL Entry", gle_doc.name, "is_reconciled", 1)
						else:
							frappe.db.set_value("GL Entry", gle_doc.name, "is_reconciled", 0)

	@frappe.whitelist()
	def allocate_entries(self, args):
		entries = []
		for pay in args.get("debit_gl"):
			for inv in args.get("credit_gl"):
				if pay.get("outstanding_amount") >= inv.get("outstanding_amount"):
					res = self.get_allocated_entry(pay, inv, inv["outstanding_amount"])
					pay["outstanding_amount"] = flt(pay.get("outstanding_amount")) - flt(inv.get("outstanding_amount"))
					inv["outstanding_amount"] = 0
				else:
					res = self.get_allocated_entry(pay, inv, pay["outstanding_amount"])
					inv["outstanding_amount"] = flt(inv.get("outstanding_amount")) - flt(pay.get("outstanding_amount"))
					pay["outstanding_amount"] = 0

				if pay.get("outstanding_amount") == 0:
					entries.append(res)
					break
				elif inv.get("outstanding_amount") == 0:
					entries.append(res)
					continue

			else:
				break

		self.set("allocation", [])
		for entry in entries:
			if entry["allocated_amount"] != 0:
				row = self.append("allocation", {})
				row.update(entry)

	def get_allocated_entry(self, pay, inv, allocated_amount):
		res = frappe._dict(
			{
				"credit_gl": inv.get("gl_entry"),
				"debit_gl": pay.get("gl_entry"),
				"allocated_amount": allocated_amount
			}
		)
		return res
	
	def update_gl_entry(self,parent_gle,child_gle,allocated_amount):
		gle_doc = frappe.get_doc("GL Entry",parent_gle)
		if gle_doc.debit_in_account_currency > 0.0:
			total_amt = gle_doc.debit_in_account_currency
		elif gle_doc.credit_in_account_currency > 0.0:
			total_amt = gle_doc.credit_in_account_currency
		
		child_gle_posting_date = frappe.db.get_value("GL Entry",{"name":child_gle},["posting_date"])

		child_entry = frappe.get_doc({
		"doctype": "GL Entry Reconciliation Details",
		"parent": gle_doc.name,
		"parentfield": "gl_entry_reconciliation_details",
		"parenttype": "GL Entry",
		"gl_entry": child_gle,
		"amount": allocated_amount,
		"posting_date":child_gle_posting_date if child_gle_posting_date else "",
		"glr_ref_id": self.name
		})
		child_entry.insert(ignore_permissions=True)

		gle_doc.reload()
		
		if gle_doc.gl_entry_reconciliation_details:
			total_reconciled_amount = 0.0
			for i in gle_doc.gl_entry_reconciliation_details:
				total_reconciled_amount += i.get("amount")
			if total_reconciled_amount and total_amt:
				total_unreconciled_amount = total_amt - total_reconciled_amount
				frappe.db.set_value("GL Entry", gle_doc.name, "reconciled_amount", total_reconciled_amount)
				frappe.db.set_value("GL Entry", gle_doc.name, "unreconciled_amount", total_unreconciled_amount)
				if total_unreconciled_amount == 0.0:
					frappe.db.set_value("GL Entry", gle_doc.name, "is_reconciled", 1)

	@frappe.whitelist()
	def reconcile_allocated_entries(self,args):
		if args.get("allocated_entries"):
			for alloc in args.get("allocated_entries"):
				self.update_gl_entry(alloc.get("credit_gl"),alloc.get("debit_gl"),alloc.get("allocated_amount"))
				self.update_gl_entry(alloc.get("debit_gl"),alloc.get("credit_gl"),alloc.get("allocated_amount"))
	
	def debit_credit_gle(self,ent_type):
		GLE = frappe.qb.DocType("GL Entry")
		
		qb_query = (
			frappe.qb.from_(GLE)
			.select(GLE.name,GLE.unreconciled_amount.as_("outstanding_amount"),GLE.voucher_type,GLE.voucher_no)
			.where(
				(GLE.company == self.company)&
				(GLE.account == self.account)&
				(GLE.is_reconciled == 0)&
				(GLE.is_cancelled == 0)
			)
		)

		if self.cost_center:
			qb_query = qb_query.where(GLE.cost_center == self.cost_center)

		if ent_type == "Debit":
			qb_query = qb_query.where(GLE.debit_in_account_currency > 0.0)
		
		else:
			qb_query = qb_query.where(GLE.credit_in_account_currency > 0.0)
		
		gle_entries = qb_query.run(as_dict=True)
		return gle_entries
