import frappe
from frappe import _

from erpnext.accounts.report.tds_payable_monthly.tds_payable_monthly import (
	get_result,
	get_tds_docs,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	validate_filters(filters)

	filters.naming_series = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	columns = get_columns(filters)
	tds_docs, tds_accounts, tax_category_map = get_tds_docs(filters)

	res = get_result(filters, tds_docs, tds_accounts, tax_category_map)
	final_result = group_by_supplier_and_category(res)

	return columns, final_result


def validate_filters(filters):
	"""Validate if dates are properly set and lie in the same fiscal year"""
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	from_year = get_fiscal_year(filters.from_date)[0]
	to_year = get_fiscal_year(filters.to_date)[0]
	if from_year != to_year:
		frappe.throw(_("From Date and To Date lie in different Fiscal Year"))

	filters["fiscal_year"] = from_year


def group_by_supplier_and_category(data):
	supplier_category_wise_map = {}

	for row in data:
		supplier_category_wise_map.setdefault(
			(row.get("supplier"), row.get("section_code")),
			{
				"pan": row.get("pan"),
				"supplier": row.get("supplier"),
				"supplier_name": row.get("supplier_name"),
				"section_code": row.get("section_code"),
				"entity_type": row.get("entity_type"),
				"tds_rate": row.get("tds_rate"),
				"total_amount_credited": 0.0,
				"tds_deducted": 0.0,
			},
		)

		supplier_category_wise_map.get((row.get("supplier"), row.get("section_code")))[
			"total_amount_credited"
		] += row.get("total_amount_credited", 0.0)

		supplier_category_wise_map.get((row.get("supplier"), row.get("section_code")))[
			"tds_deducted"
		] += row.get("tds_deducted", 0.0)

	final_result = get_final_result(supplier_category_wise_map)

	return final_result


def get_final_result(supplier_category_wise_map):
	out = []
	for key, value in supplier_category_wise_map.items():
		out.append(value)

	return out


def get_columns(filters):
	columns = [
		{"label": _("PAN"), "fieldname": "pan", "fieldtype": "Data", "width": 90},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"width": 180,
		},
	]

	if filters.naming_series == "Naming Series":
		columns.append(
			{"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180}
		)

	columns.extend(
		[
			{
				"label": _("Section Code"),
				"options": "Tax Withholding Category",
				"fieldname": "section_code",
				"fieldtype": "Link",
				"width": 180,
			},
			{"label": _("Entity Type"), "fieldname": "entity_type", "fieldtype": "Data", "width": 180},
			{"label": _("TDS Rate %"), "fieldname": "tds_rate", "fieldtype": "Percent", "width": 90},
			{
				"label": _("Total Amount Credited"),
				"fieldname": "total_amount_credited",
				"fieldtype": "Float",
				"width": 90,
			},
			{
				"label": _("Amount of TDS Deducted"),
				"fieldname": "tds_deducted",
				"fieldtype": "Float",
				"width": 90,
			},
		]
	)

	return columns
