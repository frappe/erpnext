# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt, date_diff
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import get_adjustment_details


class SalesPersonCommissionSummary(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

	def run(self):
		self.get_invoice_data()
		self.get_payment_data()
		self.get_adjustment_data()
		self.process_data()

		columns = self.get_columns()

		return columns, self.invoice_data

	def get_invoice_data(self):
		conditions = self.get_conditions()

		self.invoice_data = frappe.db.sql("""
			select inv.name, inv.posting_date,
				inv.customer, inv.territory, st.sales_person,
				inv.base_grand_total, inv.base_net_total, inv.outstanding_amount,
				st.allocated_percentage, st.allocated_amount,
				st.commission_rate, st.incentives
			from `tabSales Invoice` inv
			inner join `tabSales Team` st on st.parenttype = 'Sales Invoice' and st.parent = inv.name
			where inv.docstatus = 1 {0}
			order by inv.posting_date desc, inv.name desc, st.sales_person
		""".format(conditions), self.filters, as_dict=1)

		self.invoice_names = [d.name for d in self.invoice_data]

		return self.invoice_data

	def get_payment_data(self):
		self.invoice_payment_map = {}
		self.payment_data = []

		if not self.invoice_data:
			return

		self.payment_data = frappe.db.sql("""
			select posting_date, voucher_type, voucher_no, party_type, party, debit, credit, against_voucher
			from `tabGL Entry`
			where voucher_type in ('Journal Entry', 'Payment Entry') and against_voucher_type = 'Sales Invoice'
				and against_voucher in %s
			order by posting_date
		""", [self.invoice_names], as_dict=1)

		for d in self.payment_data:
			self.invoice_payment_map.setdefault(d.against_voucher, []).append(d)

	def get_adjustment_data(self):
		gl_entries = frappe.db.sql("""
			select
				posting_date, account, party, voucher_type, voucher_no, against_voucher_type, against_voucher,
				debit, credit, debit_in_account_currency, credit_in_account_currency
			from
				`tabGL Entry`
			where
				voucher_type not in ('Sales Invoice', 'Purchase Invoice')
				and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle
					where gle.party_type = 'Customer' and ifnull(party, '') != ''
					and gle.against_voucher_type = 'Sales Invoice' and gle.against_voucher in %(invoice_names)s
				) and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle, `tabAccount` acc
					where acc.name = gle.account and acc.root_type in ('Income', 'Expense')
				)
		""", {'invoice_names': self.invoice_names}, as_dict=True)

		adjustment_voucher_entries = {}
		for gle in gl_entries:
			adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), [])
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		self.adjustment_details = get_adjustment_details(adjustment_voucher_entries,
			"debit", "credit")

	def process_data(self):
		for d in self.invoice_data:
			d.commission_amount = flt(d.allocated_amount) * flt(d.commission_rate)
			d.paid_amount = 0

			payments = self.invoice_payment_map.get(d.name, [])
			for p in payments:
				d.paid_amount += p.credit - p.debit

			if not d.outstanding_amount and payments:
				d.clearing_date = payments[-1].posting_date
				d.age = date_diff(d.clearing_date, d.posting_date)

			voucher_tuple = ('Sales Invoice', d.name)
			total_adjustment = sum([amount for amount in self.adjustment_details.vouchers.get(voucher_tuple, {}).values()])
			d.paid_amount -= total_adjustment
			d.total_deductions = total_adjustment

			adjustments = self.adjustment_details.vouchers.get(voucher_tuple, {})
			for account in self.adjustment_details.accounts:
				d["adj_" + scrub(account)] = adjustments.get(account, 0)

	def get_conditions(self):
		conditions = []

		if self.filters.get('from_date'):
			conditions.append("inv.posting_date >= %(from_date)s")

		if self.filters.get('to_date'):
			conditions.append("inv.posting_date <= %(to_date)s")

		if self.filters.get('company'):
			conditions.append("inv.company = %(company)s")

		if self.filters.get('customer'):
			conditions.append("inv.customer = %(customer)s")

		if self.filters.get('territory'):
			conditions.append("inv.territory = %(territory)s")

		if self.filters.get('sales_person'):
			conditions.append("st.sales_person = %(sales_person)s")

		if self.filters.get('exclude_unpaid_invoices'):
			conditions.append("inv.outstanding_amount <= 0")

		return "and " + " and ".join(conditions) if conditions else ""

	def get_columns(self):
		columns = [
			{
				"label": _("Sales Invoice"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 140
			},
			{
				"label": _("Customer"),
				"options": "Customer",
				"fieldname": "customer",
				"fieldtype": "Link",
				"width": 140
			},
			{
				"label": _("Sales Person"),
				"options": "Sales Person",
				"fieldname": "sales_person",
				"fieldtype": "Link",
				"width": 140
			},
			{
				"label": _("Territory"),
				"options": "Territory",
				"fieldname": "territory",
				"fieldtype": "Link",
				"width": 100
			},
			{
				"label": _("Net Total"),
				"fieldname": "base_net_total",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("% Contribution"),
				"fieldname": "allocated_percentage",
				"fieldtype": "Percent",
				"width": 90
			},
			{
				"label": _("Contribution"),
				"fieldname": "allocated_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("% Commission"),
				"fieldname": "commission_rate",
				"fieldtype": "Percent",
				"width": 90
			},
			{
				"label": _("Commission Amount"),
				"fieldname": "commission_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Invoice Date"),
				"fieldname": "posting_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Clearing Date"),
				"fieldname": "clearing_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Age"),
				"fieldname": "age",
				"fieldtype": "Int",
				"width": 60
			},
			{
				"label": _("Grand Total"),
				"fieldname": "base_grand_total",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Outstanding Amount"),
				"fieldname": "outstanding_amount",
				"fieldtype": "Currency",
				"width": 110,
				"hide_if_exclude_unpaid": 1,
			},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Total Deductions"),
				"fieldname": "total_deductions",
				"fieldtype": "Currency",
				"width": 110
			},
		]

		if self.filters.show_deduction_details:
			for account in self.adjustment_details.accounts:
				columns.append({
					"label": account,
					"fieldname": "adj_" + scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
					"is_adjustment": 1
				})

		if self.filters.exclude_unpaid_invoices:
			columns = [c for c in columns if not c.get('hide_if_exclude_unpaid')]

		return columns


def execute(filters=None):
	return SalesPersonCommissionSummary(filters).run()
