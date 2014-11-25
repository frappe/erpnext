# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import cstr, cint, comma_and



class OverlapError(frappe.ValidationError): pass

from frappe.model.document import Document

class TimeLog(Document):

	def validate(self):
		self.set_status()
		self.validate_overlap()
		self.calculate_total_hours()
		self.check_workstation_timings()
		self.validate_qty()

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

	def before_cancel(self):
		self.set_status()

	def before_update_after_submit(self):
		self.set_status()

	def update_production_order(self):
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
		if self.time_log_for=="Manufacturing" and self.operation:
			d = frappe._dict()
			d = self.get_qty_and_status()
			dates = self.get_production_dates()
			self.production_order_update(dates, d.get('qty'), d.get('status'))

	def get_qty_and_status(self):
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
		return frappe.db.sql("""select min(from_time) as start_date, max(to_time) as end_date from `tabTime Log` 
				where production_order = %s and operation = %s and docstatus=1""",
				(self.production_order, self.operation), as_dict=1)[0]		

	def production_order_update(self, dates, qty, status):
		d = self.operation.split('. ',1)
		frappe.db.sql("""update `tabProduction Order Operation` set actual_start_time = %s, actual_end_time = %s,
			qty_completed = %s, status = %s where idx=%s and parent=%s and operation = %s """,
			(dates.start_date, dates.end_date, qty, status, d[0], self.production_order, d[1] ))

	def check_workstation_timings(self):
		if self.workstation:
			frappe.get_doc("Workstation", self.workstation).check_if_within_operating_hours(self.from_time, self.to_time)

	def validate_qty(self):
		if self.qty == None:
			self.qty=0
		required_qty = cint(frappe.db.get_value("Production Order" , self.production_order, "qty"))
		completed_qty = self.get_qty_and_status().get('qty')
		if (completed_qty + cint(self.qty)) > required_qty:
			frappe.throw(_("Quantity cannot be greater than pending quantity that is {0}").format(required_qty))

@frappe.whitelist()
def get_workstation(production_order, operation):
	if operation:
		d = operation.split('. ',1)
		idx = d[0]
		operation = d[1]

		return frappe.db.sql("""select workstation from `tabProduction Order Operation` where idx=%s and 
			parent=%s and operation = %s""", (idx, production_order, operation), as_dict=1)[0]

@frappe.whitelist()
def get_events(start, end, filters=None):
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
