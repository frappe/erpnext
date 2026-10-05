# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Timesheet billing helpers for Sales Invoice."""

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data


class TimesheetBillingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_time_sheets_are_submitted(self) -> None:
		for data in self.doc.timesheets:
			if data.time_sheet and data.timesheet_detail:
				if sales_invoice := frappe.db.get_value(
					"Timesheet Detail", data.timesheet_detail, "sales_invoice"
				):
					frappe.throw(
						_("Row {0}: Sales Invoice {1} is already created for {2}").format(
							data.idx, frappe.bold(sales_invoice), frappe.bold(data.time_sheet)
						)
					)

			if data.time_sheet:
				status = frappe.db.get_value("Timesheet", data.time_sheet, "status")
				if status not in ["Submitted", "Payslip", "Partially Billed"]:
					frappe.throw(
						_("Timesheet {0} cannot be invoiced in its current state").format(data.time_sheet)
					)

	def update_time_sheet(self, sales_invoice: str | None) -> None:
		for d in self.doc.timesheets:
			if d.time_sheet:
				timesheet = frappe.get_doc("Timesheet", d.time_sheet)
				self._update_time_sheet_detail(timesheet, d, sales_invoice)
				timesheet.calculate_total_amounts()
				timesheet.calculate_percentage_billed()
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.db_update_all()

	def unlink_sales_invoice_from_timesheets(self) -> None:
		for row in self.doc.timesheets:
			timesheet = frappe.get_doc("Timesheet", row.time_sheet)
			timesheet.unlink_sales_invoice(self.doc.name)
			timesheet.flags.ignore_validate_update_after_submit = True
			timesheet.db_update_all()

	def set_billing_hours_and_amount(self) -> None:
		"""Fill rows from their time logs; a row without one is replaced by its timesheet's unbilled logs."""
		doc = self.doc
		if doc.is_return:
			return

		pending = [
			row
			for row in doc.timesheets
			if row.time_sheet and not (row.timesheet_detail and row.billing_hours and row.billing_amount)
		]
		unbilled_logs = {
			name: get_projectwise_timesheet_data(doc.project, name)
			for name in {row.time_sheet for row in pending}
		}
		for row in pending:
			if row.timesheet_detail:
				self.fill_from_time_log(row, unbilled_logs[row.time_sheet])
			else:
				self.replace_with_time_logs(row, unbilled_logs[row.time_sheet])

	def fill_from_time_log(self, row, time_logs: list) -> None:
		if log := next((log for log in time_logs if log.name == row.timesheet_detail), None):
			row.billing_hours = row.billing_hours or log.billing_hours
			row.billing_amount = row.billing_amount or log.billing_amount

	def replace_with_time_logs(self, row, time_logs: list) -> None:
		listed = {d.timesheet_detail for d in self.doc.timesheets}
		time_logs = [log for log in time_logs if log.name not in listed]
		if not time_logs:
			frappe.throw(
				_("Row {0}: Timesheet {1} has no unbilled billable time logs").format(
					row.idx, frappe.bold(row.time_sheet)
				)
			)

		self.doc.remove(row)
		for log in time_logs:
			self.doc.append("timesheets", self.get_timesheet_row(log))

	def update_timesheet_billing_for_project(self) -> None:
		doc = self.doc
		if (
			not doc.is_return
			and not doc.timesheets
			and doc.project
			and frappe.db.get_single_value("Projects Settings", "fetch_timesheet_in_sales_invoice")
		):
			self.add_timesheet_data()
		else:
			self.calculate_billing_amount_for_timesheet()

	def add_timesheet_data(self) -> None:
		doc = self.doc
		doc.set("timesheets", [])
		if doc.project:
			for data in get_projectwise_timesheet_data(doc.project):
				doc.append("timesheets", self.get_timesheet_row(data))
			self.calculate_billing_amount_for_timesheet()

	@staticmethod
	def get_timesheet_row(time_log) -> dict:
		return {
			"time_sheet": time_log.time_sheet,
			"billing_hours": time_log.billing_hours,
			"billing_amount": time_log.billing_amount,
			"timesheet_detail": time_log.name,
			"activity_type": time_log.activity_type,
			"description": time_log.description,
		}

	def calculate_billing_amount_for_timesheet(self) -> None:
		doc = self.doc
		doc.total_billing_amount = sum(flt(ts.billing_amount) for ts in doc.timesheets)
		doc.total_billing_hours = sum(flt(ts.billing_hours) for ts in doc.timesheets)

	def _update_time_sheet_detail(self, timesheet, args, sales_invoice: str | None) -> None:
		for data in timesheet.time_logs:
			if args.timesheet_detail == data.name and self._should_set_sales_invoice(data, sales_invoice):
				data.sales_invoice = sales_invoice

	def _should_set_sales_invoice(self, time_log, sales_invoice: str | None) -> bool:
		"""Whether this time log's sales-invoice link should be (re)set to sales_invoice."""
		doc = self.doc
		if doc.project:
			return True
		if not time_log.sales_invoice:
			return True
		if not sales_invoice and time_log.sales_invoice == doc.name:
			# clearing the link on cancellation of this invoice
			return True
		# clearing the link on a return raised against the original invoice
		return bool(
			doc.is_return
			and doc.return_against
			and not sales_invoice
			and time_log.sales_invoice == doc.return_against
		)
