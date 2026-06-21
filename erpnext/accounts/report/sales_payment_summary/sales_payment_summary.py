# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Max, Sum
from frappe.utils import cstr


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = (
		get_pos_sales_payment_data(filters)
		if filters.get("is_pos")
		else get_sales_payment_data(filters, columns)
	)
	return columns, data


def get_pos_columns():
	return [
		_("Date") + ":Date:80",
		_("Owner") + ":Data:200",
		_("Payment Mode") + ":Data:240",
		_("Sales and Returns") + ":Currency/currency:120",
		_("Taxes") + ":Currency/currency:120",
		_("Payments") + ":Currency/currency:120",
		_("Warehouse") + ":Data:200",
		_("Cost Center") + ":Data:200",
	]


def get_columns(filters):
	if filters.get("is_pos"):
		return get_pos_columns()
	else:
		return [
			_("Date") + ":Date:80",
			_("Owner") + ":Data:200",
			_("Payment Mode") + ":Data:240",
			_("Sales and Returns") + ":Currency/currency:120",
			_("Taxes") + ":Currency/currency:120",
			_("Payments") + ":Currency/currency:120",
		]


def get_pos_sales_payment_data(filters):
	sales_invoice_data = get_pos_invoice_data(filters)
	data = [
		[
			row["posting_date"],
			row["owner"],
			row["mode_of_payment"],
			row["net_total"],
			row["total_taxes"],
			row["paid_amount"],
			row["warehouse"],
			row["cost_center"],
		]
		for row in sales_invoice_data
	]

	return data


def get_sales_payment_data(filters, columns):
	data = []
	show_payment_detail = False

	sales_invoice_data = get_sales_invoice_data(filters)
	mode_of_payments = get_mode_of_payments(filters)
	mode_of_payment_details = get_mode_of_payment_details(filters)

	if filters.get("payment_detail"):
		show_payment_detail = True
	else:
		show_payment_detail = False

	for inv in sales_invoice_data:
		owner_posting_date = inv["owner"] + cstr(inv["posting_date"])
		if show_payment_detail:
			row = [inv.posting_date, inv.owner, " ", inv.net_total, inv.total_taxes, 0]
			data.append(row)
			for mop_detail in mode_of_payment_details.get(owner_posting_date, []):
				row = [inv.posting_date, inv.owner, mop_detail[0], 0, 0, mop_detail[1], 0]
				data.append(row)
		else:
			total_payment = 0
			for mop_detail in mode_of_payment_details.get(owner_posting_date, []):
				total_payment = total_payment + mop_detail[1]
			row = [
				inv.posting_date,
				inv.owner,
				", ".join(mode_of_payments.get(owner_posting_date, [])),
				inv.net_total,
				inv.total_taxes,
				total_payment,
			]
			data.append(row)
	return data


