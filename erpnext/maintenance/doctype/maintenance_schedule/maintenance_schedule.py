# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.utilities.transaction_base import TransactionBase
from dateutil.relativedelta import relativedelta
from frappe.utils import add_days, getdate, cstr, today
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.accounts.party import get_contact_details


class MaintenanceSchedule(TransactionBase):
	def validate(self):
		self.set_missing_values()
		self.validate_serial_no()
		self.validate_schedule()

	def set_missing_values(self):
		self.set_contact_details()

	def set_contact_details(self):
		force = False
		if not self.contact_person and self.customer:
			contact = get_default_contact('Customer', self.customer)
			self.contact_person = contact
			force = True

		if self.contact_person:
			contact_details = get_contact_details(self.contact_person)
			for k, v in contact_details.items():
				if self.meta.has_field(k) and (force or not self.get(k)):
					self.set(k, v)

	def validate_serial_no(self):
		if self.serial_no:
			self.item_code, self.item_name = frappe.db.get_value("Serial No", self.serial_no, ["item_code", "item_name"])

	def validate_schedule(self):
		self.sort_schedules()
		date_template_pairs = set()

		for d in self.schedules:
			date_template_pair = (d.scheduled_date, cstr(d.project_template))
			if date_template_pair not in date_template_pairs:
				date_template_pairs.add(date_template_pair)
			else:
				frappe.throw(_("Row {0}: Duplicate schedule found".format(d.idx)))

	def sort_schedules(self):
		self.schedules.sort(key=lambda x: x.get('scheduled_date'))
		for index, d in enumerate(self.schedules):
			d.idx = index + 1

	def adjust_scheduled_date_for_holiday(self, scheduled_date):
		from erpnext.hr.doctype.holiday_list.holiday_list import get_default_holiday_list

		holiday_list_name = get_default_holiday_list(self.company)

		if holiday_list_name:
			holiday_dates = frappe.db.sql_list("select holiday_date from `tabHoliday` where parent=%s", holiday_list_name)
			if holiday_dates:
				scheduled_date = getdate(scheduled_date)
				while scheduled_date in holiday_dates:
					scheduled_date = add_days(scheduled_date, -1)

		return scheduled_date


def schedule_next_project_template(project_template, serial_no, args):
	if not project_template:
		return

	args = frappe._dict(args)
	if not args.reference_doctype or not args.reference_name:
		frappe.throw(_("Invalid reference for Next Maintenance Schedule"))

	template_details = frappe.db.get_value("Project Template", project_template, ["next_due_after", "next_project_template"], as_dict=1)
	if not template_details or not template_details.next_due_after or not template_details.next_project_template:
		return

	doc = get_maintenance_schedule_doc(serial_no)
	update_customer_and_contact(args, doc)

	existing_templates = [d.get('project_template') for d in doc.get('schedules', []) if d.get('project_template')]

	schedule = frappe._dict({
		'reference_doctype': args.reference_doctype,
		'reference_name': args.reference_name,
		'reference_date': getdate(args.reference_date)
	})

	if template_details.next_project_template not in existing_templates:
		schedule.project_template = template_details.next_project_template
		schedule.scheduled_date = schedule.reference_date + relativedelta(months=template_details.next_due_after)
		schedule.scheduled_date = doc.adjust_scheduled_date_for_holiday(schedule.scheduled_date)

		doc.append('schedules', schedule)
		doc.save(ignore_permissions=True)


def schedule_project_templates_after_delivery(serial_no, args):
	item_code = frappe.db.get_value("Serial No", serial_no, "item_code")
	if not item_code:
		return

	args = frappe._dict(args)
	if not args.reference_doctype or not args.reference_name:
		frappe.throw(_("Invalid reference for Maintenance Schedule after Delivery"))

	schedule_template = frappe._dict({
		'reference_doctype': args.reference_doctype,
		'reference_name': args.reference_name,
		'reference_date': getdate(args.reference_date)
	})

	project_templates = get_project_templates_due_after_delivery(item_code)

	doc = get_maintenance_schedule_doc(serial_no)
	modified = False

	update_customer_and_contact(args, doc)

	existing_templates = [d.get('project_template') for d in doc.get('schedules', []) if d.get('project_template')]

	for d in project_templates:
		if d.name not in existing_templates:
			schedule = schedule_template.copy()
			schedule.project_template = d.name
			schedule.scheduled_date = schedule.reference_date + relativedelta(months=d.due_after_delivery_date)
			schedule.scheduled_date = doc.adjust_scheduled_date_for_holiday(schedule.scheduled_date)
			doc.append('schedules', schedule)

			modified = True

	if modified:
		doc.save(ignore_permissions=True)


