# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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


def get_conditions(filters):
	conditions = "1=1"
	if filters.get("from_date"):
		conditions += " and a.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and a.posting_date <= %(to_date)s"
	if filters.get("company"):
		conditions += " and a.company=%(company)s"
	if filters.get("customer"):
		conditions += " and a.customer = %(customer)s"
	if filters.get("owner"):
		conditions += " and a.owner = %(owner)s"
	if filters.get("is_pos"):
		conditions += " and a.is_pos = %(is_pos)s"
	return conditions


def get_pos_invoice_data(filters):
	conditions = get_conditions(filters)
	result = frappe.db.sql(
		f"""
		SELECT 
			posting_date, owner, sum(net_total) as "net_total", sum(total_taxes) as "total_taxes",
			sum(paid_amount) as "paid_amount", sum(outstanding_amount) as "outstanding_amount",
			mode_of_payment, warehouse, cost_center 
		FROM (
			SELECT 
				parent, item_code, sum(amount) as "base_total", warehouse, cost_center 
			FROM `tabSales Invoice Item`
			GROUP BY parent, item_code, warehouse, cost_center
		) t1 
		LEFT JOIN (
			SELECT parent, mode_of_payment 
			FROM `tabSales Invoice Payment` 
			GROUP BY parent, mode_of_payment -- Added mode_of_payment to GROUP BY clause
		) t3 
		ON (t3.parent = t1.parent)
		JOIN (
			SELECT 
				docstatus, company, is_pos, name, posting_date, owner, 
				sum(base_total) as "base_total", sum(net_total) as "net_total", 
				sum(total_taxes_and_charges) as "total_taxes", 
				sum(base_paid_amount) as "paid_amount", 
				sum(outstanding_amount) as "outstanding_amount"
			FROM `tabSales Invoice`
			GROUP BY name, posting_date, owner, docstatus, company, is_pos
		) a 
		ON (t1.parent = a.name AND t1.base_total = a.base_total)
		WHERE a.docstatus = 1
		AND {conditions}
		GROUP BY owner, posting_date, warehouse, cost_center, mode_of_payment
		""",
		filters,
		as_dict=1,
	)
	return result


def get_sales_invoice_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		f"""
		select
			a.posting_date, a.owner,
			sum(a.net_total) as "net_total",
			sum(a.total_taxes_and_charges) as "total_taxes",
			sum(a.base_paid_amount) as "paid_amount",
			sum(a.outstanding_amount) as "outstanding_amount"
		from `tabSales Invoice` a
		where a.docstatus = 1
			and {conditions}
			group by
			a.owner, a.posting_date
	""",
		filters,
		as_dict=1,
	)


def get_mode_of_payments(filters):
	mode_of_payments = {}
	invoice_list = get_invoices(filters)
	invoice_list_names = ",".join("'" + invoice["name"] + "'" for invoice in invoice_list)
	if invoice_list:
		inv_mop = frappe.db.sql(
			f"""select a.owner,a.posting_date, ifnull(b.mode_of_payment, '') as mode_of_payment
			from `tabSales Invoice` a, `tabSales Invoice Payment` b
			where a.name = b.parent
			and a.docstatus = 1
			and a.name in ({invoice_list_names})
			union
			select a.owner,a.posting_date, ifnull(b.mode_of_payment, '') as mode_of_payment
			from `tabSales Invoice` a, `tabPayment Entry` b,`tabPayment Entry Reference` c
			where a.name = c.reference_name
			and b.name = c.parent
			and b.docstatus = 1
			and a.name in ({invoice_list_names})
			union
			select a.owner, a.posting_date,
			ifnull(a.voucher_type,'') as mode_of_payment
			from `tabJournal Entry` a, `tabJournal Entry Account` b
			where a.name = b.parent
			and a.docstatus = 1
			and b.reference_type = 'Sales Invoice'
			and b.reference_name in ({invoice_list_names})
			""",
			as_dict=1,
		)
		for d in inv_mop:
			mode_of_payments.setdefault(d["owner"] + cstr(d["posting_date"]), []).append(d.mode_of_payment)
	return mode_of_payments


def get_invoices(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		f"""select a.name
		from `tabSales Invoice` a
		where a.docstatus = 1 and {conditions}""",
		filters,
		as_dict=1,
	)


def get_mode_of_payment_details(filters):
	mode_of_payment_details = {}
	invoice_list = get_invoices(filters)
	invoice_list_names = ",".join("'" + invoice["name"] + "'" for invoice in invoice_list)
	if invoice_list:
		inv_mop_detail = frappe.db.sql(
			f"""
			SELECT t.owner,
				t.posting_date,
				t.mode_of_payment,
				SUM(t.paid_amount) AS paid_amount
			FROM (
				-- First Subquery: Sales Invoice and Payment
				SELECT a.owner, a.posting_date,
					COALESCE(b.mode_of_payment, '') AS mode_of_payment, 
					SUM(b.base_amount) AS paid_amount
				FROM `tabSales Invoice` a
				JOIN `tabSales Invoice Payment` b ON a.name = b.parent
				WHERE a.docstatus = 1
				AND a.name IN ({invoice_list_names})
				GROUP BY a.owner, a.posting_date, b.mode_of_payment

				UNION ALL
				
				-- Second Subquery: Sales Invoice and Payment Entry
				SELECT a.owner, a.posting_date,
					COALESCE(b.mode_of_payment, '') AS mode_of_payment, 
					SUM(c.allocated_amount) AS paid_amount
				FROM `tabSales Invoice` a
				JOIN `tabPayment Entry Reference` c ON a.name = c.reference_name
				JOIN `tabPayment Entry` b ON b.name = c.parent
				WHERE b.docstatus = 1
				AND a.name IN ({invoice_list_names})
				GROUP BY a.owner, a.posting_date, b.mode_of_payment

				UNION ALL
				
				-- Third Subquery: Journal Entry and Journal Entry Account
				SELECT a.owner, a.posting_date,
					COALESCE(a.voucher_type, '') AS mode_of_payment, 
					SUM(b.credit) AS paid_amount
				FROM `tabJournal Entry` a
				JOIN `tabJournal Entry Account` b ON a.name = b.parent
				WHERE a.docstatus = 1
				AND b.reference_type = 'Sales Invoice'
				AND b.reference_name IN ({invoice_list_names})
				GROUP BY a.owner, a.posting_date, a.voucher_type
			) t
			GROUP BY t.owner, t.posting_date, t.mode_of_payment
			""",
			as_dict=1,
		)

		inv_change_amount = frappe.db.sql(
			f"""select a.owner, a.posting_date,
			ifnull(b.mode_of_payment, '') as mode_of_payment, sum(a.base_change_amount) as change_amount
			from `tabSales Invoice` a, `tabSales Invoice Payment` b
			where a.name = b.parent
			and a.name in ({invoice_list_names})
			and b.type = 'Cash'
			and a.base_change_amount > 0
			group by a.owner, a.posting_date, mode_of_payment""",
			as_dict=1,
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
