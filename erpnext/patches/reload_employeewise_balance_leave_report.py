def execute(self):
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	reload_doc('hr', 'search_criteria', 'employeewise_balance_leave_report')
