# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	from webnotes.widgets.form.assign_to import add
	for t in webnotes.conn.sql("""select * from tabQuotation 
		where ifnull(contact_by, '')!=''""", as_dict=1):
		add({
			'doctype': "Quotation",
			'name': t['name'],
			'assign_to': t['contact_by'],
			'assigned_by': t['owner'],
			'description': "Contact regarding quotation.",
			'date': t['creation'],
			"no_notification": True
		})