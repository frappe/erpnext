import frappe
from frappe import _

from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import (
	_get_twc_additional_columns,
	get_tax_withholding_data,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	return _execute(filters)


def _execute(filters=None, additional_table_columns=None):
	validate_filters(filters)

	data = get_tax_withholding_data(filters, additional_table_columns)
	columns = get_columns(filters, additional_table_columns)

	final_result = group_by_party_and_category(data, filters, additional_table_columns)

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


def group_by_party_and_category(data, filters, additional_table_columns=None):
	party_category_wise_map = {}
	twc_additional_columns = _get_twc_additional_columns(additional_table_columns)

	for row in data:
		key = (row.get("party"), row.get("tax_withholding_category"))
		default_row = {
			"tax_id": row.get("tax_id"),
			"party": row.get("party"),
			"party_type": row.get("party_type"),
			"party_name": row.get("party_name"),
			"tax_withholding_category": row.get("tax_withholding_category"),
			"party_entity_type": row.get("party_entity_type"),
			"rate": row.get("rate"),
			"total_amount": 0.0,
			"tax_amount": 0.0,
		}
		if twc_additional_columns:
			for col in twc_additional_columns:
				default_row[col["fieldname"]] = row.get(col["fieldname"])

		party_category_wise_map.setdefault(key, default_row)

		party_category_wise_map[key]["total_amount"] += row.get("total_amount", 0.0)
		party_category_wise_map[key]["tax_amount"] += row.get("tax_amount", 0.0)

	final_result = get_final_result(party_category_wise_map)

	return final_result


def get_final_result(party_category_wise_map):
	out = []
	for _key, value in party_category_wise_map.items():
		out.append(value)

	return out


def get_columns(filters, additional_table_columns=None):
	tax_withholding_category_column = [
		{
			"label": _("Tax Withholding Category"),
			"options": "Tax Withholding Category",
			"fieldname": "tax_withholding_category",
			"fieldtype": "Link",
			"width": 180,
		},
	]
	if additional_table_columns:
		tax_withholding_category_column += additional_table_columns
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
		*tax_withholding_category_column,
		{
			"label": _(f"{filters.get('party_type', 'Party')} Type"),
			"fieldname": "party_entity_type",
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
			"label": _("Total Taxable Amount"),
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
