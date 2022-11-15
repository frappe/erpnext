# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, cint, comma_or, nowdate, getdate
from frappe import _
from frappe.model.document import Document


class OverAllowanceError(frappe.ValidationError):
	pass


def validate_status(status, options):
	if status not in options:
		frappe.throw(_("Status must be one of {0}").format(comma_or(options)))


class StatusUpdater(Document):
	"""
		Updates the status of the calling records
		Delivery Note: Update Delivered Qty, Update Percent and Validate over delivery
		Sales Invoice: Update Billed Amt, Update Percent and Validate over billing
		Installation Note: Update Installed Qty, Update Percent Qty and Validate over installation
	"""

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		if self.get('status_map'):
			previous_status = self.status
			if status:
				self.status = status
				if update:
					self.db_set("status", status, update_modified=update_modified)

			sl = self.status_map[:]
			sl.reverse()
			for s, condition in sl:
				if not condition:
					self.status = s
					break
				elif condition.startswith("eval:"):
					if frappe.safe_eval(condition[5:], None, {"self": self.as_dict(), "getdate": getdate,
							"nowdate": nowdate, "get_value": frappe.db.get_value}):
						self.status = s
						break
				elif getattr(self, condition)():
					self.status = s
					break

			self.add_status_comment(previous_status)

			if update:
				self.db_set('status', self.status, update_modified=update_modified)

	def add_status_comment(self, previous_status):
		if self.status != previous_status and self.status not in ("Cancelled", "Draft"):
			self.add_comment("Label", _(self.status))

	def calculate_status_percentage(self, completed_field, reference_field, items=None):
		if items is None:
			items = self.get('items', [])

		if items:
			precision = items[0].precision(reference_field)
		else:
			precision = cint(frappe.db.get_default("float_precision")) or 3

		# Allow both: single and multiple completed qty fieldnames
		if not isinstance(completed_field, list):
			completed_field = [completed_field]

		# Calculate Total Qty and Total Completed Qty
		total_reference_qty = 0
		total_completed_qty = 0
		for row in items:
			completed_qty = 0
			for f in completed_field:
				completed_qty += abs(flt(row.get(f)))

			reference_qty = abs(flt(row.get(reference_field)))
			completed_qty = min(completed_qty, reference_qty)

			total_reference_qty += reference_qty
			total_completed_qty += completed_qty

		total_reference_qty = flt(total_reference_qty, precision)
		total_completed_qty = flt(total_completed_qty, precision)

		if total_reference_qty:
			return flt(total_completed_qty / total_reference_qty * 100, 6)
		else:
			return None

	def get_completion_status(self, percentage_field, keyword):
		percentage = flt(self.get(percentage_field))
		rounded_percentage = flt(percentage, self.precision(percentage_field))

		if rounded_percentage <= 0:
			status = 'Not'
		elif rounded_percentage >= 100:
			status = 'Fully'
		else:
			status = 'Partly'

		return "{0} {1}".format(status, keyword)

	def validate_completed_qty(self, completed_field, reference_field, items=None, allowance_type=None,
			from_doctype=None, row_names=None):
		items = self.get_rows_for_qty_validation(items, row_names)
		for row in items:
			self.validate_completed_qty_for_row(row, completed_field, reference_field, allowance_type, from_doctype)

	def get_rows_for_qty_validation(self, items=None, row_names=None):
		if items is None:
			items = self.get('items', [])

		rows = []
		for row in items:
			if row_names is None or row.name in row_names:
				rows.append(row)

		return rows

	def validate_completed_qty_for_row(self, row, completed_field, reference_field, allowance_type=None, from_doctype=None):
		# Allow both: single and multiple completed qty fieldnames
		if not isinstance(completed_field, list):
			completed_field = [completed_field]

		reference_qty = flt(row.get(reference_field))
		completed_qty = 0
		for f in completed_field:
			completed_qty += flt(row.get(f))

		difference = completed_qty - reference_qty
		if not allowance_type:
			excess_qty = difference
		else:
			excess_qty = get_excess_qty_with_allowance(row, completed_field, reference_field, allowance_type)

		if reference_qty < 0:
			excess_qty = -1 * excess_qty

		rounded_excess = flt(excess_qty, row.precision(reference_field))

		if rounded_excess > 0:
			self.limits_crossed_error(row, completed_field, reference_field, allowance_type, excess_qty,
				from_doctype=from_doctype)

	def limits_crossed_error(self, row, completed_field, reference_field, allowance_type,
			excess_qty=None, from_doctype=None):
		"""Raise exception for limits crossed"""
		reference_qty = flt(row.get(reference_field))

		# Allow both: single and multiple completed qty fieldnames
		if not isinstance(completed_field, list):
			completed_field = [completed_field]

		completed_qty = 0
		for f in completed_field:
			completed_qty += flt(row.get(f))

		if excess_qty is None:
			excess_qty = completed_qty - reference_qty

		formatted_reference_qty = row.get_formatted(reference_field)
		formatted_completed_qty = frappe.format(completed_qty, df=row.meta.get_field(completed_field[0]), doc=row)
		formatted_excess = frappe.format(excess_qty, df=row.meta.get_field(reference_field), doc=row)

		reference_field_label = row.meta.get_label(reference_field)

		completed_field_label = []
		for f in completed_field:
			completed_field_label.append(row.meta.get_label(f))
		completed_field_label = " + ".join(completed_field_label)

		over_limit_msg = _("{0} for Item {1} is over limit by {2}.").format(
			frappe.bold(completed_field_label),
			frappe.bold(row.get('item_code') or row.get('item_name')),
			frappe.bold(formatted_excess)
		)

		actual_qty_msg = _("{0} {1} is {2}, however, {3} is {4}").format(
			frappe.bold(self.doctype),
			frappe.bold(reference_field_label),
			frappe.bold(formatted_reference_qty),
			frappe.bold(completed_field_label),
			frappe.bold(formatted_completed_qty),
		)

		from_doctype_msg = ""
		if from_doctype:
			from_doctype_msg = _("Are you making a duplicate {0} against the same {1}?").format(
				frappe.bold(from_doctype),
				frappe.bold(self.doctype),
			)

		if not allowance_type:
			action_msg = ""
		elif allowance_type == "billing":
			action_msg = _('To allow Over Billing, update "Over Billing Allowance" in Accounts Settings or the Item.')
		else:
			action_msg = _('To allow Over Receipt/Delivery, update "Over Receipt/Delivery Allowance" in Stock Settings or the Item.')

		full_msg = over_limit_msg + "<br>" + actual_qty_msg

		if from_doctype_msg:
			full_msg += "<br><br>" + from_doctype_msg
		if action_msg:
			full_msg += "<br><br>" + action_msg

		frappe.throw(full_msg, OverAllowanceError, title=_('{0} Limit Crossed').format(completed_field_label))


