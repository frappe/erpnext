import json

import frappe

REFERENCE_REPORTS = [
	"Accounts Receivable",
	"Accounts Receivable Summary",
	"Accounts Payable",
	"Accounts Payable Summary",
	"Stock Ageing",
]


def execute():
	for report in REFERENCE_REPORTS:
		update_reference_reports(report)


def update_reference_reports(reference_report):
	reports = frappe.get_all(
		"Report", filters={"reference_report": reference_report}, fields={"json", "name"}
	)

	for report in reports:
		update_report_json(report)
		update_reference_reports(report.name)


def update_report_json(report):
	report_json = json.loads(report.json) if report.get("json") else {}
	report_filter = report_json.get("filters")

	if not report_filter:
		return

	keys_to_pop = [key for key in report_filter if key.startswith("range")]
	report_filter["range"] = ", ".join(str(report_filter.pop(key)) for key in keys_to_pop)

	frappe.db.set_value("Report", report.name, "json", json.dumps(report_json))
