import frappe
from frappe import _

from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import (
	get_tax_withholding_data,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	validate_filters(filters)

	data = get_tax_withholding_data(filters)
	columns = get_columns(filters)

	final_result = group_by_party_and_category(data, filters)

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


def group_by_party_and_category(data, filters):
	party_category_wise_map = {}

	for row in data:
		party_category_wise_map.setdefault(
			(row.get("party"), row.get("section_code")),
			{
				"tax_id": row.get("tax_id"),
				"party": row.get("party"),
				"party_name": row.get("party_name"),
				"section_code": row.get("section_code"),
				"entity_type": row.get("entity_type"),
				"rate": row.get("rate"),
				"total_amount": 0.0,
				"tax_amount": 0.0,
			},
		)

		party_category_wise_map.get((row.get("party"), row.get("section_code")))["total_amount"] += row.get(
			"total_amount", 0.0
		)

		party_category_wise_map.get((row.get("party"), row.get("section_code")))["tax_amount"] += row.get(
			"tax_amount", 0.0
		)

	final_result = get_final_result(party_category_wise_map)

	return final_result


def get_final_result(party_category_wise_map):
	out = []
	for _key, value in party_category_wise_map.items():
		out.append(value)

	return out


def get_columns(filters):
	columns = [
		{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 90},
		{
			"label": _(filters.get("party_type")),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 180,
		},
		{
			"label": _(f"{filters.get('party_type', 'Party')} Name"),
			"fieldname": "party_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Section Code"),
			"options": "Tax Withholding Category",
			"fieldname": "section_code",
			"fieldtype": "Link",
			"width": 180,
		},
		{
			"label": _("Entity Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Tax Rate %"),
			"fieldname": "rate",
			"fieldtype": "Percent",
			"width": 120,
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Tax Amount"),
			"fieldname": "tax_amount",
			"fieldtype": "Float",
			"width": 120,
		},
	]

	return columns
