from webnotes.model.doc import Document

emp = Document(
	fielddata = {
		'doctype': 'Employee',
		'name': 'emp1',
		'employee_name': 'Nijil',
		'status': 'Active',
		'date_of_joining': '2011-01-01'
	}
)



l_all = Document(
	fielddata = {
		'doctype' : 'Leave Allocation',
		'name': 'l_all',
		'employee' : 'emp1',
		'leave_type' : 'Casual Leave',
		'posting_date': '2011-03-01',
		'fiscal_year': '2011-2012',
		'total_leaves_allocated': 20,
		'docstatus': 1
	}
)

l_app1 = Document(
	fielddata = {
		'doctype' : 'Leave Application',
		'name': 'l_app1',
		'employee' : 'emp1',
		'leave_type' : 'Casual Leave',
		'posting_date': '2011-03-01',
		'fiscal_year': '2011-2012',
		'from_date': '2011-08-01',
		'to_date': '2011-08-02',
		'total_leave_days': 2
	}
)

l_app2 = Document(
	fielddata = {
		'doctype' : 'Leave Application',
		'name': 'l_app2',
		'employee' : 'emp1',
		'leave_type' : 'Casual Leave',
		'posting_date': '2011-03-01',
		'fiscal_year': '2011-2012',
		'from_date': '2011-08-15',
		'to_date': '2011-08-17',
		'total_leave_days': 3
	}
)