def remove_schedule_for_reference_document(serial_no, reference_doctype, reference_name):
	doc = get_maintenance_schedule_doc(serial_no)

	if not doc.get('schedules'):
		return

	to_remove = [d for d in doc.schedules if d.reference_doctype == reference_doctype and d.reference_name == reference_name]
	if to_remove:
		for d in to_remove:
			doc.remove(d)

		doc.save(ignore_permissions=True)


def get_project_templates_due_after_delivery(item_code):
	filters = {'due_after_delivery_date': ['>', 0]}

	fields = ['name', 'due_after_delivery_date']
	order_by = "due_after_delivery_date"

	filters['applies_to_item'] = item_code
	project_templates = frappe.get_all('Project Template', filters=filters, fields=fields, order_by=order_by)

	if not project_templates:
		variant_of = frappe.get_cached_value("Item", item_code, "variant_of")
		if variant_of:
			filters["applies_to_item"] = variant_of
			project_templates = frappe.get_all('Project Template', filters=filters, fields=fields, order_by=order_by)

	return project_templates


def get_maintenance_schedule_doc(serial_no):
	schedule_name = frappe.db.get_value('Maintenance Schedule', filters={'serial_no': serial_no})

	if schedule_name:
		doc = frappe.get_doc('Maintenance Schedule', schedule_name)
	else:
		doc = frappe.new_doc('Maintenance Schedule')
		doc.serial_no = serial_no
		doc.item_code, doc.item_name = frappe.db.get_value("Serial No", serial_no, ["item_code", "item_name"])

	return doc


def update_customer_and_contact(source, target_doc):
	customer_fields = ['customer', 'customer_name']
	contact_fields = ['contact_person', 'contact_display', 'contact_mobile', 'contact_phone', 'contact_email']

	if source.customer:
		for f in customer_fields:
			target_doc.set(f, source.get(f))

		for f in contact_fields:
			target_doc.set(f, None)

	if source.contact_person:
		for f in contact_fields:
			target_doc.set(f, source.get(f))


def get_maintenance_schedule_from_serial_no(serial_no):
	schedule_name = frappe.db.get_value('Maintenance Schedule', filters={'serial_no': serial_no})

	if schedule_name:
		schedule_doc = frappe.get_doc('Maintenance Schedule', schedule_name)
		return schedule_doc.schedules


def create_opportunity_from_schedule(for_date=None):
	if not frappe.db.get_single_value("CRM Settings", "auto_create_opportunity_from_schedule"):
		return

	days_in_advance = frappe.get_cached_value("CRM Settings", None, "auto_create_opportunity_before_days")
	default_opportunity_type = frappe.get_cached_value("CRM Settings", None, "default_opportunity_type_for_schedule")

	for_date = getdate(for_date)
	target_date = getdate(add_days(for_date, days_in_advance))

	schedule_data = frappe.db.sql("""
		select msd.name, msd.parent, msd.project_template
		from `tabMaintenance Schedule Detail` msd
		inner join `tabMaintenance Schedule` ms on ms.name = msd.parent
		where ms.status = 'Active' and msd.scheduled_date = %s
	""", target_date, as_dict=1)

	for schedule in schedule_data:
		schedule_doc = frappe.get_doc('Maintenance Schedule', schedule.parent)
		opportunity_doc = frappe.new_doc('Opportunity')

		opportunity_doc.opportunity_from = 'Customer'
		opportunity_doc.party_name = schedule_doc.customer
		opportunity_doc.transaction_date = getdate(today())
		opportunity_doc.due_date = target_date
		opportunity_doc.status = 'Open'
		opportunity_doc.opportunity_type = default_opportunity_type
		opportunity_doc.applies_to_serial_no = schedule_doc.serial_no

		opportunity_doc.maintenance_schedule = schedule_doc.name
		opportunity_doc.maintenance_schedule_row = schedule.name

		project_template = frappe.get_cached_doc('Project Template', schedule.project_template)
		for d in project_template.applicable_items:
			opportunity_doc.append("items", {
				"item_code": d.applicable_item_code,
				"qty": d.applicable_qty,
			})

		opportunity_doc.save(ignore_permissions=True)
