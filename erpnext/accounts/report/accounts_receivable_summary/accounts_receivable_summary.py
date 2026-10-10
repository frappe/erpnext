# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.utils import get_currency_precision, get_party_types_from_account_type


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)


class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		self.account_type = args.get("account_type")
		self.party_type = get_party_types_from_account_type(self.account_type)
		self.party_naming_by = frappe.db.get_single_value(args.get("naming_by")[0], args.get("naming_by")[1])
		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_data(self, args):
		self.data = []
		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]
		self.currency_precision = get_currency_precision() or 2

		self.get_party_total(args)

		if self.filters.show_gl_balance:
			gl_balance_map = self.get_gl_balance()

		for party, party_dict in self.party_total.items():
			if flt(party_dict.outstanding, self.currency_precision) == 0:
				continue

			row = frappe._dict()

			row.party = party
			if self.party_naming_by == "Naming Series":
				if self.account_type == "Payable":
					doctype = "Supplier"
					fieldname = "supplier_name"
				else:
					doctype = "Customer"
					fieldname = "customer_name"
				row.party_name = frappe.get_cached_value(doctype, party, fieldname)

			row.update(party_dict)

			# Advance against party
			row.advance = self.party_advance.get(party, 0)

			# In AR/AP, advance shown in paid columns,
			# but in summary report advance shown in separate column
			row.paid -= row.advance

			if self.filters.show_gl_balance:
				row.gl_balance = gl_balance_map.get(party)
				row.diff = flt(row.outstanding) - flt(row.gl_balance)

			if self.filters.show_future_payments:
				row.remaining_balance = flt(row.outstanding) - flt(row.future_amount)

			self.data.append(row)

	def get_party_total(self, args):
		self.party_total = frappe._dict()
		self.party_advance = frappe._dict()
		invoice_doctypes = frappe.get_hooks("invoice_doctypes")

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.party]):
				if isinstance(self.party_total[d.party][k], float):
					self.party_total[d.party][k] += d.get(k) or 0.0

			# unallocated payments are the rows of non invoice vouchers
			if d.voucher_type not in invoice_doctypes:
				self.party_advance[d.party] = self.party_advance.get(d.party, 0.0) + flt(d.paid)

			# set territory, customer_group, sales person etc
			self.set_party_details(d)

	def init_party_total(self, row):
		default_dict = {
			"invoiced": 0.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 0.0,
			"total_due": 0.0,
			"future_amount": 0.0,
			"sales_person": [],
			"party_type": row.party_type,
		}
		for i in [0, *self.range_numbers]:
			range_key = f"range{i}"
			default_dict[range_key] = 0.0

		self.party_total.setdefault(
			row.party,
			frappe._dict(default_dict),
		)

	def set_party_details(self, row):
		self.party_total[row.party].currency = row.currency

		for key in ("territory", "customer_group", "supplier_group"):
			if row.get(key):
				self.party_total[row.party][key] = row.get(key, "")
		if row.sales_person:
			self.party_total[row.party].sales_person.append(row.get("sales_person", ""))

		if self.filters.sales_partner and row.get("sales_partner"):
			self.party_total[row.party]["sales_partner"] = row.get("sales_partner")

	def get_columns(self):
		self.columns = []
		self.add_column(
			label=_("Party Type"),
			fieldname="party_type",
			fieldtype="Link",
			options="DocType",
			width=100,
		)
		self.add_column(
			label=_("Party"),
			fieldname="party",
			fieldtype="Dynamic Link",
			options="party_type",
			width=180,
			sticky=(self.party_naming_by not in ["Naming Series", "Auto Name"]),
		)

		if self.party_naming_by == "Naming Series":
			self.add_column(
				label=_("Supplier Name") if self.account_type == "Payable" else _("Customer Name"),
				fieldname="party_name",
				fieldtype="Data",
				sticky=True,
			)

		credit_debit_label = "Credit Note" if self.account_type == "Receivable" else "Debit Note"

		self.add_column(_("Advance Amount"), fieldname="advance")
		self.add_column(_("Invoiced Amount"), fieldname="invoiced")
		self.add_column(_("Paid Amount"), fieldname="paid")
		self.add_column(_(credit_debit_label), fieldname="credit_note")
		self.add_column(_("Outstanding Amount"), fieldname="outstanding")

		if self.filters.show_gl_balance:
			self.add_column(_("GL Balance"), fieldname="gl_balance")
			self.add_column(_("Difference"), fieldname="diff")

		self.setup_ageing_columns()
		self.add_column(label=_("Total Amount Due"), fieldname="total_due")

		if self.filters.show_future_payments:
			self.add_column(label=_("Future Payment Amount"), fieldname="future_amount")
			self.add_column(label=_("Remaining Balance"), fieldname="remaining_balance")

		if self.account_type == "Receivable":
			self.add_column(
				label=_("Territory"), fieldname="territory", fieldtype="Link", options="Territory"
			)
			self.add_column(
				label=_("Customer Group"),
				fieldname="customer_group",
				fieldtype="Link",
				options="Customer Group",
			)
			if self.filters.show_sales_person:
				self.add_column(label=_("Sales Person"), fieldname="sales_person", fieldtype="Data")

			if self.filters.sales_partner:
				self.add_column(label=_("Sales Partner"), fieldname="sales_partner", fieldtype="Data")

		else:
			self.add_column(
				label=_("Supplier Group"),
				fieldname="supplier_group",
				fieldtype="Link",
				options="Supplier Group",
			)

		self.add_column(
			label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", width=80
		)

	def get_gl_balance(self) -> frappe._dict:
		gle = frappe.qb.DocType("GL Entry")
		balance = gle.credit - gle.debit if self.account_type == "Payable" else gle.debit - gle.credit
		query = (
			frappe.qb.from_(gle)
			.select(gle.party, Sum(balance))
			.where(
				(gle.posting_date <= self.filters.report_date)
				& (gle.is_cancelled == 0)
				& (gle.company == self.filters.company)
				& (gle.party_type.isin(self.party_type))
				& (gle.account.isin(self.get_party_accounts()))
			)
			.groupby(gle.party)
		)
		if self.filters.cost_center:
			query = query.where(
				gle.cost_center.isin(get_cost_centers_with_children(self.filters.cost_center))
			)

		return frappe._dict(query.run())

	def get_party_accounts(self) -> list[str]:
		if self.filters.party_account:
			return [self.filters.party_account]

		return frappe.get_all(
			"Account",
			filters={"account_type": self.account_type, "company": self.filters.company},
			pluck="name",
		)
