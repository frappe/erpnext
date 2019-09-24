from __future__ import unicode_literals
import frappe
from frappe import _

class StudentNotInGroupError(frappe.ValidationError): pass

def validate_student_belongs_to_group(student, student_group):
	groups = frappe.db.get_all('Student Group Student', ['parent'], dict(student = student, active=1))
	if not student_group in [d.parent for d in groups]:
		frappe.throw(_('Student {0} does not belong to group {1}').format(frappe.bold(student), frappe.bold(student_group)),
			StudentNotInGroupError)
