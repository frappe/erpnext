import webnotes

def set_doctype_permissions():
	
	# remove descriptions
	webnotes.conn.sql("update tabDocType set description=null")
		
	from webnotes.modules.module_manager import reload_doc
	reload_doc('core','doctype','custom_script')
	reload_doc('core','doctype','custom_field')
	reload_doc('core','doctype','property_setter')
	
	# remove admin rights
	webnotes.conn.sql("delete from tabUserRole where role in ('Administrator','Customer','Supplier') and parent!='Administrator'")	
	
	# create custom scripts
	create_custom_scripts()

	# remove script fields
	reload_doc('core','doctype','doctype')

	# allow sys manager to read doctype, custom script
	allow_sys_manager()
	
def create_custom_scripts():
	
	cs_list = webnotes.conn.sql("select name, server_code, client_script from tabDocType where ifnull(server_code,'')!='' or ifnull(client_script,'')!=''")
	
	from webnotes.model.doc import Document
	
	for c in cs_list:
		if c[1]:
			cs = Document('Custom Script')
			cs.dt = c[0]
			cs.script_type = 'Server'
			cs.script = c[1]
			try:
				cs.save(1)
			except NameError:
				pass

		if c[2]:
			cs = Document('Custom Script')
			cs.dt = c[0]
			cs.script_type = 'Client'
			cs.script = c[2]
			try:
				cs.save(1)
			except NameError:
				pass

def allow_sys_manager():
	from webnotes.model.doc import Document

	if not webnotes.conn.sql("select name from tabDocPerm where parent='DocType' and role='System Manager' and `read`=1"):
		d = Document('DocPerm')
		d.parent = 'DocType'
		d.parenttype = 'DocType'
		d.parentfield = 'permissions'
		d.role = 'System Manager'
		d.read = 1
		d.save(1)

	
	if not webnotes.conn.sql("select name from tabDocPerm where parent='Custom Script' and role='System Manager' and `write`=1"):
		d = Document('DocPerm')
		d.parent = 'Custom Script'
		d.parenttype = 'DocType'
		d.parentfield = 'permissions'
		d.role = 'System Manager'
		d.read = 1
		d.write = 1
		d.create = 1
		d.save(1)