def apply_conditions(query, a, filters):
	"""Apply the same filters get_conditions() used to build, as parameterized qb .where() clauses.

	`a` is the field source for the Sales Invoice columns -- either the `tabSales Invoice`
	DocType or a subquery aliased `a` that selects those columns. This mirrors the previous
	raw SQL where every predicate was keyed on the `a` alias.
	"""
	if filters.get("from_date"):
		query = query.where(a.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		query = query.where(a.posting_date <= filters.get("to_date"))
	if filters.get("company"):
		query = query.where(a.company == filters.get("company"))
	if filters.get("customer"):
		query = query.where(a.customer == filters.get("customer"))
	if filters.get("owner"):
		query = query.where(a.owner == filters.get("owner"))
	if filters.get("is_pos"):
		query = query.where(a.is_pos == filters.get("is_pos"))
	return query


def get_pos_invoice_data(filters):
	sii = frappe.qb.DocType("Sales Invoice Item")
	sip = frappe.qb.DocType("Sales Invoice Payment")
	si = frappe.qb.DocType("Sales Invoice")

	# t1: one row per invoice with the summed item base_total. warehouse/cost_center are line-level and
	# not grouped, so they are arbitrary per invoice -- Max() makes that pick deterministic and valid on
	# Postgres (item_code was selected but never consumed downstream, so it is dropped).
	t1 = (
		frappe.qb.from_(sii)
		.select(
			sii.parent,
			Sum(sii.amount).as_("base_total"),
			Max(sii.warehouse).as_("warehouse"),
			Max(sii.cost_center).as_("cost_center"),
		)
		.groupby(sii.parent)
	)

	# t3: mode_of_payment per invoice (arbitrary across an invoice's payment lines -> Max() to be valid)
	t3 = (
		frappe.qb.from_(sip)
		.select(sip.parent, Max(sip.mode_of_payment).as_("mode_of_payment"))
		.groupby(sip.parent)
	)

	# a: invoice-level aggregates. Grouped by the primary key (si.name), so the other plain si columns
	# (incl. customer, needed by the customer filter) are functionally dependent and valid on Postgres.
	a = (
		frappe.qb.from_(si)
		.select(
			si.docstatus,
			si.company,
			si.customer,
			si.is_pos,
			si.name,
			si.posting_date,
			si.owner,
			Sum(si.base_total).as_("base_total"),
			Sum(si.net_total).as_("net_total"),
			Sum(si.total_taxes_and_charges).as_("total_taxes"),
			Sum(si.base_paid_amount).as_("paid_amount"),
			Sum(si.outstanding_amount).as_("outstanding_amount"),
		)
		.groupby(si.name)
	)

	query = (
		frappe.qb.from_(t1)
		.left_join(t3)
		.on(t3.parent == t1.parent)
		.join(a)
		.on((t1.parent == a.name) & (t1.base_total == a.base_total))
		.select(
			a.posting_date,
			a.owner,
			Sum(a.net_total).as_("net_total"),
			Sum(a.total_taxes).as_("total_taxes"),
			Sum(a.paid_amount).as_("paid_amount"),
			Sum(a.outstanding_amount).as_("outstanding_amount"),
			# mode_of_payment/cost_center are not in the outer GROUP BY -> Max() (deterministic, both engines)
			Max(t3.mode_of_payment).as_("mode_of_payment"),
			t1.warehouse,
			Max(t1.cost_center).as_("cost_center"),
		)
		.where(a.docstatus == 1)
		.groupby(a.owner, a.posting_date, t1.warehouse)
	)
	query = apply_conditions(query, a, filters)

	return query.run(as_dict=True)


def get_sales_invoice_data(filters):
	a = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(a)
		.select(
			a.posting_date,
			a.owner,
			Sum(a.net_total).as_("net_total"),
			Sum(a.total_taxes_and_charges).as_("total_taxes"),
			Sum(a.base_paid_amount).as_("paid_amount"),
			Sum(a.outstanding_amount).as_("outstanding_amount"),
		)
		.where(a.docstatus == 1)
		.groupby(a.owner, a.posting_date)
	)
	query = apply_conditions(query, a, filters)
	return query.run(as_dict=True)


def get_mode_of_payments(filters):
	mode_of_payments = {}
	invoice_list = get_invoices(filters)
	invoice_names = [invoice["name"] for invoice in invoice_list]
	if invoice_list:
		# Branch 1: payments recorded directly on the Sales Invoice
		si1 = frappe.qb.DocType("Sales Invoice")
		sip = frappe.qb.DocType("Sales Invoice Payment")
		branch1 = (
			frappe.qb.from_(si1)
			.join(sip)
			.on(si1.name == sip.parent)
			.select(si1.owner, si1.posting_date, Coalesce(sip.mode_of_payment, "").as_("mode_of_payment"))
			.where(si1.docstatus == 1)
			.where(si1.name.isin(invoice_names))
		)

		# Branch 2: payments via Payment Entry referencing the invoice
		si2 = frappe.qb.DocType("Sales Invoice")
		pe = frappe.qb.DocType("Payment Entry")
		per = frappe.qb.DocType("Payment Entry Reference")
		branch2 = (
			frappe.qb.from_(si2)
			.join(per)
			.on(si2.name == per.reference_name)
			.join(pe)
			.on(pe.name == per.parent)
			.select(si2.owner, si2.posting_date, Coalesce(pe.mode_of_payment, "").as_("mode_of_payment"))
			.where(pe.docstatus == 1)
			.where(si2.name.isin(invoice_names))
		)

		# Branch 3: payments via Journal Entry referencing the invoice
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		branch3 = (
			frappe.qb.from_(je)
			.join(jea)
			.on(je.name == jea.parent)
			.select(je.owner, je.posting_date, Coalesce(je.voucher_type, "").as_("mode_of_payment"))
			.where(je.docstatus == 1)
			.where(jea.reference_type == "Sales Invoice")
			.where(jea.reference_name.isin(invoice_names))
		)

		# bare UNION => de-duplicated rows across the three branches
		inv_mop = (branch1.union(branch2).union(branch3)).run(as_dict=True)
		for d in inv_mop:
			mode_of_payments.setdefault(d["owner"] + cstr(d["posting_date"]), []).append(d.mode_of_payment)
	return mode_of_payments


