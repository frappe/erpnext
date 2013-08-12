# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	for employee in webnotes.conn.sql_list("""select name from `tabEmployee` where ifnull(date_of_birth, '')!=''"""):
		obj = webnotes.get_obj("Employee", employee)
		obj.update_dob_event()
		