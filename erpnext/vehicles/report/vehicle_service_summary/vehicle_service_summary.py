# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from erpnext.projects.report.project_sales_summary.project_sales_summary import ProjectSalesSummaryReport


def execute(filters=None):
	return ProjectSalesSummaryReport(filters, is_vehicle_service=True).run()
