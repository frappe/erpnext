import frappe
from frappe import _

from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import (
	get_result,
	get_tds_docs,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	if filters.get("party_type") == "Customer":
		party_naming_by = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	else:
		party_naming_by = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	filters.update({"naming_series": party_naming_by})

	validate_filters(filters)

	columns = get_columns(filters)
	(
		tds_accounts,
		tax_category_map,
		net_total_map,
	) = get_tds_docs(filters)

	res = get_result(filters, tds_accounts, tax_category_map, net_total_map)
	final_result = group_by_party_and_category(res, filters)

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
		key = (row.get("party_type"), row.get("party"), row.get("tax_withholding_category"))
		party_category_wise_map.setdefault(
			key,
			{
				"pan": row.get("pan"),
				"tax_id": row.get("tax_id"),
				"party": row.get("party"),
				"party_type": row.get("party_type"),
				"party_name": row.get("party_name"),
				"tax_withholding_category": row.get("tax_withholding_category"),
				"party_entity_type": row.get("party_entity_type"),
				"rate": row.get("rate"),
				"total_amount": 0.0,
				"tax_amount": 0.0,
			},
		)

		party_category_wise_map.get(key)["total_amount"] += row.get("total_amount", 0.0)
		party_category_wise_map.get(key)["tax_amount"] += row.get("tax_amount", 0.0)

	final_result = get_final_result(party_category_wise_map)

	return final_result


def get_final_result(party_category_wise_map):
	out = []
	for _key, value in party_category_wise_map.items():
		out.append(value)

	return out


def get_columns(filters):
	pan = "pan" if frappe.db.has_column(filters.party_type, "pan") else "tax_id"
	columns = [
		{"label": _(frappe.unscrub(pan)), "fieldname": pan, "fieldtype": "Data", "width": 90},
		{
			"label": _(filters.get("party_type")),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 180,
		},
	]

	if filters.naming_series == "Naming Series":
		columns.append(
			{
				"label": _(filters.party_type + " Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 180,
			}
		)

	columns.extend(
		[
			{
				"label": _("Tax Withholding Category"),
				"options": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"width": 180,
			},
			{
				"label": _(f"{filters.get('party_type', 'Party')} Type"),
				"fieldname": "party_entity_type",
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"label": _("TDS Rate %") if filters.get("party_type") == "Supplier" else _("TCS Rate %"),
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
	)

	return columns
