# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name, validate_active_employee

class Appraisal(Document):
	def validate(self):
		if not self.status:
			self.status = 'Draft'

		validate_active_employee(self.employee)
		set_employee_name(self)
		self.validate_dates()
		self.validate_existing_appraisal()
		self.calculate_total_for_kra_assessment()
		self.check_for_kra_assessment()
		self.check_for_behavioural_assessment()
		self.check_for_self_improvement_areas()
		self.check_for_new_designation()

	def get_employee_name(self):
		self.employee_name = frappe.db.get_value('Employee', self.employee, 'employee_name')
		return self.employee_name

	def validate_dates(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_('End Date can not be less than Start Date'))

	def validate_existing_appraisal(self):
		chk = frappe.db.sql('''select name from `tabAppraisal` where employee=%s
			and (status='Submitted' or status='Completed')
			and ((start_date>=%s and start_date<=%s)
			or (end_date>=%s and end_date<=%s))''',
			(self.employee,self.start_date,self.end_date,self.start_date,self.end_date))
		if chk:
			frappe.throw(_('Appraisal {0} created for Employee {1} in the given date range').format(chk[0][0], self.employee_name))

	def calculate_total_for_kra_assessment(self):
		total_mentor_score, total_w, total_self_score = 0, 0, 0
		for d in self.get('kra_assessment'):
			if d.mentor_score:
				total_mentor_score = total_mentor_score + flt(d.mentor_score) * (flt(d.per_weightage)/100)
				total_self_score = total_self_score + flt(d.self_score) * (flt(d.per_weightage)/100)
			total_w += flt(d.per_weightage)

		if int(total_w) != 100:
			frappe.throw(_('Total weightage assigned should be 100%.<br>It is {0}').format(str(total_w) + '%'))

		self.overall_self_score = total_self_score
		self.overall_score = total_mentor_score

	def check_for_kra_assessment(self):
		for d in self.get('kra_assessment'):
			if d.mentor_score < 1 or d.mentor_score > 5 and d.self_score < 1 or d.self_score > 5:
				frappe.throw(_('KRA Assessment Score should be between 1 to 5'))
			
	def check_for_behavioural_assessment(self):

		for d in self.get('behavioural_assessment'):
			if d.mentors_score > 5 or d.mentors_score < 1:
				frappe.throw(_('Behavioural Assessment Score should be between 1 and 5'))

			if d.self_score > 5 or d.self_score < 1:
				frappe.throw(_('Behavioural Assessment Score should be between 1 and 5'))

	def check_for_self_improvement_areas(self):

		for d in self.get('self_improvement_areas'):
			if d.current_score > 5 or d.current_score < 1:
				frappe.throw(_('Self Improvement Score should be between 1 and 5'))
			
			if d.target_score > 5 or d.target_score < 1:
				frappe.throw(_('Self Improvement Score should be between 1 and 5'))

			if d.achieved_score > 5 or d.achieved_score < 1:
				frappe.throw(_('Self Improvement Score should be between 1 and 5'))

	def check_for_new_designation(self):

		if self.get('action_taken') == "Promoted" or self.get('action_taken') == "Demoted":
			if not self.get('new_designation'):
				frappe.throw(_("Please update the new designation"))

	def on_submit(self):
		frappe.db.set(self, 'status', 'Submitted')

	def on_cancel(self):
		frappe.db.set(self, 'status', 'Cancelled')


@frappe.whitelist()
def fetch_appraisal_template(source_name, target_doc=None):
	target_doc = get_mapped_doc('Appraisal Template', source_name, {
		'Appraisal Template': {
			'doctype': 'Appraisal',
		},
		'KRA Assessment Goals': {
			'doctype': 'KRA Assessment'
		},
		'Behavioural Assessment Goals': {
			'doctype': 'Behavioural Assessment'
		},
		'Self Improvement Area Goals': {
			'doctype': 'Self Improvement Areas'
		}
	}, target_doc)

	return target_doc