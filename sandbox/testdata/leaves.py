# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
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
