from __future__ import unicode_literals
import webnotes

def execute():
	from webnotes.widgets.form.assign_to import add
	for t in webnotes.conn.sql("""select * from tabTask 
		where ifnull(allocated_to, '')!=''""", as_dict=1):
		add({
			'doctype': "Task",
			'name': t['name'],
			'assign_to': t['allocated_to'],
			'assigned_by': t['owner'],
			'description': t['subject'],
			'date': t['creation'],
			"no_notification": True
		})