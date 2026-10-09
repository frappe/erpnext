# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.utils import escape_html, format_date, get_datetime

from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	validate_serial_no_for_customer,
)
from erpnext.utilities.transaction_base import TransactionBase

CLAIM_STATUS = {"Fully Completed": "Closed", "Partially Completed": "Work In Progress"}


class MaintenanceVisit(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.maintenance.doctype.maintenance_visit_purpose.maintenance_visit_purpose import (
			MaintenanceVisitPurpose,
		)

		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		company: DF.Link
		completion_status: DF.Literal["", "Partially Completed", "Fully Completed"]
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.Data | None
		contact_person: DF.Link | None
		customer: DF.Link
		customer_address: DF.Link | None
		customer_feedback: DF.SmallText | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		maintenance_schedule: DF.Link | None
		maintenance_schedule_detail: DF.Link | None
		maintenance_type: DF.Literal["", "Scheduled", "Unscheduled", "Breakdown"]
		mntc_date: DF.Date
		mntc_time: DF.Time | None
		naming_series: DF.Literal["MAT-MVS-.YYYY.-"]
		purposes: DF.Table[MaintenanceVisitPurpose]
		status: DF.Literal["", "Draft", "Cancelled", "Submitted"]
		territory: DF.Link | None
	# end: auto-generated types

	def validate_serial_no(self):
		for d in self.get("purposes"):
			if not d.serial_no:
				continue
			serial = frappe.db.get_value(
				"Serial No", d.serial_no, ["serial_no", "item_code", "warehouse", "customer"], as_dict=True
			)
			if not serial:
				frappe.throw(_("Row #{0}: Selected Serial No no longer exists.").format(d.idx))
			if serial.item_code != d.item_code:
				frappe.throw(
					_("Serial No {0} does not belong to Item {1}").format(
						escape_html(serial.serial_no), escape_html(d.item_code)
					)
				)
			if serial.warehouse and was_delivered_to(d.serial_no, self.customer):
				continue
			validate_serial_no_for_customer(serial, self.customer)

	def validate_purpose_table(self):
		if not self.purposes:
			frappe.throw(_("Add Items in the Purpose Table"), title=_("Purposes Required"))

	def get_schedule_details(self):
		if self.maintenance_schedule_detail:
			return [self.maintenance_schedule_detail]
		return [
			purpose.maintenance_schedule_detail
			for purpose in self.purposes
			if purpose.maintenance_schedule_detail
		]

	def validate_maintenance_date(self):
		for detail in self.get_schedule_details():
			item_ref = frappe.db.get_value("Maintenance Schedule Detail", detail, "item_reference")
			if item_ref:
				start_date, end_date = frappe.db.get_value(
					"Maintenance Schedule Item", item_ref, ["start_date", "end_date"]
				)
				if get_datetime(self.mntc_date) < get_datetime(start_date) or get_datetime(
					self.mntc_date
				) > get_datetime(end_date):
					frappe.throw(
						_("Date must be between {0} and {1}").format(
							format_date(start_date), format_date(end_date)
						)
					)

	def validate_schedule_details(self):
		details = self.get_schedule_details()
		if details:
			self.validate_schedule_customer()
			self.validate_schedule_rows(details)

	def validate_schedule_customer(self):
		schedule = frappe.db.get_value(
			"Maintenance Schedule", self.maintenance_schedule, ["customer", "docstatus"], as_dict=True
		)
		if not schedule or schedule.docstatus != 1:
			frappe.throw(_("Select a submitted Maintenance Schedule for the scheduled visits"))
		if schedule.customer != self.customer:
			frappe.throw(
				_("Customer {0} does not match the customer of Maintenance Schedule {1}").format(
					frappe.bold(self.customer), frappe.bold(self.maintenance_schedule)
				)
			)

	def validate_schedule_rows(self, details):
		items = dict(
			frappe.get_all(
				"Maintenance Schedule Detail",
				filters={"name": ("in", details), "parent": self.maintenance_schedule},
				fields=["name", "item_code"],
				as_list=True,
			)
		)
		if missing := [detail for detail in details if detail not in items]:
			frappe.throw(
				_("Schedule rows {0} do not belong to Maintenance Schedule {1}").format(
					escape_html(", ".join(missing)), frappe.bold(self.maintenance_schedule)
				)
			)
		for purpose in self.purposes:
			row_item = items.get(self.maintenance_schedule_detail or purpose.maintenance_schedule_detail)
			if row_item and row_item != purpose.item_code:
				frappe.throw(
					_("Row #{0}: Item {1} does not match the item of its schedule row").format(
						purpose.idx, frappe.bold(escape_html(purpose.item_code))
					)
				)

	def validate(self):
		self.validate_serial_no()
		self.validate_schedule_details()
		self.validate_maintenance_date()
		self.validate_purpose_table()

	def update_status_and_actual_date(self):
		details = self.get_schedule_details()
		if not details:
			return

		visits = self.get_submitted_schedule_visits(details)
		for detail in details:
			references = [visit for visit in visits if visit.detail == detail]
			fully_completed = [visit for visit in references if visit.completion_status == "Fully Completed"]
			latest = next(iter(fully_completed or references), None)
			frappe.db.set_value(
				"Maintenance Schedule Detail",
				detail,
				{
					"completion_status": latest.completion_status if latest else "Pending",
					"actual_date": latest.mntc_date if latest else None,
				},
			)

	def get_submitted_schedule_visits(self, details):
		"""Submitted visits referencing the schedule rows, latest first."""
		visit = frappe.qb.DocType("Maintenance Visit")
		purpose = frappe.qb.DocType("Maintenance Visit Purpose")
		visits = (
			frappe.qb.from_(visit)
			.inner_join(purpose)
			.on(purpose.parent == visit.name)
			.select(
				visit.maintenance_schedule_detail.as_("header_detail"),
				purpose.maintenance_schedule_detail.as_("detail"),
				visit.completion_status,
				visit.mntc_date,
			)
			.where(
				(visit.docstatus == 1)
				& (
					visit.maintenance_schedule_detail.isin(details)
					| purpose.maintenance_schedule_detail.isin(details)
				)
			)
			.orderby(visit.mntc_date, order=Order.desc)
			.orderby(visit.creation, order=Order.desc)
		).run(as_dict=True)

		for row in visits:
			row.detail = row.header_detail or row.detail
		return visits

	def update_customer_issue(self, flag):
		if not self.maintenance_schedule:
			for d in self.get("purposes"):
				if d.prevdoc_docname and d.prevdoc_doctype == "Warranty Claim":
					if flag == 1:
						mntc_date = self.mntc_date
						service_person = d.service_person
						work_done = d.work_done
						status = CLAIM_STATUS.get(self.completion_status, "Open")
					else:
						mv = frappe.qb.DocType("Maintenance Visit")
						mvp = frappe.qb.DocType("Maintenance Visit Purpose")
						nm = (
							frappe.qb.from_(mv)
							.inner_join(mvp)
							.on(mvp.parent == mv.name)
							.select(
								mv.name, mv.mntc_date, mvp.service_person, mvp.work_done, mv.completion_status
							)
							.where(
								(mvp.prevdoc_docname == d.prevdoc_docname)
								& (mv.name != self.name)
								& (mv.docstatus == 1)
							)
							.orderby(mv.name, order=frappe.qb.desc)
							.limit(1)
							.run()
						)

						if nm:
							status = CLAIM_STATUS.get(nm[0][4], "Open")
							mntc_date = nm and nm[0][1] or ""
							service_person = nm and nm[0][2] or ""
							work_done = nm and nm[0][3] or ""
						else:
							status = "Open"
							mntc_date = None
							service_person = None
							work_done = None

					wc_doc = frappe.get_doc("Warranty Claim", d.prevdoc_docname)
					wc_doc.update(
						{
							"resolution_date": mntc_date,
							"resolved_by": service_person,
							"resolution_details": work_done,
							"status": status,
						}
					)

					wc_doc.db_update()

	def check_if_last_visit(self):
		"""check if last maintenance visit against same Warranty Claim"""
		check_for_docname = None
		for d in self.get("purposes"):
			if d.prevdoc_docname and d.prevdoc_doctype == "Warranty Claim":
				check_for_docname = d.prevdoc_docname

		if check_for_docname:
			mv = frappe.qb.DocType("Maintenance Visit")
			mvp = frappe.qb.DocType("Maintenance Visit Purpose")
			check = (
				frappe.qb.from_(mv)
				.inner_join(mvp)
				.on(mvp.parent == mv.name)
				.select(mv.name)
				.where(
					(mv.name != self.name)
					& (mvp.prevdoc_docname == check_for_docname)
					& (mv.docstatus == 1)
					& (
						(mv.mntc_date > self.mntc_date)
						| ((mv.mntc_date == self.mntc_date) & (mv.mntc_time > self.mntc_time))
					)
				)
				.run(pluck=True)
			)

			if check:
				check_lst = ",".join(check)
				frappe.throw(
					_("Cancel Maintenance Visits {0} before cancelling this Maintenance Visit").format(
						check_lst
					)
				)
				raise Exception
			else:
				self.update_customer_issue(0)

	def on_submit(self):
		self.update_customer_issue(1)
		self.db_set("status", "Submitted")
		self.update_status_and_actual_date()

	def on_cancel(self):
		self.check_if_last_visit()
		self.db_set("status", "Cancelled")
		self.update_status_and_actual_date()

	def on_update(self):
		pass


def was_delivered_to(serial_no, customer):
	"""Whether the serial was ever delivered to the customer, e.g. before coming back for repair."""
	entry = frappe.qb.DocType("Serial and Batch Entry")
	deliveries = (
		frappe.qb.from_(entry)
		.select(entry.voucher_type, entry.voucher_no)
		.where(
			(entry.serial_no == serial_no)
			& (entry.docstatus == 1)
			& (entry.is_cancelled == 0)
			& (entry.type_of_transaction == "Outward")
			& entry.voucher_type.isin(["Delivery Note", "Sales Invoice"])
		)
	).run(as_dict=True)

	for doctype in ("Delivery Note", "Sales Invoice"):
		names = [row.voucher_no for row in deliveries if row.voucher_type == doctype]
		if names and frappe.db.exists(doctype, {"name": ("in", names), "customer": customer}):
			return True
	return False
