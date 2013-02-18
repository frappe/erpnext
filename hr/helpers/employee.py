# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

def update_employee_details(controller, method=None):
	"""update employee details in linked doctypes"""
	if method == "on_update" and controller.doc.doctype == "Employee":
		# update salary structure
		active_salary_structure = webnotes.conn.get_value("Salary Structure", 
			{"is_active": "Yes", "employee": controller.doc.name})
		if not active_salary_structure:
			return
		
		ss = webnotes.model_wrapper("Salary Structure", active_salary_structure)
		ss_doctype = webnotes.get_doctype("Salary Structure")
		update = False
		for fieldname, value in controller.doc.fields.items():
			if ss_doctype.get_field(fieldname) and ss.doc.fields[fieldname] != value:
				ss.doc.fields[fieldname] = value
				update = True
				
		if update:
			ss.save()
		
	