# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import get_link_to_form, getdate

from erpnext.hr.doctype.shift_assignment.shift_assignment import has_overlapping_timings
from erpnext.hr.utils import share_doc_with_approver, validate_active_employee


class OverlappingShiftRequestError(frappe.ValidationError):
	pass


class ShiftRequest(Document):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_dates()
		self.validate_overlapping_shift_requests()
		self.validate_approver()
		self.validate_default_shift()

	def on_update(self):
		share_doc_with_approver(self, self.approver)

	def on_submit(self):
		if self.status not in ["Approved", "Rejected"]:
			frappe.throw(_("Only Shift Request with status 'Approved' and 'Rejected' can be submitted"))
		if self.status == "Approved":
			assignment_doc = frappe.new_doc("Shift Assignment")
			assignment_doc.company = self.company
			assignment_doc.shift_type = self.shift_type
			assignment_doc.employee = self.employee
			assignment_doc.start_date = self.from_date
			if self.to_date:
				assignment_doc.end_date = self.to_date
			assignment_doc.shift_request = self.name
			assignment_doc.flags.ignore_permissions = 1
			assignment_doc.insert()
			assignment_doc.submit()

			frappe.msgprint(
				_("Shift Assignment: {0} created for Employee: {1}").format(
					frappe.bold(assignment_doc.name), frappe.bold(self.employee)
				)
			)

	def on_cancel(self):
		shift_assignment_list = frappe.get_list(
			"Shift Assignment", {"employee": self.employee, "shift_request": self.name}
		)
		if shift_assignment_list:
			for shift in shift_assignment_list:
				shift_assignment_doc = frappe.get_doc("Shift Assignment", shift["name"])
				shift_assignment_doc.cancel()

	def validate_default_shift(self):
		default_shift = frappe.get_value("Employee", self.employee, "default_shift")
		if self.shift_type == default_shift:
			frappe.throw(
				_("You can not request for your Default Shift: {0}").format(frappe.bold(self.shift_type))
			)

	def validate_approver(self):
		department = frappe.get_value("Employee", self.employee, "department")
		shift_approver = frappe.get_value("Employee", self.employee, "shift_request_approver")
		approvers = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
			(department),
		)
		approvers = [approver[0] for approver in approvers]
		approvers.append(shift_approver)
		if self.approver not in approvers:
			frappe.throw(_("Only Approvers can Approve this Request."))

	def validate_dates(self):
		if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
			frappe.throw(_("To date cannot be before from date"))

	def validate_overlapping_shift_requests(self):
		overlapping_dates = self.get_overlapping_dates()
		if len(overlapping_dates):
			# if dates are overlapping, check if timings are overlapping, else allow
			overlapping_timings = has_overlapping_timings(self.shift_type, overlapping_dates[0].shift_type)
			if overlapping_timings:
				self.throw_overlap_error(overlapping_dates[0])

	def get_overlapping_dates(self):
		if not self.name:
			self.name = "New Shift Request"

		shift = frappe.qb.DocType("Shift Request")
		query = (
			frappe.qb.from_(shift)
			.select(shift.name, shift.shift_type)
			.where((shift.employee == self.employee) & (shift.docstatus < 2) & (shift.name != self.name))
		)

		if self.to_date:
			query = query.where(
				Criterion.any(
					[
						Criterion.any(
							[
								shift.to_date.isnull(),
								((self.from_date >= shift.from_date) & (self.from_date <= shift.to_date)),
							]
						),
						Criterion.any(
							[
								((self.to_date >= shift.from_date) & (self.to_date <= shift.to_date)),
								shift.from_date.between(self.from_date, self.to_date),
							]
						),
					]
				)
			)
		else:
			query = query.where(
				shift.to_date.isnull()
				| ((self.from_date >= shift.from_date) & (self.from_date <= shift.to_date))
			)

		return query.run(as_dict=True)

	def throw_overlap_error(self, shift_details):
		shift_details = frappe._dict(shift_details)
		msg = _(
			"Employee {0} has already applied for Shift {1}: {2} that overlaps within this period"
		).format(
			frappe.bold(self.employee),
			frappe.bold(shift_details.shift_type),
			get_link_to_form("Shift Request", shift_details.name),
		)

		frappe.throw(msg, title=_("Overlapping Shift Requests"), exc=OverlappingShiftRequestError)
