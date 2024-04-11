# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, throw
from frappe.utils import add_days, cint, cstr, date_diff, formatdate, getdate

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.utilities.transaction_base import TransactionBase, delete_events


class MaintenanceSchedule(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.maintenance.doctype.maintenance_schedule_detail.maintenance_schedule_detail import (
			MaintenanceScheduleDetail,
		)
		from erpnext.maintenance.doctype.maintenance_schedule_item.maintenance_schedule_item import (
			MaintenanceScheduleItem,
		)

		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.Data | None
		contact_person: DF.Link | None
		customer: DF.Link | None
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		items: DF.Table[MaintenanceScheduleItem]
		naming_series: DF.Literal["MAT-MSH-.YYYY.-"]
		schedules: DF.Table[MaintenanceScheduleDetail]
		status: DF.Literal["", "Draft", "Submitted", "Cancelled"]
		territory: DF.Link | None
		transaction_date: DF.Date
	# end: auto-generated types

	@frappe.whitelist()
	def generate_schedule(self):
		if self.docstatus != 0:
			return
		self.set("schedules", [])
		count = 1
		for d in self.get("items"):
			self.validate_maintenance_detail()
			s_list = []
			s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.sales_person)
			for i in range(d.no_of_visits):
				child = self.append("schedules")
				child.item_code = d.item_code
				child.item_name = d.item_name
				child.scheduled_date = s_list[i].strftime("%Y-%m-%d")
				if d.serial_no:
					child.serial_no = d.serial_no
				child.idx = count
				count = count + 1
				child.sales_person = d.sales_person
				child.completion_status = "Pending"
				child.item_reference = d.name

	@frappe.whitelist()
	def validate_end_date_visits(self):
		days_in_period = {"Weekly": 7, "Monthly": 30, "Quarterly": 91, "Half Yearly": 182, "Yearly": 365}
		for item in self.items:
			if item.periodicity and item.periodicity != "Random" and item.start_date:
				if not item.end_date:
					if item.no_of_visits:
						item.end_date = add_days(
							item.start_date, item.no_of_visits * days_in_period[item.periodicity]
						)
					else:
						item.end_date = add_days(item.start_date, days_in_period[item.periodicity])

				diff = date_diff(item.end_date, item.start_date) + 1
				no_of_visits = cint(diff / days_in_period[item.periodicity])

				if not item.no_of_visits or item.no_of_visits == 0:
					item.end_date = add_days(item.start_date, days_in_period[item.periodicity])
					diff = date_diff(item.end_date, item.start_date) + 1
					item.no_of_visits = cint(diff / days_in_period[item.periodicity])

				elif item.no_of_visits > no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

				elif item.no_of_visits < no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

	def on_submit(self):
		if not self.get("schedules"):
			throw(_("Please click on 'Generate Schedule' to get schedule"))
		self.check_serial_no_added()
		self.validate_schedule()

		email_map = {}
		for d in self.get("items"):
			if d.serial_and_batch_bundle:
				serial_nos = frappe.get_doc(
					"Serial and Batch Bundle", d.serial_and_batch_bundle
				).get_serial_nos()

				if serial_nos:
					self.validate_serial_no(d.item_code, serial_nos, d.start_date)
					self.update_amc_date(serial_nos, d.end_date)

			no_email_sp = []
			if d.sales_person and d.sales_person not in email_map:
				sp = frappe.get_doc("Sales Person", d.sales_person)
				try:
					email_map[d.sales_person] = sp.get_email_id()
				except frappe.ValidationError:
					no_email_sp.append(d.sales_person)

			if no_email_sp:
				frappe.msgprint(
					_(
						"Setting Events to {0}, since the Employee attached to the below Sales Persons does not have a User ID{1}"
					).format(self.owner, "<br>" + "<br>".join(no_email_sp))
				)

			scheduled_date = frappe.db.get_all(
				"Maintenance Schedule Detail",
				{"parent": self.name, "item_code": d.item_code},
				["scheduled_date"],
				as_list=False,
			)

			for key in scheduled_date:
				description = frappe._("Reference: {0}, Item Code: {1} and Customer: {2}").format(
					self.name, d.item_code, self.customer
				)
				event = frappe.get_doc(
					{
						"doctype": "Event",
						"owner": email_map.get(d.sales_person, self.owner),
						"subject": description,
						"description": description,
						"starts_on": cstr(key["scheduled_date"]) + " 10:00:00",
						"event_type": "Private",
					}
				)
				event.add_participant(self.doctype, self.name)
				event.insert(ignore_permissions=1)

		self.db_set("status", "Submitted")

	def create_schedule_list(self, start_date, end_date, no_of_visit, sales_person):
		schedule_list = []
		start_date_copy = start_date
		date_diff = (getdate(end_date) - getdate(start_date)).days
		add_by = date_diff / no_of_visit

		for _visit in range(cint(no_of_visit)):
			if getdate(start_date_copy) < getdate(end_date):
				start_date_copy = add_days(start_date_copy, add_by)
				if len(schedule_list) < no_of_visit:
					schedule_date = self.validate_schedule_date_for_holiday_list(
						getdate(start_date_copy), sales_person
					)
					if schedule_date > getdate(end_date):
						schedule_date = getdate(end_date)
					schedule_list.append(schedule_date)

		return schedule_list

	def validate_schedule_date_for_holiday_list(self, schedule_date, sales_person):
		validated = False

		employee = frappe.db.get_value("Sales Person", sales_person, "employee")
		if employee:
			holiday_list = get_holiday_list_for_employee(employee)
		else:
			holiday_list = frappe.get_cached_value("Company", self.company, "default_holiday_list")

		holidays = frappe.db.sql_list(
			"""select holiday_date from `tabHoliday` where parent=%s""", holiday_list
		)

		if not validated and holidays:
			# max iterations = len(holidays)
			for _i in range(len(holidays)):
				if schedule_date in holidays:
					schedule_date = add_days(schedule_date, -1)
				else:
					validated = True
					break

		return schedule_date

	def validate_dates_with_periodicity(self):
		for d in self.get("items"):
			if d.start_date and d.end_date and d.periodicity and d.periodicity != "Random":
				date_diff = (getdate(d.end_date) - getdate(d.start_date)).days + 1
				days_in_period = {
					"Weekly": 7,
					"Monthly": 30,
					"Quarterly": 90,
					"Half Yearly": 180,
					"Yearly": 365,
				}

				if date_diff < days_in_period[d.periodicity]:
					throw(
						_(
							"Row {0}: To set {1} periodicity, difference between from and to date must be greater than or equal to {2}"
						).format(d.idx, d.periodicity, days_in_period[d.periodicity])
					)

	def validate_maintenance_detail(self):
		if not self.get("items"):
			throw(_("Please enter Maintaince Details first"))

		for d in self.get("items"):
			if not d.item_code:
				throw(_("Please select item code"))
			elif not d.start_date or not d.end_date:
				throw(_("Please select Start Date and End Date for Item {0}").format(d.item_code))
			elif not d.no_of_visits:
				throw(_("Please mention no of visits required"))

			if getdate(d.start_date) >= getdate(d.end_date):
				throw(_("Start date should be less than end date for Item {0}").format(d.item_code))

	def validate_sales_order(self):
		for d in self.get("items"):
			if d.sales_order:
				chk = frappe.db.sql(
					"""select ms.name from `tabMaintenance Schedule` ms,
					`tabMaintenance Schedule Item` msi where msi.parent=ms.name and
					msi.sales_order=%s and ms.docstatus=1""",
					d.sales_order,
				)
				if chk:
					throw(_("Maintenance Schedule {0} exists against {1}").format(chk[0][0], d.sales_order))

	def validate_items_table_change(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return
		for prev_item, item in zip(doc_before_save.items, self.items, strict=False):
			fields = [
				"item_code",
				"start_date",
				"end_date",
				"periodicity",
				"sales_person",
				"no_of_visits",
				"serial_no",
			]
			for field in fields:
				b_doc = prev_item.as_dict()
				doc = item.as_dict()
				if cstr(b_doc[field]) != cstr(doc[field]):
					return True

	def validate_no_of_visits(self):
		return len(self.schedules) != sum(d.no_of_visits for d in self.items)

	def validate(self):
		self.validate_end_date_visits()
		self.validate_maintenance_detail()
		self.validate_dates_with_periodicity()
		self.validate_sales_order()
		self.validate_serial_no_bundle()
		if not self.schedules or self.validate_items_table_change() or self.validate_no_of_visits():
			self.generate_schedule()

	def validate_serial_no_bundle(self):
		ids = [d.serial_and_batch_bundle for d in self.items if d.serial_and_batch_bundle]

		if not ids:
			return

		voucher_nos = frappe.get_all(
			"Serial and Batch Bundle", fields=["name", "voucher_type"], filters={"name": ("in", ids)}
		)

		for row in voucher_nos:
			if row.voucher_type != "Maintenance Schedule":
				msg = f"""Serial and Batch Bundle {row.name}
					should have voucher type as 'Maintenance Schedule'"""

				frappe.throw(_(msg))

	def on_update(self):
		self.db_set("status", "Draft")

	def update_amc_date(self, serial_nos, amc_expiry_date=None):
		for serial_no in serial_nos:
			serial_no_doc = frappe.get_doc("Serial No", serial_no)
			serial_no_doc.amc_expiry_date = amc_expiry_date
			serial_no_doc.save()

	def validate_serial_no(self, item_code, serial_nos, amc_start_date):
		for serial_no in serial_nos:
			sr_details = frappe.db.get_value(
				"Serial No",
				serial_no,
				["warranty_expiry_date", "amc_expiry_date", "warehouse", "delivery_date", "item_code"],
				as_dict=1,
			)

			if not sr_details:
				frappe.throw(_("Serial No {0} not found").format(serial_no))

			if sr_details.get("item_code") != item_code:
				frappe.throw(
					_("Serial No {0} does not belong to Item {1}").format(
						frappe.bold(serial_no), frappe.bold(item_code)
					),
					title=_("Invalid"),
				)

			if sr_details.warranty_expiry_date and getdate(sr_details.warranty_expiry_date) >= getdate(
				amc_start_date
			):
				throw(
					_("Serial No {0} is under warranty upto {1}").format(
						serial_no, sr_details.warranty_expiry_date
					)
				)

			if sr_details.amc_expiry_date and getdate(sr_details.amc_expiry_date) >= getdate(amc_start_date):
				throw(
					_("Serial No {0} is under maintenance contract upto {1}").format(
						serial_no, sr_details.amc_expiry_date
					)
				)

			if (
				not sr_details.warehouse
				and sr_details.delivery_date
				and getdate(sr_details.delivery_date) >= getdate(amc_start_date)
			):
				throw(
					_("Maintenance start date can not be before delivery date for Serial No {0}").format(
						serial_no
					)
				)

	def validate_schedule(self):
		item_lst1 = []
		item_lst2 = []
		for d in self.get("items"):
			if d.item_code not in item_lst1:
				item_lst1.append(d.item_code)

		for m in self.get("schedules"):
			if m.item_code not in item_lst2:
				item_lst2.append(m.item_code)

		if len(item_lst1) != len(item_lst2):
			throw(
				_(
					"Maintenance Schedule is not generated for all the items. Please click on 'Generate Schedule'"
				)
			)
		else:
			for x in item_lst1:
				if x not in item_lst2:
					throw(_("Please click on 'Generate Schedule'"))

	def check_serial_no_added(self):
		serial_present = []
		for d in self.get("items"):
			if d.serial_no:
				serial_present.append(d.item_code)

		for m in self.get("schedules"):
			if serial_present:
				if m.item_code in serial_present and not m.serial_no:
					throw(
						_("Please click on 'Generate Schedule' to fetch Serial No added for Item {0}").format(
							m.item_code
						)
					)

	def on_cancel(self):
		for d in self.get("items"):
			if d.serial_and_batch_bundle:
				serial_nos = frappe.get_doc(
					"Serial and Batch Bundle", d.serial_and_batch_bundle
				).get_serial_nos()

				if serial_nos:
					self.update_amc_date(serial_nos)

		self.db_set("status", "Cancelled")
		delete_events(self.doctype, self.name)

	def on_trash(self):
		delete_events(self.doctype, self.name)

	@frappe.whitelist()
	def get_pending_data(self, data_type, s_date=None, item_name=None):
		if data_type == "date":
			dates = ""
			for schedule in self.schedules:
				if schedule.item_name == item_name and schedule.completion_status == "Pending":
					dates = dates + "\n" + formatdate(schedule.scheduled_date, "dd-MM-yyyy")
			return dates
		elif data_type == "items":
			items = ""
			for item in self.items:
				for schedule in self.schedules:
					if item.item_name == schedule.item_name and schedule.completion_status == "Pending":
						items = items + "\n" + item.item_name
						break
			return items
		elif data_type == "id":
			for schedule in self.schedules:
				if schedule.item_name == item_name and s_date == formatdate(
					schedule.scheduled_date, "dd-mm-yyyy"
				):
					return schedule.name


@frappe.whitelist()
def get_serial_nos_from_schedule(item_code, schedule=None):
	serial_nos = []
	if schedule:
		serial_nos = frappe.db.get_value(
			"Maintenance Schedule Item", {"parent": schedule, "item_code": item_code}, "serial_no"
		)

	if serial_nos:
		serial_nos = get_serial_nos(serial_nos)

	return serial_nos


@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None, item_name=None, s_id=None):
	from frappe.model.mapper import get_mapped_doc

	def condition(doc):
		if s_id:
			return doc.name == s_id
		elif item_name:
			return doc.item_name == item_name

		return True

	def update_status_and_detail(source, target, parent):
		target.maintenance_type = "Scheduled"

	def update_serial(source, target, parent):
		if source.item_reference:
			if sbb := frappe.db.get_value(
				"Maintenance Schedule Item", source.item_reference, "serial_and_batch_bundle"
			):
				serial_nos = frappe.get_doc("Serial and Batch Bundle", sbb).get_serial_nos()

				if len(serial_nos) == 1:
					target.serial_no = serial_nos[0]
				else:
					target.serial_no = ""

	doclist = get_mapped_doc(
		"Maintenance Schedule",
		source_name,
		{
			"Maintenance Schedule": {
				"doctype": "Maintenance Visit",
				"field_map": {"name": "maintenance_schedule"},
				"validation": {"docstatus": ["=", 1]},
				"postprocess": update_status_and_detail,
			},
			"Maintenance Schedule Detail": {
				"doctype": "Maintenance Visit Purpose",
				"condition": condition,
				"field_map": {
					"sales_person": "service_person",
					"name": "maintenance_schedule_detail",
				},
				"postprocess": update_serial,
			},
		},
		target_doc,
	)

	return doclist
