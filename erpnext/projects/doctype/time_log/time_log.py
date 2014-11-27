# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import cstr, cint, comma_and


class OverlapError(frappe.ValidationError): pass
class OverProductionError(frappe.ValidationError): pass
class NotSubmittedError(frappe.ValidationError): pass

from frappe.model.document import Document

class TimeLog(Document):

	def validate(self):
		self.set_status()
		self.validate_overlap()
		self.validate_timings()
		self.calculate_total_hours()
		self.check_workstation_timings()
		self.validate_qty()
		self.validate_production_order()

	def on_submit(self):
		self.update_production_order()

	def on_cancel(self):
		self.update_production_order_on_cancel()

	def calculate_total_hours(self):
		from frappe.utils import time_diff_in_hours
		self.hours = time_diff_in_hours(self.to_time, self.from_time)

	def set_status(self):
		self.status = {
			0: "Draft",
			1: "Submitted",
			2: "Cancelled"
		}[self.docstatus or 0]

		if self.time_log_batch:
			self.status="Batched for Billing"

		if self.sales_invoice:
			self.status="Billed"

	def validate_overlap(self):
		"""Checks if 'Time Log' entries overlap each other. """
		existing = frappe.db.sql_list("""select name from `tabTime Log` where owner=%s and
			(
				(from_time between %s and %s) or
				(to_time between %s and %s) or
				(%s between from_time and to_time))
			and name!=%s
			and ifnull(task, "")=%s
			and docstatus < 2""",
			(self.owner, self.from_time, self.to_time, self.from_time,
				self.to_time, self.from_time, self.name or "No Name",
				cstr(self.task)))

		if existing:
			frappe.throw(_("This Time Log conflicts with {0}").format(comma_and(existing)), OverlapError)
			
	def validate_timings(self):
		if self.to_time < self.from_time:
			frappe.throw(_("From Time cannot be greater than To Time"))

	def before_cancel(self):
		self.set_status()

	def before_update_after_submit(self):
		self.set_status()

	def update_production_order(self):
		"""Updates `start_date`, `end_date` for operation in Production Order."""
		if self.time_log_for=="Manufacturing" and self.operation:
			d = self.get_qty_and_status()
			required_qty = cint(frappe.db.get_value("Production Order" , self.production_order, "qty"))
			if  d.get('qty') == required_qty:
				d['status'] = "Completed" 

			dates = self.get_production_dates()
			if self.from_time < dates.start_date:
				dates.start_date = self.from_time
			if self.to_time > dates.end_date:
				dates.end_date = self.to_time

			self.production_order_update(dates, d.get('qty'), d['status'])

	def update_production_order_on_cancel(self):
		"""Updates operations in 'Production Order' when an associated 'Time Log' is cancelled."""
		if self.time_log_for=="Manufacturing" and self.operation:
			d = frappe._dict()
			d = self.get_qty_and_status()
			dates = self.get_production_dates()
			self.production_order_update(dates, d.get('qty'), d.get('status'))

	def get_qty_and_status(self):
		"""Returns quantity and status of Operation in 'Time Log'. """
		status = "Work in Progress"
		qty = cint(frappe.db.sql("""select sum(qty) as qty from `tabTime Log` where production_order = %s
			and operation = %s and docstatus=1""", (self.production_order, self.operation),as_dict=1)[0].qty)
		if qty == 0:
			status = "Pending" 
		return {
			"qty": qty,
			"status": status
		}

	def get_production_dates(self):
		"""Returns Min From and Max To Dates of Time Logs against a specific Operation. """
		return frappe.db.sql("""select min(from_time) as start_date, max(to_time) as end_date from `tabTime Log` 
				where production_order = %s and operation = %s and docstatus=1""",
				(self.production_order, self.operation), as_dict=1)[0]		

	def production_order_update(self, dates, qty, status):
		"""Updates 'Produuction Order' and sets 'Actual Start Time', 'Actual End Time', 'Status', 'Compleated Qty'. """
		d = self.operation.split('. ',1)
		actual_op_time = self.get_actual_op_time().time_diff
		if actual_op_time == None:
			actual_op_time = 0
		actual_op_cost = self.get_actual_op_cost(actual_op_time)
		frappe.db.sql("""update `tabProduction Order Operation` set actual_start_time = %s, actual_end_time = %s, qty_completed = %s, 
		status = %s, actual_operation_time = %s, actual_operating_cost = %s where idx=%s and parent=%s and operation = %s """,
			(dates.start_date, dates.end_date, qty, status, actual_op_time, actual_op_cost, d[0], self.production_order, d[1] ))
			
	def get_actual_op_time(self):
		"""Returns 'Actual Operating Time'. """
		return frappe.db.sql("""select sum(time_to_sec(timediff(to_time, from_time))/60) as time_diff from 
			`tabTime Log` where production_order = %s and operation = %s and docstatus=1""",
			(self.production_order, self.operation), as_dict = 1)[0]
			
	def get_actual_op_cost(self, actual_op_time):
		"""Returns 'Actual Operating Cost'. """
		if self.operation:
			d = self.operation.split('. ',1)
			idx = d[0]
			operation = d[1]

			hour_rate = frappe.db.sql("""select hour_rate from `tabProduction Order Operation` where idx=%s and 
				parent=%s and operation = %s""", (idx, self.production_order, operation), as_dict=1)[0].hour_rate
			return hour_rate * actual_op_time
			
	def check_workstation_timings(self):
		"""Checks if **Time Log** is between operating hours of the **Workstation**."""
		if self.workstation:
			frappe.get_doc("Workstation", self.workstation).check_if_within_operating_hours(self.from_time, self.to_time)

	def validate_qty(self):
		"""Throws `OverProductionError` if quantity surpasses **Production Order** quantity."""
		if self.qty == None:
			self.qty=0
		required_qty = cint(frappe.db.get_value("Production Order" , self.production_order, "qty"))
		completed_qty = self.get_qty_and_status().get('qty')
		if (completed_qty + cint(self.qty)) > required_qty:
			frappe.throw(_("Quantity cannot be greater than pending quantity that is {0}").format(required_qty), OverProductionError)
			
	def validate_production_order(self):
		"""Throws 'NotSubmittedError' if **production order** is not submitted. """
		if self.production_order:
			if frappe.db.get_value("Production Order", self.production_order, "docstatus") != 1 :
				frappe.throw(_("You cannot make a time log against a production order that has not been submitted.")
				, NotSubmittedError)
				
