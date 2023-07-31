# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import comma_and


class RepostAccountingLedger(Document):
	def __init__(self, *args, **kwargs):
		super(RepostAccountingLedger, self).__init__(*args, **kwargs)
		self._allowed_types = set(
			["Purchase Invoice", "Sales Invoice", "Payment Entry", "Journal Entry"]
		)

	def validate(self):
		self.validate_vouchers()
		self.validate_for_closed_fiscal_year()

	def validate_for_closed_fiscal_year(self):
		if self.vouchers:
			latest_pcv = (
				frappe.db.get_all(
					"Period Closing Voucher",
					filters={"company": self.company},
					order_by="posting_date desc",
					pluck="posting_date",
					limit=1,
				)
				or None
			)
			if not latest_pcv:
				return

			for vtype in self._allowed_types:
				if names := [x.voucher_no for x in self.vouchers if x.voucher_type == vtype]:
					latest_voucher = frappe.db.get_all(
						vtype,
						filters={"name": ["in", names]},
						pluck="posting_date",
						order_by="posting_date desc",
						limit=1,
					)[0]
					if latest_voucher and latest_pcv > latest_voucher:
						frappe.throw(_("Cannot Resubmit Ledger entries for vouchers in Closed fiscal year."))

	def validate_vouchers(self):
		if self.vouchers:
			# Validate voucher types
			voucher_types = set([x.voucher_type for x in self.vouchers])
			if disallowed_types := voucher_types.difference(self._allowed_types):
				frappe.throw(
					_("{0} types are not allowed. Only {1} are.").format(
						frappe.bold(comma_and(list(disallowed_types))),
						frappe.bold(comma_and(list(self._allowed_types))),
					)
				)

	def generate_preview(self):
		self.gl_entries = []
		for x in self.vouchers:
			doc = frappe.get_doc(x.voucher_type, x.voucher_no)
			if doc.doctype in ["Payment Entry", "Journal Entry"]:
				gle_map = doc.build_gl_map()
			else:
				gle_map = doc.get_gl_entries()

			# add empty row
			self.gl_entries.append(gle_map + [])

	def format_preview(self):
		from erpnext.accounts.report.general_ledger.general_ledger import get_columns
		from erpnext.controllers.stock_controller import get_columns, get_data

		if self.gl_entries:
			fields = [
				"posting_date",
				"account",
				"debit",
				"credit",
				"against",
				"party",
				"party_type",
				"cost_center",
				"against_voucher_type",
				"against_voucher",
			]

			filters = {"company": self.company}
			columns = get_columns(filters)
			data = self.gl_entries

			gl_columns = get_columns(columns, fields)
			gl_data = get_data(fields, self.gl_entries)

	def on_submit(self):
		job_name = "repost_accounting_ledger_" + self.name
		frappe.enqueue(
			method="erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger.start_repost",
			account_repost_doc=self.name,
			is_async=True,
			job_name=job_name,
		)
		frappe.msgprint(_("Repost has started in the background"))


@frappe.whitelist()
def start_repost(account_repost_doc=str) -> None:
	if account_repost_doc:
		repost_doc = frappe.get_doc("Repost Accounting Ledger", account_repost_doc)

		if repost_doc.docstatus == 1:
			for x in repost_doc.vouchers:
				doc = frappe.get_doc(x.voucher_type, x.voucher_no)

				if repost_doc.delete_cancelled_entries:
					frappe.db.delete("GL Entry", filters={"voucher_type": doc.doctype, "voucher_no": doc.name})
					frappe.db.delete(
						"Payment Ledger Entry", filters={"voucher_type": doc.doctype, "voucher_no": doc.name}
					)

				if doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
					if not repost_doc.delete_cancelled_entries:
						doc.docstatus = 2
						doc.make_gl_entries_on_cancel()

					doc.docstatus = 1
					doc.make_gl_entries()

				elif doc.doctype in ["Payment Entry", "Journal Entry"]:
					if not repost_doc.delete_cancelled_entries:
						doc.make_gl_entries(1)
					doc.make_gl_entries()

				frappe.db.commit()
