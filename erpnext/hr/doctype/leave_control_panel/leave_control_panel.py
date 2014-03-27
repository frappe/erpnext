# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint, cstr, flt, nowdate
from frappe.model.doc import Document
from frappe.model.code import get_obj
from frappe import msgprint, _

	


from frappe.model.document import Document

class LeaveControlPanel(Document):
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist	 
	

	def get_employees(self):		
		lst1 = [[self.doc.employee_type,"employment_type"],[self.doc.branch,"branch"],[self.doc.designation,"designation"],[self.doc.department, "department"],[self.doc.grade,"grade"]]
		condition = "where "
		flag = 0
		for l in lst1:
			if(l[0]):
				if flag == 0:
					condition += l[1] + "= '" + l[0] +"'"
				else:
					condition += " and " + l[1]+ "= '" +l[0] +"'"
				flag = 1
		emp_query = "select name from `tabEmployee` "
		if flag == 1:
			emp_query += condition 
		e = frappe.db.sql(emp_query)
		return e

	def validate_values(self):
		meta = frappe.get_doctype(self.doc.doctype)
		for f in ["fiscal_year", "leave_type", "no_of_days"]:
			if not self.doc.fields[f]:
				frappe.throw(_(meta.get_label(f)) + _(" is mandatory"))

	def allocate_leave(self):
		self.validate_values()
		leave_allocated_for = []
		employees = self.get_employees()
		if not employees:
			frappe.throw(_("No employee found"))
			
		for d in self.get_employees():
			try:
				la = Document('Leave Allocation')
				la.employee = cstr(d[0])
				la.employee_name = frappe.db.get_value('Employee',cstr(d[0]),'employee_name')
				la.leave_type = self.doc.leave_type
				la.fiscal_year = self.doc.fiscal_year
				la.posting_date = nowdate()
				la.carry_forward = cint(self.doc.carry_forward)
				la.new_leaves_allocated = flt(self.doc.no_of_days)
				la_obj = get_obj(doc=la)
				la_obj.doc.docstatus = 1
				la_obj.validate()
				la_obj.on_update()
				la_obj.doc.save(1)
				leave_allocated_for.append(d[0])
			except:
				pass
		if leave_allocated_for:
			msgprint("Leaves Allocated Successfully for " + ", ".join(leave_allocated_for))
