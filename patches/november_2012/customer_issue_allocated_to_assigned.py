# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	from webnotes.widgets.form.assign_to import add
	# clear old customer issue todos
	webnotes.conn.sql("""delete from tabToDo where reference_type='Customer Issue'""")
	webnotes.conn.sql("""delete from tabComment where comment like '%Form/Customer Issue%'""")
	for t in webnotes.conn.sql("""select * from `tabCustomer Issue` 
		where ifnull(allocated_to, '')!='' and ifnull(status, "")="Open" """, as_dict=1):
		add({
			'doctype': "Customer Issue",
			'name': t['name'],
			'assign_to': t['allocated_to'],
			'assigned_by': t['owner'],
			'description': t['complaint'],
			'date': t['creation'],
			'no_notification': True
		})