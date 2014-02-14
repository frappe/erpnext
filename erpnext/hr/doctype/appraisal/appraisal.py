# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr, flt, getdate
from webnotes.model.bean import getlist
from webnotes import msgprint, throw, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		if not self.doc.status:
			self.doc.status = "Draft"

		self.validate_dates()
		self.validate_existing_appraisal()
		self.calculate_total()

	def get_employee_name(self):
		emp_nm = webnotes.conn.sql("""select employee_name from `tabEmployee` where 
			name=%s""", self.doc.employee)
		emp_nm = emp_nm and emp_nm[0][0] or ''
		self.doc.employee_name = emp_nm
		return emp_nm

	def validate_dates(self):
		if getdate(self.doc.start_date) > getdate(self.doc.end_date):
			throw(_("End Date can not be less than Start Date"))

	def validate_existing_appraisal(self):
		chk = webnotes.conn.sql("""select name from `tabAppraisal` where employee=%s 
			and (status='Submitted' or status='Completed') 
			and ((start_date>=%s and start_date<=%s) 
			or (end_date>=%s and end_date<=%s))""",
			(self.doc.employee, self.doc.start_date, self.doc.end_date, self.doc.start_date, self.doc.end_date))

		if chk:
			throw("{created} {chk} {date} {employee}".format(**{
				"created": _("You have already created Appraisal"),
				"chk": cstr(chk[0][0]),
				"date": _("in the current date range for employee"),
				"employee": cstr(self.doc.employee_name)
			}))

	def calculate_total(self):
		total, total_w = 0, 0
		for d in getlist(self.doclist, 'appraisal_details'):
			if d.score:
				d.score_earned = flt(d.score) * flt(d.per_weightage) / 100
				total = total + d.score_earned
			total_w += flt(d.per_weightage)

		if cint(total_w) != 100:
			throw("{weightage}: {total}%".format(**{
				"weightage": _("Total weightage assigned should be 100%. It is"),
				"total": cstr(total_w)
			}))

		if webnotes.conn.get_value("Employee", self.doc.employee, "user_id") != \
				webnotes.session.user and total == 0:
			throw(_("Total can't be zero. You must atleast give some points!"))

		self.doc.total_score = total

	def on_submit(self):
		webnotes.conn.set(self.doc, 'status', 'Submitted')

	def on_cancel(self): 
		webnotes.conn.set(self.doc, 'status', 'Cancelled')

@webnotes.whitelist()
def fetch_appraisal_template(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist

	doclist = get_mapped_doclist("Appraisal Template", source_name, {
		"Appraisal Template": {
			"doctype": "Appraisal", 
		}, 
		"Appraisal Template Goal": {
			"doctype": "Appraisal Goal", 
		}
	}, target_doclist)

	return [d.fields for d in doclist]