@frappe.whitelist()
def get_workstation(production_order, operation):
	"""Returns workstation name from Production Order against an associated Operation.
	
	:param production_order string
	:param operation string
	"""
	if operation:
		d = operation.split('. ',1)
		idx = d[0]
		operation = d[1]

		return frappe.db.sql("""select workstation from `tabProduction Order Operation` where idx=%s and 
			parent=%s and operation = %s""", (idx, production_order, operation), as_dict=1)[0]

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.
	
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters like workstation, project etc.
	"""
	from frappe.desk.reportview import build_match_conditions
	if not frappe.has_permission("Time Log"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	match = build_match_conditions("Time Log")
	
	conditions = build_match_conditions("Time Log")
	conditions = conditions and (" and " + conditions) or ""
	if filters:
		filters = json.loads(filters)
		for key in filters:
			if filters[key]:
				conditions += " and " + key + ' = "' + filters[key].replace('"', '\"') + '"'

	data = frappe.db.sql("""select name, from_time, to_time,
		activity_type, task, project, production_order, workstation from `tabTime Log`
		where ( from_time between %(start)s and %(end)s or to_time between %(start)s and %(end)s )
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
			}, as_dict=True, update={"allDay": 0})
	
	for d in data:
		d.title = d.name + ": " + (d.activity_type or d.production_order or "")
		if d.task:
			d.title += " for Task: " + d.task
		if d.project:
			d.title += " for Project: " + d.project

	return data
