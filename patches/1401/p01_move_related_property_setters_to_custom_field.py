# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.model.meta import get_field

def execute():
	webnotes.reload_doc("core", "doctype", "custom_field")
	
	custom_fields = {}
	for cf in webnotes.conn.sql("""select dt, fieldname from `tabCustom Field`""", as_dict=1):
		custom_fields.setdefault(cf.dt, []).append(cf.fieldname)
		
	delete_list = []
	for ps in webnotes.conn.sql("""select * from `tabProperty Setter`""", as_dict=1):
		if ps.field_name in custom_fields.get(ps.doc_type, []):
			
			if ps.property == "previous_field":
				property_name = "insert_after"
				
				field_meta = get_field(ps.doc_type, ps.value)
				property_value = field_meta.label if field_meta else ""
			else:
				property_name = ps.property
				property_value  =ps.value
	
			webnotes.conn.sql("""update `tabCustom Field` 
				set %s=%s where dt=%s and fieldname=%s""" % (property_name,	'%s', '%s', '%s'), 
				(property_value, ps.doc_type, ps.field_name))
				
			delete_list.append(ps.name)
			
	if delete_list:
		webnotes.conn.sql("""delete from `tabProperty Setter` where name in (%s)""" % 
			', '.join(['%s']*len(delete_list)), tuple(delete_list))