def get_allowance_for(allowance_type, item_code=None):
	"""
		Returns the allowance for the item, if not set, returns global allowance
	"""

	if not allowance_type:
		return 0

	allowance = 0
	allowance_field = "over_billing_allowance" if allowance_type == "billing" else "over_delivery_receipt_allowance"

	if item_code:
		allowance = flt(frappe.get_cached_value('Item', item_code, allowance_field))

	if not allowance:
		if allowance_type == "billing":
			allowance = flt(frappe.get_cached_value('Accounts Settings', None, 'over_billing_allowance'))
		else:
			allowance = flt(frappe.get_cached_value('Stock Settings', None, 'over_delivery_receipt_allowance'))

	return allowance


def get_excess_qty_with_allowance(row, completed_field, reference_field, allowance_type):
	"""
		Checks if there is overflow condering a relaxation allowance
	"""
	reference_qty = flt(row.get(reference_field))
	if not reference_qty:
		return 0

	# Allow both: single and multiple completed qty fieldnames
	if not isinstance(completed_field, list):
		completed_field = [completed_field]

	completed_qty = 0
	for f in completed_field:
		completed_qty += flt(row.get(f))

	difference = completed_qty - reference_qty

	# check if overflow is within allowance
	allowance = get_allowance_for(allowance_type, item_code=row.get('item_code'))
	overflow_percent = difference / reference_qty * 100

	excess_qty = 0
	if overflow_percent - allowance > 0.01:
		max_allowed = flt(reference_qty * (100 + allowance) / 100)
		excess_qty = completed_qty - max_allowed

	return excess_qty
