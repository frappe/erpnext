import json

import frappe


def execute():
	update_reference_report("Accounts Receivable")


def update_reference_report(reference_report):
	reports = frappe.get_all(
		"Report", filters={"reference_report": reference_report}, fields={"json", "name"}
	)

	for report in reports:
		update_report_json(report)
		update_reference_report(report.name)


def update_report_json(report):
	report_json = json.loads(report.json)
	report_filter = report_json.get("filters")

	age_range_keys = [f"range{i}" for i in range(1, 6) if report_filter.get(f"range{i}")]

	report_filter["age_range"] = ", ".join(str(report_filter.get(key)) for key in age_range_keys)

	for age_range in age_range_keys:
		del report_filter[age_range]

	report_json["filters"] = report_filter
	frappe.db.set_value("Report", report.name, "json", json.dumps(report_json))
