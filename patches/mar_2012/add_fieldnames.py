# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# do not run this patch
from __future__ import unicode_literals
def execute():
	import webnotes
	import webnotes.modules
	forbidden = ['%', "'", '"', '#', '*', '?', '`', '(', ')', '<', '>', '-',
	'\\', '/', '.', '&', '!', '@', '$', '^', '+']
	doctype_list = webnotes.conn.sql("SELECT name, module FROM `tabDocType`")
	for doctype, module in doctype_list:
		docfield_list = webnotes.conn.sql("""\
				SELECT name, label, fieldtype FROM `tabDocField`
				WHERE parent = %s AND IFNULL(fieldname, '') = ''""", doctype)
		field_type_count = {}
		count = 0
		for name, label, fieldtype in docfield_list:
			fieldname = None
			if label:
				temp_label = label
				if len(temp_label)==1:
					temp_label = fieldtype + temp_label
				
				fieldname = temp_label.lower().replace(' ', '_')
				if "<" in fieldname:
					count = field_type_count.setdefault(fieldtype, 0)
					fieldname = fieldtype.lower().replace(' ', '_') + str(count)
					field_type_count[fieldtype] = count + 1
			elif fieldtype:
				count = field_type_count.setdefault(fieldtype, 0)
				fieldname = fieldtype.lower().replace(' ', '_') + str(count)
				field_type_count[fieldtype] = count + 1

			if fieldname:
				for f in forbidden: fieldname = fieldname.replace(f, '')
				fieldname = fieldname.replace('__', '_')
				if fieldname.endswith('_'):
					fieldname = fieldname[:-1]
				if fieldname.startswith('_'):
					fieldname = fieldname[1:]
				#print fieldname
				webnotes.conn.sql("""\
						UPDATE `tabDocField` SET fieldname = %s
						WHERE name = %s""", (fieldname, name))
		webnotes.modules.export_doc('DocType', doctype)
