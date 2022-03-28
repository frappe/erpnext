# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
from math import ceil

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import date_diff, flt, formatdate, get_last_day, get_link_to_form, getdate


class LeavePolicyAssignment(Document):
	def validate(self):
		self.set_dates()
		self.validate_policy_assignment_overlap()
		self.warn_about_carry_forwarding()

	def on_submit(self):
		self.grant_leave_alloc_for_employee()

	def set_dates(self):
		if self.assignment_based_on == "Leave Period":
			self.effective_from, self.effective_to = frappe.db.get_value(
				"Leave Period", self.leave_period, ["from_date", "to_date"]
			)
		elif self.assignment_based_on == "Joining Date":
			self.effective_from = frappe.db.get_value("Employee", self.employee, "date_of_joining")

	def validate_policy_assignment_overlap(self):
		leave_policy_assignments = frappe.get_all(
			"Leave Policy Assignment",
			filters={
				"employee": self.employee,
				"name": ("!=", self.name),
				"docstatus": 1,
				"effective_to": (">=", self.effective_from),
				"effective_from": ("<=", self.effective_to),
			},
		)

		if len(leave_policy_assignments):
			frappe.throw(
				_("Leave Policy: {0} already assigned for Employee {1} for period {2} to {3}").format(
					bold(self.leave_policy),
					bold(self.employee),
					bold(formatdate(self.effective_from)),
					bold(formatdate(self.effective_to)),
				)
			)

	def warn_about_carry_forwarding(self):
		if not self.carry_forward:
			return

		leave_types = get_leave_type_details()
		leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)

		for policy in leave_policy.leave_policy_details:
			leave_type = leave_types.get(policy.leave_type)
			if not leave_type.is_carry_forward:
				msg = _(
					"Leaves for the Leave Type {0} won't be carry-forwarded since carry-forwarding is disabled."
				).format(frappe.bold(get_link_to_form("Leave Type", leave_type.name)))
				frappe.msgprint(msg, indicator="orange", alert=True)

	@frappe.whitelist()
	def grant_leave_alloc_for_employee(self):
		if self.leaves_allocated:
			frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))
		else:
			leave_allocations = {}
			leave_type_details = get_leave_type_details()

			leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

			for leave_policy_detail in leave_policy.leave_policy_details:
				if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
					leave_allocation, new_leaves_allocated = self.create_leave_allocation(
						leave_policy_detail.leave_type,
						leave_policy_detail.annual_allocation,
						leave_type_details,
						date_of_joining,
					)
					leave_allocations[leave_policy_detail.leave_type] = {
						"name": leave_allocation,
						"leaves": new_leaves_allocated,
					}
			self.db_set("leaves_allocated", 1)
			return leave_allocations

	def create_leave_allocation(
		self, leave_type, new_leaves_allocated, leave_type_details, date_of_joining
	):
		# Creates leave allocation for the given employee in the provided leave period
		carry_forward = self.carry_forward
		if self.carry_forward and not leave_type_details.get(leave_type).is_carry_forward:
			carry_forward = 0

		new_leaves_allocated = self.get_new_leaves(
			leave_type, new_leaves_allocated, leave_type_details, date_of_joining
		)

		allocation = frappe.get_doc(
			dict(
				doctype="Leave Allocation",
				employee=self.employee,
				leave_type=leave_type,
				from_date=self.effective_from,
				to_date=self.effective_to,
				new_leaves_allocated=new_leaves_allocated,
				leave_period=self.leave_period if self.assignment_based_on == "Leave Policy" else "",
				leave_policy_assignment=self.name,
				leave_policy=self.leave_policy,
				carry_forward=carry_forward,
			)
		)
		allocation.save(ignore_permissions=True)
		allocation.submit()
		return allocation.name, new_leaves_allocated

	def get_new_leaves(self, leave_type, new_leaves_allocated, leave_type_details, date_of_joining):
		from frappe.model.meta import get_field_precision

		precision = get_field_precision(
			frappe.get_meta("Leave Allocation").get_field("new_leaves_allocated")
		)

		# Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
		if leave_type_details.get(leave_type).is_compensatory == 1:
			new_leaves_allocated = 0

		elif leave_type_details.get(leave_type).is_earned_leave == 1:
			if not self.assignment_based_on:
				new_leaves_allocated = 0
			else:
				# get leaves for past months if assignment is based on Leave Period / Joining Date
				new_leaves_allocated = self.get_leaves_for_passed_months(
					leave_type, new_leaves_allocated, leave_type_details, date_of_joining
				)

		# Calculate leaves at pro-rata basis for employees joining after the beginning of the given leave period
		elif getdate(date_of_joining) > getdate(self.effective_from):
			remaining_period = (date_diff(self.effective_to, date_of_joining) + 1) / (
				date_diff(self.effective_to, self.effective_from) + 1
			)
			new_leaves_allocated = ceil(new_leaves_allocated * remaining_period)

		return flt(new_leaves_allocated, precision)

	def get_leaves_for_passed_months(
		self, leave_type, new_leaves_allocated, leave_type_details, date_of_joining
	):
		from erpnext.hr.utils import get_monthly_earned_leave

		current_date = frappe.flags.current_date or getdate()
		if current_date > getdate(self.effective_to):
			current_date = getdate(self.effective_to)

		from_date = getdate(self.effective_from)
		if getdate(date_of_joining) > from_date:
			from_date = getdate(date_of_joining)

		months_passed = 0
		based_on_doj = leave_type_details.get(leave_type).based_on_date_of_joining

		if current_date.year == from_date.year and current_date.month >= from_date.month:
			months_passed = current_date.month - from_date.month
			months_passed = add_current_month_if_applicable(months_passed, date_of_joining, based_on_doj)

		elif current_date.year > from_date.year:
			months_passed = (12 - from_date.month) + current_date.month
			months_passed = add_current_month_if_applicable(months_passed, date_of_joining, based_on_doj)

		if months_passed > 0:
			monthly_earned_leave = get_monthly_earned_leave(
				new_leaves_allocated,
				leave_type_details.get(leave_type).earned_leave_frequency,
				leave_type_details.get(leave_type).rounding,
			)
			new_leaves_allocated = monthly_earned_leave * months_passed
		else:
			new_leaves_allocated = 0

		return new_leaves_allocated


