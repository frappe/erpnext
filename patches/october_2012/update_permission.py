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
def execute():
	import webnotes
	webnotes.conn.sql("""
		delete from `tabDocPerm`
		where 
			role in ('Sales User', 'Sales Manager', 'Sales Master Manager', 
				'Purchase User', 'Purchase Manager', 'Purchase Master Manager')
			and parent = 'Sales and Purchase Return Tool'
	""")
	
	webnotes.conn.sql("""delete from `tabDocPerm` where ifnull(role, '') = ''""")
	
	if not webnotes.conn.sql("""select name from `tabDocPerm` where parent = 'Leave Application'
			and role = 'Employee' and permlevel = 1"""):
		from webnotes.model.code import get_obj
		from webnotes.model.doc import addchild
		leave_app = get_obj('DocType', 'Leave Application', with_children=1)
		ch = addchild(leave_app.doc, 'permissions', 'DocPerm')
		ch.role = 'Employee'
		ch.permlevel = 1
		ch.read = 1
		ch.save()