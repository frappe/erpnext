# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import DATE_FORMAT, flt, getdate, today


class LeaveLedgerEntry(Document):
	def validate(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("To date needs to be before from date"))

	def on_cancel(self):
		# allow cancellation of expiry leaves
		if self.is_expired:
			frappe.db.set_value("Leave Allocation", self.transaction_name, "expired", 0)
		else:
			frappe.throw(_("Only expired allocation can be cancelled"))


def validate_leave_allocation_against_leave_application(ledger):
	"""Checks that leave allocation has no leave application against it"""
	leave_application_records = frappe.db.sql_list(
		"""
		SELECT transaction_name
		FROM `tabLeave Ledger Entry`
		WHERE
			employee=%s
			AND leave_type=%s
			AND transaction_type='Leave Application'
			AND from_date>=%s
			AND to_date<=%s
	""",
		(ledger.employee, ledger.leave_type, ledger.from_date, ledger.to_date),
	)

	if leave_application_records:
		frappe.throw(
			_("Leave allocation {0} is linked with the Leave Application {1}").format(
				ledger.transaction_name, ", ".join(leave_application_records)
			)
		)


def create_leave_ledger_entry(ref_doc, args, submit=True):
	ledger = frappe._dict(
		doctype="Leave Ledger Entry",
		employee=ref_doc.employee,
		employee_name=ref_doc.employee_name,
		leave_type=ref_doc.leave_type,
		transaction_type=ref_doc.doctype,
		transaction_name=ref_doc.name,
		is_carry_forward=0,
		is_expired=0,
		is_lwp=0,
	)
	ledger.update(args)

	if submit:
		doc = frappe.get_doc(ledger)
		doc.flags.ignore_permissions = 1
		doc.submit()
	else:
		delete_ledger_entry(ledger)


def delete_ledger_entry(ledger):
	"""Delete ledger entry on cancel of leave application/allocation/encashment"""
	if ledger.transaction_type == "Leave Allocation":
		validate_leave_allocation_against_leave_application(ledger)

	expired_entry = get_previous_expiry_ledger_entry(ledger)
	frappe.db.sql(
		"""DELETE
		FROM `tabLeave Ledger Entry`
		WHERE
			`transaction_name`=%s
			OR `name`=%s""",
		(ledger.transaction_name, expired_entry),
	)


def get_previous_expiry_ledger_entry(ledger):
	"""Returns the expiry ledger entry having same creation date as the ledger entry to be cancelled"""
	creation_date = frappe.db.get_value(
		"Leave Ledger Entry",
		filters={
			"transaction_name": ledger.transaction_name,
			"is_expired": 0,
			"transaction_type": "Leave Allocation",
		},
		fieldname=["creation"],
	)

	creation_date = creation_date.strftime(DATE_FORMAT) if creation_date else ""

	return frappe.db.get_value(
		"Leave Ledger Entry",
		filters={
			"creation": ("like", creation_date + "%"),
			"employee": ledger.employee,
			"leave_type": ledger.leave_type,
			"is_expired": 1,
			"docstatus": 1,
			"is_carry_forward": 0,
		},
		fieldname=["name"],
	)


def process_expired_allocation():
	"""Check if a carry forwarded allocation has expired and create a expiry ledger entry
	Case 1: carry forwarded expiry period is set for the leave type,
	        create a separate leave expiry entry against each entry of carry forwarded and non carry forwarded leaves
	Case 2: leave type has no specific expiry period for carry forwarded leaves
	        and there is no carry forwarded leave allocation, create a single expiry against the remaining leaves.
	"""

	# fetch leave type records that has carry forwarded leaves expiry
	leave_type_records = frappe.db.get_values(
		"Leave Type", filters={"expire_carry_forwarded_leaves_after_days": (">", 0)}, fieldname=["name"]
	)

	leave_type = [record[0] for record in leave_type_records] or [""]

	# fetch non expired leave ledger entry of transaction_type allocation
	expire_allocation = frappe.db.sql(
		"""
		SELECT
			leaves, to_date, employee, leave_type,
			is_carry_forward, transaction_name as name, transaction_type
		FROM `tabLeave Ledger Entry` l
		WHERE (NOT EXISTS
			(SELECT name
				FROM `tabLeave Ledger Entry`
				WHERE
					transaction_name = l.transaction_name
					AND transaction_type = 'Leave Allocation'
					AND name<>l.name
					AND docstatus = 1
					AND (
						is_carry_forward=l.is_carry_forward
						OR (is_carry_forward = 0 AND leave_type not in %s)
			)))
			AND transaction_type = 'Leave Allocation'
			AND to_date < %s""",
		(leave_type, today()),
		as_dict=1,
	)

	if expire_allocation:
		create_expiry_ledger_entry(expire_allocation)


def create_expiry_ledger_entry(allocations):
	"""Create ledger entry for expired allocation"""
	for allocation in allocations:
		if allocation.is_carry_forward:
			expire_carried_forward_allocation(allocation)
		else:
			expire_allocation(allocation)


def get_remaining_leaves(allocation):
	"""Returns remaining leaves from the given allocation"""
	return frappe.db.get_value(
		"Leave Ledger Entry",
		filters={
			"employee": allocation.employee,
			"leave_type": allocation.leave_type,
			"to_date": ("<=", allocation.to_date),
			"docstatus": 1,
		},
		fieldname=["SUM(leaves)"],
	)


@frappe.whitelist()
def expire_allocation(allocation, expiry_date=None):
	"""expires non-carry forwarded allocation"""
	leaves = get_remaining_leaves(allocation)
	expiry_date = expiry_date if expiry_date else allocation.to_date

	# allows expired leaves entry to be created/reverted
	if leaves:
		args = dict(
			leaves=flt(leaves) * -1,
			transaction_name=allocation.name,
			transaction_type="Leave Allocation",
			from_date=expiry_date,
			to_date=expiry_date,
			is_carry_forward=0,
			is_expired=1,
		)
		create_leave_ledger_entry(allocation, args)

	frappe.db.set_value("Leave Allocation", allocation.name, "expired", 1)


def expire_carried_forward_allocation(allocation):
	"""Expires remaining leaves in the on carried forward allocation"""
	from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period

	leaves_taken = get_leaves_for_period(
		allocation.employee,
		allocation.leave_type,
		allocation.from_date,
		allocation.to_date,
		skip_expired_leaves=False,
	)
	leaves = flt(allocation.leaves) + flt(leaves_taken)

	# allow expired leaves entry to be created
	if leaves > 0:
		args = frappe._dict(
			transaction_name=allocation.name,
			transaction_type="Leave Allocation",
			leaves=allocation.leaves * -1,
			is_carry_forward=allocation.is_carry_forward,
			is_expired=1,
			from_date=allocation.to_date,
			to_date=allocation.to_date,
		)
		create_leave_ledger_entry(allocation, args)
