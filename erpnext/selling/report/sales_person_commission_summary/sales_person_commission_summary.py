# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub, unscrub
from frappe.utils import getdate, nowdate, flt, cint, date_diff, cstr
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import get_adjustment_details
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from frappe.desk.query_report import group_report_data


class SalesPersonCommissionSummary(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

	def run(self):
		self.get_invoice_data()
		self.preprocess_invoice_data()
		self.get_payment_data()
		self.get_adjustment_data()
		self.process_data()

		data = self.get_grouped_data()
		columns = self.get_columns()

		return columns, data

	def get_invoice_data(self):
		conditions, having = self.get_conditions()

		self.invoice_data = frappe.db.sql("""
			select inv.name, inv.posting_date,
				inv.customer, inv.territory, sp.sales_person,
				i.sales_commission_category as item_commission_category,
				sp.sales_commission_category as sales_person_commission_category,
				i.commission_rate as item_commission_rate, sp.commission_rate as sales_person_commission_rate,
				inv.base_grand_total, inv.base_net_total, inv.outstanding_amount,
				i.base_net_amount as base_net_amount,
				sp.allocated_percentage,
				(
					select max(posting_date)
					from `tabGL Entry`
					where against_voucher_type = 'Sales Invoice' and against_voucher = inv.name and inv.outstanding_amount <= 0
				) as clearing_date
			from `tabSales Invoice` inv
			inner join `tabSales Invoice Item` i on i.parent = inv.name
			inner join `tabSales Team` sp on sp.parenttype = 'Sales Invoice' and sp.parent = inv.name
			where inv.docstatus = 1 {conditions}
			{having}
		""".format(conditions=conditions, having=having), self.filters, as_dict=1)

		return self.invoice_data

	def preprocess_invoice_data(self):
		# group invoice data
		self.data = {}
		self.invoice_names = []

		for d in self.invoice_data:
			# Determine commission category & rate
			if d.item_commission_category:
				d.sales_commission_category = cstr(d.item_commission_category)
				d.commission_rate = flt(d.item_commission_rate)
			else:
				d.sales_commission_category = cstr(d.sales_person_commission_category)
				d.commission_rate = flt(d.sales_person_commission_rate)

			# Set commission as 0 if outstanding
			commission_category_details = frappe.get_cached_doc("Sales Commission Category", d.sales_commission_category)\
				if d.sales_commission_category else frappe._dict()

			if commission_category_details.not_payable_if_outstanding and d.outstanding_amount > 0:
				d.commission_rate = 0

			# filter 0 commission
			if not self.filters.exclude_zero_commission or d.commission_rate:
				self.invoice_names.append(d.name)

				# Group Data
				key = (d.name, d.sales_person, d.sales_commission_category, d.commission_rate)
				if key not in self.data:
					new_row = d.copy()
					self.data[key] = new_row
				else:
					self.data[key].base_net_amount += d.base_net_amount

		# sort data
		self.data = list(self.data.values())
		self.data = sorted(self.data, key=lambda d: (d.posting_date, d.name, d.sales_commission_category))

	def process_data(self):
		for d in self.data:
			d.group = "'{0} | {1}'".format(d.sales_person, d.sales_commission_category or 'No Category')

			d.invoice_portion = flt(d.base_net_amount) / flt(d.base_net_total) * 100 if d.base_net_total else 100
			d.contribution_amount = flt(d.base_net_amount) * flt(d.allocated_percentage) / 100

			# Payments and Allocations
			d.paid_amount = 0
			d.return_amount = 0

			payments = self.invoice_payment_map.get(d.name, [])
			for p in payments:
				if p.is_return:
					d.return_amount += p.credit - p.debit
				else:
					d.paid_amount += p.credit - p.debit

			if not d.outstanding_amount and payments:
				d.age = date_diff(d.clearing_date, d.posting_date)

			# Payment Deductions
			voucher_tuple = ('Sales Invoice', d.name)
			total_adjustment = sum([amount for amount in self.adjustment_details.vouchers.get(voucher_tuple, {}).values()])
			d.paid_amount -= total_adjustment
			d.total_deductions = total_adjustment + d.return_amount

			adjustments = self.adjustment_details.vouchers.get(voucher_tuple, {})
			for account in self.adjustment_details.accounts:
				d["adj_" + scrub(account)] = adjustments.get(account, 0)

			# Commission Category Details
			commission_category_details = frappe.get_cached_doc("Sales Commission Category", d.sales_commission_category)\
				if d.sales_commission_category else frappe._dict()

			# Deduct Payment Deductions
			d.deduction_on_contribution_amount = 0
			if commission_category_details.consider_deductions:
				d.deduction_on_contribution_amount = d.total_deductions * (d.invoice_portion / 100) * (d.allocated_percentage / 100)

			# Commission Calculation
			d.net_contribution_amount = d.contribution_amount - d.deduction_on_contribution_amount
			d.commission_amount = d.net_contribution_amount * flt(d.commission_rate) / 100

			# Late Payment Deduction
			d.late_payment_deduction_percent = get_late_payment_deduction_percent(commission_category_details, d.age)
			d.commission_amount = d.commission_amount * (100 - d.late_payment_deduction_percent) / 100

	def get_payment_data(self):
		self.invoice_payment_map = {}
		self.payment_data = []

		if not self.data:
			return

		self.payment_data = frappe.db.sql("""
			select gl.posting_date, gl.voucher_type, gl.voucher_no, gl.party_type, gl.party, gl.debit, gl.credit,
				gl.against_voucher, ifnull(inv.is_return, 0) as is_return
			from `tabGL Entry` gl
			left join `tabSales Invoice` inv on gl.voucher_type = 'Sales Invoice' and gl.voucher_no = inv.name
			where against_voucher_type = 'Sales Invoice' and against_voucher in %s
			order by posting_date
		""", [self.invoice_names], as_dict=1)

		for d in self.payment_data:
			self.invoice_payment_map.setdefault(d.against_voucher, []).append(d)

	def get_adjustment_data(self):
		gl_entries = []
		if self.invoice_names:
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
						where acc.name = gle.account and (acc.root_type in ('Income', 'Expense') or acc.account_type = 'Tax')
					)
			""", {'invoice_names': self.invoice_names}, as_dict=True)

		adjustment_voucher_entries = {}
		for gle in gl_entries:
			adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), [])
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		self.adjustment_details = get_adjustment_details(adjustment_voucher_entries, "debit", "credit")

	def get_conditions(self):
		conditions = []
		having_condition = []

		date_field = 'clearing_date' if self.filters.date_type == "Clearing Date" else 'inv.posting_date'
		if self.filters.date_type == "Clearing Date":
			date_conditions = having_condition
		else:
			date_conditions = conditions

		if self.filters.get('from_date'):
			date_conditions.append("{0} >= %(from_date)s".format(date_field))
		if self.filters.get('to_date'):
			date_conditions.append("{0} <= %(to_date)s".format(date_field))

		if self.filters.get('company'):
			conditions.append("inv.company = %(company)s")

		if self.filters.get('customer'):
			conditions.append("inv.customer = %(customer)s")

		if self.filters.get('territory'):
			conditions.append("inv.territory = %(territory)s")

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get('exclude_unpaid_invoices'):
			conditions.append("inv.outstanding_amount <= 0")

		if self.filters.get('name'):
			conditions.append("inv.name = %(name)s")

		if self.filters.get('transaction_type'):
			conditions.append("inv.transaction_type = %(transaction_type)s")

		if self.filters.get('sales_commission_category'):
			conditions.append("IF(i.sales_commission_category IS NULL or i.sales_commission_category = '', sp.sales_commission_category, i.sales_commission_category) = %(sales_commission_category)s")

		if self.filters.get("cost_center"):
			self.filters.cost_center = get_cost_centers_with_children(self.filters.get("cost_center"))

			if frappe.get_meta("Sales Invoice Item").has_field("cost_center") and frappe.get_meta("Sales Invoice").has_field("cost_center"):
				conditions.append("IF(inv.cost_center IS NULL or inv.cost_center = '', i.cost_center, inv.cost_center) in %(cost_center)s")
			elif frappe.get_meta("Sales Invoice Item").has_field("cost_center"):
				conditions.append("i.cost_center in %(cost_center)s")
			elif frappe.get_meta("Sales Invoice").has_field("cost_center"):
				conditions.append("inv.cost_center in %(cost_center)s")

		return "and " + " and ".join(conditions) if conditions else "",\
			"having " + " and ".join(having_condition) if having_condition else ""

	def get_grouped_data(self):
		data = self.data

		self.group_by = [None]
		for i in range(2):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue

			if group_label == "Invoice":
				group_field = "name"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		if len(self.group_by) <= 1:
			return data

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals,
			totals_only=self.filters.totals_only)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		total_fields = [
			'contribution_amount', 'deduction_on_contribution_amount', 'net_contribution_amount', 'commission_amount'
		]

		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		# Set zeros
		for f in total_fields:
			totals[f] = 0

		# Add totals
		for d in data:
			for f in total_fields:
				totals[f] += flt(d[f])

		# Set group values
		if data:
			if 'name' in grouped_by:
				totals['posting_date'] = data[0].get('posting_date')
				totals['customer'] = data[0].get('customer')
				totals['sales_person'] = data[0].get('sales_person')

			if group_field in ('name', 'customer'):
				totals['customer_name'] = data[0].get("customer_name")

		# Set reference field
		group_reference_doctypes = {
			"customer": "Customer",
			"name": "Sales Invoice",
			"item_code": "Item",
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['doc_type'] = reference_dt
		totals['group'] = grouped_by.get(reference_field) if group_field else "'Total'"

		return totals

	def get_columns(self):
		columns = []

		if len(self.group_by) > 1:
			columns.append({
				"label": _("Group"),
				"fieldtype": "Dynamic Link",
				"fieldname": "group",
				"options": "doc_type",
				"width": 180
			})

		columns += [
			{
				"label": _("Sales Person"),
				"fieldname": "sales_person",
				"fieldtype": "Link",
				"options": "Sales Person",
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
				"label": _("Category"),
				"fieldname": "sales_commission_category",
				"fieldtype": "Link",
				"options": "Sales Commission Category",
				"width": 100
			},
			{
				"label": _("Net Amount"),
				"fieldname": "base_net_amount",
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
				"fieldname": "contribution_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Deduction"),
				"fieldname": "deduction_on_contribution_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Net Contribution"),
				"fieldname": "net_contribution_amount",
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
				"label": _("% Late Payment Deduction"),
				"fieldname": "late_payment_deduction_percent",
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
				"label": _("Sales Invoice"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 140
			},
			{
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 140
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
			{
				"label": _("Credit Note"),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"width": 110
			},
			{
				"label": _("Portion %"),
				"fieldname": "invoice_portion",
				"fieldtype": "Percent",
				"width": 80
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
		#
		# if self.filters.exclude_unpaid_invoices:
		# 	columns = [c for c in columns if not c.get('hide_if_exclude_unpaid')]

		return columns


def get_late_payment_deduction_percent(sales_commission_category, payment_days):
	deduction_percent = 0

	if sales_commission_category.late_payment_deduction and payment_days is not None:
		for d in sales_commission_category.late_payment_deduction:
			if cint(payment_days) > cint(d.days):
				deduction_percent = flt(d.deduction_percent)

	return deduction_percent


def execute(filters=None):
	return SalesPersonCommissionSummary(filters).run()


# TODO
# Credit Note Cases
# No negative commission on more deduction than net
# Write Off penalty
