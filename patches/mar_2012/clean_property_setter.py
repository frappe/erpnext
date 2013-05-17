from __future__ import unicode_literals
import webnotes

def execute():
	"""
		* Remove unnecessary doctype properties
		* Remove docfield property setters if fieldname doesn't exist
		* Remove prev_field properties if value fieldname doesn't exist
	"""
	change_property_setter_fieldnames()
	clean_doctype_properties()
	clean_docfield_properties()

def change_property_setter_fieldnames():
	webnotes.reload_doc('core', 'doctype', 'property_setter')
	docfield_list = webnotes.conn.sql("""\
		SELECT name, fieldname FROM `tabDocField`""", as_list=1)
	custom_field_list = webnotes.conn.sql("""\
		SELECT name, fieldname FROM `tabCustom Field`""", as_list=1)
	field_list = docfield_list + custom_field_list
	property_setter_list = webnotes.conn.sql("""\
		SELECT name, doc_name, value, property
		FROM `tabProperty Setter`
		WHERE doctype_or_field='DocField'""")
	field_dict = dict(field_list)
	for name, doc_name, value, prop in property_setter_list:
		if doc_name in field_dict:
			webnotes.conn.sql("""\
				UPDATE `tabProperty Setter`
				SET field_name = %s
				WHERE name = %s""", (field_dict.get(doc_name), name))
		if value in field_dict and prop=='previous_field':
			webnotes.conn.sql("""\
				UPDATE `tabProperty Setter`
				SET value = %s
				WHERE name = %s""", (field_dict.get(value), name))

def clean_doctype_properties():
	desc = webnotes.conn.sql("DESC `tabDocType`", as_dict=1)
	property_list = '", "'.join([d.get('Field') for d in desc])
	webnotes.conn.sql("""\
		DELETE FROM `tabProperty Setter`
		WHERE doctype_or_field = 'DocType'
		AND property NOT IN ("%s")""" % property_list)
	
def clean_docfield_properties():
	delete_list_1 = webnotes.conn.sql("""\
		SELECT name FROM `tabProperty Setter` ps
		WHERE doctype_or_field = 'DocField'
		AND NOT EXISTS (
			SELECT fieldname FROM `tabDocField` df
			WHERE df.parent = ps.doc_type
			AND df.fieldname = ps.field_name
		) AND NOT EXISTS (
			SELECT fieldname FROM `tabCustom Field` cf
			WHERE cf.dt = ps.doc_type
			AND cf.fieldname = ps.field_name
		)""")
	
	delete_list_2 = webnotes.conn.sql("""\
		SELECT name FROM `tabProperty Setter` ps
		WHERE doctype_or_field = 'DocField'
		AND property = 'previous_field'
		AND NOT EXISTS (
			SELECT fieldname FROM `tabDocField` df
			WHERE df.parent = ps.doc_type
			AND df.fieldname = ps.value
		) AND NOT EXISTS (
			SELECT fieldname FROM `tabCustom Field` cf
			WHERE cf.dt = ps.doc_type
			AND cf.fieldname = ps.value
		)""")

	delete_list = [d[0] for d in delete_list_1] + [d[0] for d in delete_list_2]

	webnotes.conn.sql("""\
		DELETE FROM `tabProperty Setter`
		WHERE NAME IN ("%s")""" % '", "'.join(delete_list))