def get_invoices(filters):
	a = frappe.qb.DocType("Sales Invoice")
	query = frappe.qb.from_(a).select(a.name).where(a.docstatus == 1)
	query = apply_conditions(query, a, filters)
	return query.run(as_dict=True)


def get_mode_of_payment_details(filters):
	mode_of_payment_details = {}
	invoice_list = get_invoices(filters)
	invoice_names = [invoice["name"] for invoice in invoice_list]
	if invoice_list:
		# Branch 1: amounts paid directly on the Sales Invoice
		si1 = frappe.qb.DocType("Sales Invoice")
		sip = frappe.qb.DocType("Sales Invoice Payment")
		mop1 = Coalesce(sip.mode_of_payment, "")
		branch1 = (
			frappe.qb.from_(si1)
			.join(sip)
			.on(si1.name == sip.parent)
			.select(
				si1.owner,
				si1.posting_date,
				mop1.as_("mode_of_payment"),
				Sum(sip.base_amount).as_("paid_amount"),
			)
			.where(si1.docstatus == 1)
			.where(si1.name.isin(invoice_names))
			.groupby(si1.owner, si1.posting_date, mop1)
		)

		# Branch 2: amounts allocated via Payment Entry
		si2 = frappe.qb.DocType("Sales Invoice")
		pe = frappe.qb.DocType("Payment Entry")
		per = frappe.qb.DocType("Payment Entry Reference")
		mop2 = Coalesce(pe.mode_of_payment, "")
		branch2 = (
			frappe.qb.from_(si2)
			.join(per)
			.on(si2.name == per.reference_name)
			.join(pe)
			.on(pe.name == per.parent)
			.select(
				si2.owner,
				si2.posting_date,
				mop2.as_("mode_of_payment"),
				Sum(per.allocated_amount).as_("paid_amount"),
			)
			.where(pe.docstatus == 1)
			.where(si2.name.isin(invoice_names))
			.groupby(si2.owner, si2.posting_date, mop2)
		)

		# Branch 3: amounts credited via Journal Entry
		je = frappe.qb.DocType("Journal Entry")
		jea = frappe.qb.DocType("Journal Entry Account")
		mop3 = Coalesce(je.voucher_type, "")
		branch3 = (
			frappe.qb.from_(je)
			.join(jea)
			.on(je.name == jea.parent)
			.select(
				je.owner, je.posting_date, mop3.as_("mode_of_payment"), Sum(jea.credit).as_("paid_amount")
			)
			.where(je.docstatus == 1)
			.where(jea.reference_type == "Sales Invoice")
			.where(jea.reference_name.isin(invoice_names))
			.groupby(je.owner, je.posting_date, mop3)
		)

		# bare UNION => de-duplicated rows; wrapped as subquery `t` for the outer re-aggregation
		t = branch1.union(branch2).union(branch3)
		inv_mop_detail = (
			frappe.qb.from_(t)
			.select(
				t.owner,
				t.posting_date,
				t.mode_of_payment,
				Sum(t.paid_amount).as_("paid_amount"),
			)
			.groupby(t.owner, t.posting_date, t.mode_of_payment)
			.run(as_dict=True)
		)

		# change amount paid back in cash, subtracted from the matching mode-of-payment detail below
		sic = frappe.qb.DocType("Sales Invoice")
		sipc = frappe.qb.DocType("Sales Invoice Payment")
		mopc = Coalesce(sipc.mode_of_payment, "")
		inv_change_amount = (
			frappe.qb.from_(sic)
			.join(sipc)
			.on(sic.name == sipc.parent)
			.select(
				sic.owner,
				sic.posting_date,
				mopc.as_("mode_of_payment"),
				Sum(sic.base_change_amount).as_("change_amount"),
			)
			.where(sic.name.isin(invoice_names))
			.where(sipc.type == "Cash")
			.where(sic.base_change_amount > 0)
			.groupby(sic.owner, sic.posting_date, mopc)
			.run(as_dict=True)
		)

		for d in inv_change_amount:
			for det in inv_mop_detail:
				if (
					det["owner"] == d["owner"]
					and det["posting_date"] == d["posting_date"]
					and det["mode_of_payment"] == d["mode_of_payment"]
				):
					paid_amount = det["paid_amount"] - d["change_amount"]
					det["paid_amount"] = paid_amount

		for d in inv_mop_detail:
			mode_of_payment_details.setdefault(d["owner"] + cstr(d["posting_date"]), []).append(
				(d.mode_of_payment, d.paid_amount)
			)

	return mode_of_payment_details
