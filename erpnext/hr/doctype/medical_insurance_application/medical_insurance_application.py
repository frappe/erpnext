# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, add_days, date_diff
from frappe.utils.csvutils import UnicodeWriter

class MedicalInsuranceApplication(Document):

	def validate(self):
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
			    self.docstatus = 1
			    self.docstatus = 2


@frappe.whitelist()
def get_template():
	pass
	# import urllib
	# urllib.urlretrieve("/home/frappe/frappe-bench/sites/t1/public/files/scan0089.pdf", "scan0089.pdf")
	# import urllib2
	# response = urllib2.urlopen('/home/frappe/frappe-bench/sites/t1/public/files/scan0089.pdf')
	# frappe.local.response.filename = "Medical_Declaration_Form_V1.2016.pdf"
	# with open("/home/frappe/frappe-bench/sites/t1/public/files/Medical_Declaration_Form_V1.2016.pdf", "rb") as fileobj:
	# 	filedata = fileobj.read()
	# frappe.local.response.filecontent = filedata
	# frappe.local.response.type = "download"
	# frappe.utils.response.download_private_file("/files/scan0089.pdf")
	# frappe.utils.file_manager.download_file("public/files/scan0089.pdf")
	# frappe.local.response["type"] = "download"
	# frappe.local.response["filename"] = "scan0089.pdf"
	# frappe.local.response["filecontent"] = ""
	# frappe.local.response["location"] = "public/files"
	# if not frappe.has_permission("Attendance", "create"):
	# 	raise frappe.PermissionError

	# args = frappe.local.form_dict

	# w = UnicodeWriter()
	# # w = add_header(w)

	# # w = add_data(w, args)

	# # write out response as a type csv
	# frappe.response['result'] = cstr(w.getvalue())
	# frappe.response['type'] = 'csv'
	# frappe.response['doctype'] = "Medical Insurance Application"



def get_permission_query_conditions(user):
	pass	
	# if not user: user = frappe.session.user
	# employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	# if employees:
	# 	query = ""
	# 	employee = frappe.get_doc('Employee', {'name': employees[0].name})
		
	# 	if u'Employee' in frappe.get_roles(user):
	# 		if query != "":
	# 			query+=" or "
	# 		query+=""" employee = '{0}'""".format(employee.name)
	# 	return query
