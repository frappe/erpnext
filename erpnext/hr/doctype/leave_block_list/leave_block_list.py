# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class LeaveBlockList(Document):
	def validate(self):
		dates = []
		for d in self.get("leave_block_list_dates"):

			# date is not repeated
			if d.block_date in dates:
				frappe.msgprint(_("Date is repeated") + ":" + d.block_date, raise_exception=1)
			dates.append(d.block_date)


@frappe.whitelist()
def get_applicable_block_dates(from_date, to_date, employee=None, company=None, all_lists=False):
	block_dates = []
	for block_list in get_applicable_block_lists(employee, company, all_lists):
		block_dates.extend(
			frappe.db.sql(
				"""select block_date, reason
			from `tabLeave Block List Date` where parent=%s
			and block_date between %s and %s""",
				(block_list, from_date, to_date),
				as_dict=1,
			)
		)

	return block_dates


def get_applicable_block_lists(employee=None, company=None, all_lists=False):
	block_lists = []

	if not employee:
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
		if not employee:
			return []

	if not company:
		company = frappe.db.get_value("Employee", employee, "company")

	def add_block_list(block_list):
		if block_list:
			if all_lists or not is_user_in_allow_list(block_list):
				block_lists.append(block_list)

	# per department
	department = frappe.db.get_value("Employee", employee, "department")
	if department:
		block_list = frappe.db.get_value("Department", department, "leave_block_list")
		add_block_list(block_list)

	# global
	for block_list in frappe.db.sql_list(
		"""select name from `tabLeave Block List`
		where applies_to_all_departments=1 and company=%s""",
		company,
	):
		add_block_list(block_list)

	return list(set(block_lists))


def is_user_in_allow_list(block_list):
	return frappe.session.user in frappe.db.sql_list(
		"""select allow_user
		from `tabLeave Block List Allow` where parent=%s""",
		block_list,
	)
