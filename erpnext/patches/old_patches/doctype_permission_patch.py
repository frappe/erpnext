# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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