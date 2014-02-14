# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "custom_field")
	
	cf_doclist = webnotes.get_doctype("Custom Field")

	delete_list = []
	for d in webnotes.conn.sql("""select cf.name as cf_name, ps.property, 
			ps.value, ps.name as ps_name
		from `tabProperty Setter` ps, `tabCustom Field` cf
		where ps.doctype_or_field = 'DocField' and ps.property != 'previous_field'
		and ps.doc_type=cf.dt and ps.field_name=cf.fieldname""", as_dict=1):
			if cf_doclist.get_field(d.property):
				webnotes.conn.sql("""update `tabCustom Field` 
					set `%s`=%s where name=%s""" % (d.property, '%s', '%s'), (d.value, d.cf_name))
				
				delete_list.append(d.ps_name)
	
	if delete_list:
		webnotes.conn.sql("""delete from `tabProperty Setter` where name in (%s)""" % 
			', '.join(['%s']*len(delete_list)), tuple(delete_list))