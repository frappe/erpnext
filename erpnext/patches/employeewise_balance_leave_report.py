"""
	This patch changes criteria name
	of search criteria "employeewise_balance_leave_report"
	from "Employeewise Balance Leave Report"
	to "Employee Leave Balance Report"
"""
def execute():
	from webnotes.model.doc import Document
	d = Document('Search Criteria', 'employeewise_balance_leave_report')
	d.criteria_name = 'Employee Leave Balance Report'
	d.description = 'Employeewise Balance Leave Report'
	d.save()