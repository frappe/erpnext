# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import json

def execute():
	doctypes_child_tables_map = {}

	# Get all saved report columns
	columns = webnotes.conn.sql("""select defvalue, defkey from `tabDefaultValue` where 
		defkey like '_list_settings:%'""")

	# Make map of doctype and child tables
	for value, key in columns:
		doctype = key.split(':')[-1]
		child_tables = webnotes.conn.sql_list("""select options from `tabDocField` 
			where parent=%s and fieldtype='Table'""", doctype)
		doctypes_child_tables_map.setdefault(doctype, child_tables + [doctype])

	# If defvalue contains child doctypes then only append the column
	for value, key in columns:
		new_columns = []
		column_doctype = key.split(':')[-1]
		for field, field_doctype in json.loads(value):
			if field_doctype in doctypes_child_tables_map.get(column_doctype):
				new_columns.append([field, field_doctype])

		if new_columns:
			webnotes.conn.sql("""update `tabDefaultValue` set defvalue=%s 
				where defkey=%s""" % ('%s', '%s'), (json.dumps(new_columns), key))
		else:
			webnotes.conn.sql("""delete from `tabDefaultValue` where defkey=%s""", key)