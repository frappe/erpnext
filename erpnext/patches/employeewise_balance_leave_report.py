"""
	This patch changes criteria name
	of search criteria "employeewise_balance_leave_report"
	from "Employeewise Balance Leave Report"
	to "Employee Leave Balance Report"
"""
def execute():
	from webnotes.model.doc import Document
	from webnotes.modules.module_manager import reload_doc
	reload_doc('hr', 'search_criteria', 'employeewise_balance_leave_report')
	d = Document('Search Criteria', 'employeewise_balance_leave_report')
	d.criteria_name = 'Employee Leave Balance Report'
	d.description = 'Employeewise Balance Leave Report'
	d.save()
