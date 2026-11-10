import frappe

REPORTS = (
	"Accounts Receivable",
	"Accounts Payable",
	"Accounts Receivable Summary",
	"Accounts Payable Summary",
)


def execute():
	# filter `calculate_ageing_with` -> `age_as_on`, option "Today Date" -> "Today"
	_migrate("Auto Email Report", "filters", "report")
	_migrate("Dashboard Chart", "filters_json", "report_name", type_field="chart_type")
	_migrate("Number Card", "filters_json", "report_name", type_field="type")


def _migrate(doctype, filter_field, report_field, type_field=None):
	conditions = {report_field: ("in", REPORTS)}
	if type_field:
		conditions[type_field] = "Report"

	for row in frappe.get_all(doctype, filters=conditions, fields=["name", filter_field]):
		updated = _rewrite(row.get(filter_field))
		if updated is not None:
			frappe.db.set_value(doctype, row.name, filter_field, updated, update_modified=False)


def _rewrite(raw):
	if not raw:
		return None

	try:
		filters = frappe.parse_json(raw)
	except ValueError:
		return None

	if not isinstance(filters, dict) or "calculate_ageing_with" not in filters:
		return None

	filters["age_as_on"] = filters.pop("calculate_ageing_with")
	if filters["age_as_on"] == "Today Date":
		filters["age_as_on"] = "Today"

	return frappe.as_json(filters, indent=None)
