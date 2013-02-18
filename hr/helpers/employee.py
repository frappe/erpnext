# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.model.doc import copy_common_fields

def update_employee_details(controller, method=None):
	"""update employee details in linked doctypes"""
	if method == "on_update" and controller.doc.doctype == "Employee":
		# update salary structure
		active_salary_structure = webnotes.conn.get_value("Salary Structure", 
			{"is_active": "Yes", "employee": controller.doc.name})
		if not active_salary_structure:
			return
		
		ss = webnotes.model_wrapper("Salary Structure", active_salary_structure)
		copy_common_fields(controller.doc, ss.doc)
		ss.save()