def add_current_month_if_applicable(months_passed, date_of_joining, based_on_doj):
	date = getdate(frappe.flags.current_date) or getdate()

	if based_on_doj:
		# if leave type allocation is based on DOJ, and the date of assignment creation is same as DOJ,
		# then the month should be considered
		if date.day == date_of_joining.day:
			months_passed += 1
	else:
		last_day_of_month = get_last_day(date)
		# if its the last day of the month, then that month should be considered
		if last_day_of_month == date:
			months_passed += 1

	return months_passed


@frappe.whitelist()
def create_assignment_for_multiple_employees(employees, data):

	if isinstance(employees, str):
		employees = json.loads(employees)

	if isinstance(data, str):
		data = frappe._dict(json.loads(data))

	docs_name = []
	for employee in employees:
		assignment = frappe.new_doc("Leave Policy Assignment")
		assignment.employee = employee
		assignment.assignment_based_on = data.assignment_based_on or None
		assignment.leave_policy = data.leave_policy
		assignment.effective_from = getdate(data.effective_from) or None
		assignment.effective_to = getdate(data.effective_to) or None
		assignment.leave_period = data.leave_period or None
		assignment.carry_forward = data.carry_forward
		assignment.save()
		try:
			assignment.submit()
		except frappe.exceptions.ValidationError:
			continue

		frappe.db.commit()

		docs_name.append(assignment.name)

	return docs_name


def get_leave_type_details():
	leave_type_details = frappe._dict()
	leave_types = frappe.get_all(
		"Leave Type",
		fields=[
			"name",
			"is_lwp",
			"is_earned_leave",
			"is_compensatory",
			"based_on_date_of_joining",
			"is_carry_forward",
			"expire_carry_forwarded_leaves_after_days",
			"earned_leave_frequency",
			"rounding",
		],
	)
	for d in leave_types:
		leave_type_details.setdefault(d.name, d)
	return leave_type_details
