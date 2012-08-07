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

import webnotes
from webnotes.model.doc import Document

@webnotes.whitelist()
def get(arg=None):
	"""get todo list"""
	return webnotes.conn.sql("""select name, owner, description, date,
		priority, checked, reference_type, reference_name, assigned_by
		from `tabToDo` where (owner=%s or assigned_by=%s)
		order by field(priority, 'High', 'Medium', 'Low') asc, date asc""",
		(webnotes.session['user'], webnotes.session['user']), as_dict=1)

@webnotes.whitelist()		
def edit(arg=None):
	import markdown2
	args = webnotes.form_dict

	d = Document('ToDo', args.get('name') or None)
	d.description = args['description']
	d.date = args['date']
	d.priority = args['priority']
	d.checked = args.get('checked', 0)
	if not d.owner: d.owner = webnotes.session['user']
	d.save(not args.get('name') and 1 or 0)

	if args.get('name') and d.checked:
		notify_assignment(d)

	return d.name

@webnotes.whitelist()
def delete(arg=None):
	name = webnotes.form_dict['name']
	d = Document('ToDo', name)
	if d and d.name:
		notify_assignment(d)
	webnotes.conn.sql("delete from `tabToDo` where name = %s", name)

def notify_assignment(d):
	doc_type = d.reference_type
	doc_name = d.reference_name
	assigned_by = d.assigned_by
	
	if doc_type and doc_name and assigned_by:
		from webnotes.widgets.form import assign_to
		assign_to.notify_assignment(assigned_by, d.owner, doc_type, doc_name)
		