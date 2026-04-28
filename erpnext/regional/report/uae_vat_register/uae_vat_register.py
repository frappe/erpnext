# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	doc_type = filters.get("doc_type") or "Sales Invoice"
	is_sales = doc_type == "Sales Invoice"
	item_wise = bool(filters.get("item_wise"))

	columns = [
		{
			"label": _("Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": doc_type,
			"width": 180,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Customer") if is_sales else _("Supplier"),
			"fieldname": "party",
			"fieldtype": "Link",
			"options": "Customer" if is_sales else "Supplier",
			"width": 150,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 130,
		},
	]
	if is_sales:
		columns.append({"label": _("Emirate"), "fieldname": "emirate", "fieldtype": "Data", "width": 110})
	else:
		columns.append(
			{
				"label": _("Reverse Charge"),
				"fieldname": "reverse_charge",
				"fieldtype": "Data",
				"width": 110,
			}
		)
	if item_wise:
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 150,
				},
				{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
				{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
			]
		)
	else:
		columns.append({"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80})
	columns.extend(
		[
			{"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("VAT Amount"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Total Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Currency",
				"width": 120,
			},
		]
	)
	return columns


def get_data(filters):
	doc_type = filters.get("doc_type") or "Sales Invoice"
	if doc_type == "Sales Invoice":
		return fetch_sales_rows(filters)
	if doc_type == "Purchase Invoice":
		return fetch_purchase_rows(filters)
	return []


def fetch_sales_rows(filters):
	conditions, params = build_conditions(filters)
	category_clause = sales_category_clause(filters.get("category"))

	emirate_clause = ""
	if filters.get("vat"):
		emirate_clause = "AND s.vat_emirate = %(vat)s"
		params["vat"] = filters["vat"]

	if filters.get("item_wise"):
		return frappe.db.sql(
			f"""
			SELECT
				s.name, s.posting_date, s.customer AS party,
				COALESCE(i.cost_center, s.cost_center) AS cost_center,
				s.vat_emirate AS emirate,
				i.item_code, i.qty, i.rate,
				i.base_net_amount AS net_amount,
				i.tax_amount AS vat_amount,
				(i.base_net_amount + COALESCE(i.tax_amount, 0)) AS total_amount
			FROM `tabSales Invoice` s
			INNER JOIN `tabSales Invoice Item` i ON i.parent = s.name
			WHERE s.docstatus = 1 {conditions} {category_clause} {emirate_clause}
			ORDER BY s.posting_date, s.name, i.idx
			""",
			params,
			as_dict=True,
		)

	return frappe.db.sql(
		f"""
		SELECT
			s.name, s.posting_date, s.customer AS party, s.cost_center,
			s.vat_emirate AS emirate,
			SUM(i.qty) AS qty,
			SUM(i.base_net_amount) AS net_amount,
			SUM(i.tax_amount) AS vat_amount,
			SUM(i.base_net_amount + COALESCE(i.tax_amount, 0)) AS total_amount
		FROM `tabSales Invoice` s
		INNER JOIN `tabSales Invoice Item` i ON i.parent = s.name
		WHERE s.docstatus = 1 {conditions} {category_clause} {emirate_clause}
		GROUP BY s.name, s.posting_date, s.customer, s.cost_center, s.vat_emirate
		ORDER BY s.posting_date, s.name
		""",
		params,
		as_dict=True,
	)


def fetch_purchase_rows(filters):
	conditions, params = build_conditions(filters)

	rc_clause = ""
	if filters.get("reverse_charge") in ("Y", "N"):
		rc_clause = "AND s.reverse_charge = %(reverse_charge)s"
		params["reverse_charge"] = filters["reverse_charge"]

	if filters.get("item_wise"):
		return frappe.db.sql(
			f"""
			SELECT
				s.name, s.posting_date, s.supplier AS party,
				COALESCE(i.cost_center, s.cost_center) AS cost_center,
				s.reverse_charge,
				i.item_code, i.qty, i.rate,
				i.base_net_amount AS net_amount,
				i.tax_amount AS vat_amount,
				(i.base_net_amount + COALESCE(i.tax_amount, 0)) AS total_amount
			FROM `tabPurchase Invoice` s
			INNER JOIN `tabPurchase Invoice Item` i ON i.parent = s.name
			WHERE s.docstatus = 1 {conditions} {rc_clause}
			ORDER BY s.posting_date, s.name, i.idx
			""",
			params,
			as_dict=True,
		)

	return frappe.db.sql(
		f"""
		SELECT
			s.name, s.posting_date, s.supplier AS party, s.cost_center,
			s.reverse_charge,
			SUM(i.qty) AS qty,
			SUM(i.base_net_amount) AS net_amount,
			SUM(i.tax_amount) AS vat_amount,
			SUM(i.base_net_amount + COALESCE(i.tax_amount, 0)) AS total_amount
		FROM `tabPurchase Invoice` s
		INNER JOIN `tabPurchase Invoice Item` i ON i.parent = s.name
		WHERE s.docstatus = 1 {conditions} {rc_clause}
		GROUP BY s.name, s.posting_date, s.supplier, s.cost_center, s.reverse_charge
		ORDER BY s.posting_date, s.name
		""",
		params,
		as_dict=True,
	)


def build_conditions(filters):
	conditions = ""
	params = {}
	if filters.get("company"):
		conditions += " AND s.company = %(company)s"
		params["company"] = filters["company"]
	if filters.get("from_date"):
		conditions += " AND s.posting_date >= %(from_date)s"
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions += " AND s.posting_date <= %(to_date)s"
		params["to_date"] = filters["to_date"]
	return conditions, params


def sales_category_clause(category):
	if category == "Standard":
		return "AND i.is_zero_rated != 1 AND i.is_exempt != 1"
	if category == "Zero Rated":
		return "AND i.is_zero_rated = 1"
	if category == "Exempt Rated":
		return "AND i.is_exempt = 1"
	return ""
