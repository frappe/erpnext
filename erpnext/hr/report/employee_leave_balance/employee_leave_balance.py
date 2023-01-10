# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from itertools import groupby
from typing import Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from erpnext.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
from erpnext.hr.doctype.leave_application.leave_application import (
	get_leave_balance_on,
	get_leaves_for_period,
)

Filters = frappe._dict


def execute(filters: Optional[Filters] = None) -> Tuple:
	if filters.to_date <= filters.from_date:
		frappe.throw(_('"From Date" can not be greater than or equal to "To Date"'))

	columns = get_columns()
	data = get_data(filters)
	charts = get_chart_data(data)
	return columns, data, None, charts


def get_columns() -> List[Dict]:
	return [
		{
			"label": _("Leave Type"),
			"fieldtype": "Link",
			"fieldname": "leave_type",
			"width": 200,
			"options": "Leave Type",
		},
		{
			"label": _("Employee"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"width": 100,
			"options": "Employee",
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "employee_name",
			"width": 100,
			"options": "employee",
		},
		{
			"label": _("Opening Balance"),
			"fieldtype": "float",
			"fieldname": "opening_balance",
			"width": 150,
		},
		{
			"label": _("New Leave(s) Allocated"),
			"fieldtype": "float",
			"fieldname": "leaves_allocated",
			"width": 200,
		},
		{
			"label": _("Leave(s) Taken"),
			"fieldtype": "float",
			"fieldname": "leaves_taken",
			"width": 150,
		},
		{
			"label": _("Leave(s) Expired"),
			"fieldtype": "float",
			"fieldname": "leaves_expired",
			"width": 150,
		},
		{
			"label": _("Closing Balance"),
			"fieldtype": "float",
			"fieldname": "closing_balance",
			"width": 150,
		},
	]


def get_data(filters: Filters) -> List:
	leave_types = frappe.db.get_list("Leave Type", pluck="name", order_by="name")
	conditions = get_conditions(filters)

	user = frappe.session.user
	department_approver_map = get_department_leave_approver_map(filters.get("department"))

	active_employees = frappe.get_list(
		"Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "user_id", "leave_approver"],
	)

	data = []

	for leave_type in leave_types:
		if len(active_employees) > 1:
			data.append({"leave_type": leave_type})
		else:
			row = frappe._dict({"leave_type": leave_type})

		for employee in active_employees:

			leave_approvers = department_approver_map.get(employee.department_name, []).append(
				employee.leave_approver
			)

			if len(active_employees) > 1:
				row = frappe._dict()

			row.employee = employee.name
			row.employee_name = employee.employee_name

			leaves_taken = (
				get_leaves_for_period(employee.name, leave_type, filters.from_date, filters.to_date) * -1
			)

			new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
				filters.from_date, filters.to_date, employee.name, leave_type
			)
			opening = get_opening_balance(employee.name, leave_type, filters, carry_forwarded_leaves)

			row.leaves_allocated = new_allocation
			row.leaves_expired = expired_leaves
			row.opening_balance = opening
			row.leaves_taken = leaves_taken

			# not be shown on the basis of days left it create in user mind for carry_forward leave
			row.closing_balance = new_allocation + opening - (row.leaves_expired + leaves_taken)
			row.indent = 1
			data.append(row)

	return data


def get_opening_balance(
	employee: str, leave_type: str, filters: Filters, carry_forwarded_leaves: float
) -> float:
	# allocation boundary condition
	# opening balance is the closing leave balance 1 day before the filter start date
	opening_balance_date = add_days(filters.from_date, -1)
	allocation = get_previous_allocation(filters.from_date, leave_type, employee)

	if (
		allocation
		and allocation.get("to_date")
		and opening_balance_date
		and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
	):
		# if opening balance date is same as the previous allocation's expiry
		# then opening balance should only consider carry forwarded leaves
		opening_balance = carry_forwarded_leaves
	else:
		# else directly get leave balance on the previous day
		opening_balance = get_leave_balance_on(employee, leave_type, opening_balance_date)

	return opening_balance


def get_conditions(filters: Filters) -> Dict:
	conditions = {}

	if filters.get("employee"):
		conditions["name"] = filters.get("employee")

	if filters.get("company"):
		conditions["company"] = filters.get("company")

	if filters.get("department"):
		conditions["department"] = filters.get("department")

	if filters.get("employee_status"):
		conditions["status"] = filters.get("employee_status")

	return conditions


def get_department_leave_approver_map(department: Optional[str] = None):
	# get current department and all its child
	department_list = frappe.get_list(
		"Department",
		filters={"disabled": 0},
		or_filters={"name": department, "parent_department": department},
		pluck="name",
	)
	# retrieve approvers list from current department and from its subsequent child departments
	approver_list = frappe.get_all(
		"Department Approver",
		filters={"parentfield": "leave_approvers", "parent": ("in", department_list)},
		fields=["parent", "approver"],
		as_list=True,
	)

	approvers = {}

	for k, v in approver_list:
		approvers.setdefault(k, []).append(v)

	return approvers


def get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> Tuple[float, float, float]:
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0

	records = get_leave_ledger_entries(from_date, to_date, employee, leave_type)

	for record in records:
		# new allocation records with `is_expired=1` are created when leave expires
		# these new records should not be considered, else it leads to negative leave balance
		if record.is_expired:
			continue

		if record.to_date < getdate(to_date):
			# leave allocations ending before to_date, reduce leaves taken within that period
			# since they are already used, they won't expire
			expired_leaves += record.leaves
			expired_leaves += get_leaves_for_period(employee, leave_type, record.from_date, record.to_date)

		if record.from_date >= getdate(from_date):
			if record.is_carry_forward:
				carry_forwarded_leaves += record.leaves
			else:
				new_allocation += record.leaves

	return new_allocation, expired_leaves, carry_forwarded_leaves


def get_leave_ledger_entries(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> List[Dict]:
	ledger = frappe.qb.DocType("Leave Ledger Entry")
	records = (
		frappe.qb.from_(ledger)
		.select(
			ledger.employee,
			ledger.leave_type,
			ledger.from_date,
			ledger.to_date,
			ledger.leaves,
			ledger.transaction_name,
			ledger.transaction_type,
			ledger.is_carry_forward,
			ledger.is_expired,
		)
		.where(
			(ledger.docstatus == 1)
			& (ledger.transaction_type == "Leave Allocation")
			& (ledger.employee == employee)
			& (ledger.leave_type == leave_type)
			& (
				(ledger.from_date[from_date:to_date])
				| (ledger.to_date[from_date:to_date])
				| ((ledger.from_date < from_date) & (ledger.to_date > to_date))
			)
		)
	).run(as_dict=True)

	return records


def get_chart_data(data: List) -> Dict:
	labels = []
	datasets = []
	employee_data = data

	if data and data[0].get("employee_name"):
		get_dataset_for_chart(employee_data, datasets, labels)

	chart = {
		"data": {"labels": labels, "datasets": datasets},
		"type": "bar",
		"colors": ["#456789", "#EE8888", "#7E77BF"],
	}

	return chart


def get_dataset_for_chart(employee_data: List, datasets: List, labels: List) -> List:
	leaves = []
	employee_data = sorted(employee_data, key=lambda k: k["employee_name"])

	for key, group in groupby(employee_data, lambda x: x["employee_name"]):
		for grp in group:
			if grp.closing_balance:
				leaves.append(
					frappe._dict({"leave_type": grp.leave_type, "closing_balance": grp.closing_balance})
				)

		if leaves:
			labels.append(key)

	for leave in leaves:
		datasets.append({"name": leave.leave_type, "values": [leave.closing_balance]})
