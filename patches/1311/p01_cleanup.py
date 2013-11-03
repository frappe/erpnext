import webnotes

def execute():
	from core.doctype.custom_field.custom_field import delete_and_create_custom_field_if_values_exist
	delete_and_create_custom_field_if_values_exist("Material Request", 
		{"fieldtype":"Text", "fieldname":"remark", "label":"Remarks","insert_after":"Fiscal Year"})