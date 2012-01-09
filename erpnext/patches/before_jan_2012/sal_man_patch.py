
def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	sql = webnotes.conn.sql

	reload_doc('hr', 'doctype', 'salary_manager')
	sql("delete from `tabDocField` where parent = 'Salary Manager' and fieldname = 'employment_type'")
