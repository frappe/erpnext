# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, getdate, today, add_days
from dateutil.relativedelta import relativedelta
from frappe.contacts.doctype.contact.contact import get_default_contact
import json


def execute(filters=None):
	return VehicleMaintenanceSchedule(filters).run()


class VehicleMaintenanceSchedule:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.filters.from_date = getdate(self.filters.from_date or today())
		self.filters.to_date = getdate(self.filters.to_date or today())

		self.maintenance_reminder_days = cint(frappe.db.get_value("CRM Settings", None, "maintenance_opportunity_reminder_days"))
		self.filters.follow_up_from_date = add_days(self.filters.from_date, self.maintenance_reminder_days)
		self.filters.follow_up_to_date = add_days(self.filters.to_date, self.maintenance_reminder_days)

		self.communication_columns = 3

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

	def run(self):
		self.get_data()
		self.get_communication_map()
		self.get_follow_up_map()
		self.process_data()
		self.get_columns()
		return self.columns, self.data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			SELECT
				msd.scheduled_date as due_date, msd.project_template, msd.name as maintenance_schedule_row,
				ms.name as maintenance_schedule, ms.customer, ms.customer_name, ms.contact_mobile, ms.contact_phone,
				v.name as vehicle, v.item_code, v.delivery_date, v.chassis_no,
				v.engine_no, v.license_plate, v.unregistered, v.variant_of_name,
				v.customer as vehicle_customer, v.customer_name as vehicle_customer_name,
				pt.project_template_name, opp.name as opportunity, opp.status
			FROM `tabMaintenance Schedule Detail` msd
			LEFT JOIN `tabProject Template` pt ON pt.name = msd.project_template
			LEFT JOIN `tabMaintenance Schedule` ms ON ms.name = msd.parent
			LEFT JOIN `tabVehicle` v ON v.name = ms.serial_no
			LEFT JOIN `tabCustomer` c ON c.name = ms.customer
			LEFT JOIN `tabItem` im ON im.name = v.item_code
			LEFT JOIN `tabOpportunity` opp ON opp.maintenance_schedule = msd.parent AND opp.maintenance_schedule_row = msd.name
			WHERE ifnull(ms.serial_no, '') != '' AND {conditions}
		""".format(conditions=conditions), self.filters, as_dict=1)

	def get_conditions(self):
		conditions = []

		if self.filters.get("date_type") == "Follow Up Date":
			conditions.append("""(
				msd.scheduled_date BETWEEN %(follow_up_from_date)s AND %(follow_up_to_date)s
				OR exists(select fup.name from `tabLead Follow Up` fup where fup.parenttype = 'Opportunity'
					and fup.parent = opp.name and fup.schedule_date BETWEEN %(from_date)s AND %(to_date)s)
			)""")
		else:
			conditions.append("msd.scheduled_date BETWEEN %(from_date)s AND %(to_date)s")

		if self.filters.get("company"):
			conditions.append("ms.company = %(company)s")

		if self.filters.get("project_template"):
			conditions.append("msd.project_template = %(project_template)s")

		if self.filters.get("project_template_category"):
			conditions.append("pt.project_template_category = %(project_template_category)s")

		if self.filters.get("customer"):
			conditions.append("c.name = %(customer)s")

		if self.filters.get("customer_group"):
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""c.customer_group in (select name from `tabCustomer Group`
				where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("variant_of"):
			conditions.append("im.variant_of = %(variant_of)s")

		if self.filters.get("item_code"):
			conditions.append("im.name = %(item_code)s")

		if self.filters.get("item_group"):
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""im.item_group in (select name from `tabItem Group`
				where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("opportunity"):
			conditions.append("opp.name = %(opportunity)s")

		return " AND ".join(conditions) if conditions else ""

	def get_communication_map(self):
		self.communication_map = {}

		opportunities = [d.opportunity for d in self.data if d.get("opportunity")]
		if opportunities:
			communications = frappe.db.sql("""
				SELECT reference_name as opportunity, content,
					CAST(communication_date as DATE) as contact_date
				FROM tabCommunication
				WHERE reference_doctype = 'Opportunity' AND reference_name in %s
					AND communication_type != 'Automated Message' and sent_or_received = 'Received'
				ORDER BY communication_date, creation
			""", [opportunities], as_dict=1)

			for d in communications:
				self.communication_map.setdefault(d.opportunity, []).append(d)

	def get_follow_up_map(self):
		self.follow_up_map = {}

		opportunities = [d.opportunity for d in self.data if d.get("opportunity")]
		if opportunities:
			follow_ups = frappe.db.sql("""
				SELECT parent as opportunity, schedule_date
				FROM `tabLead Follow Up`
				WHERE parenttype = 'Opportunity' AND parent in %s AND ifnull(contact_date, '0000-00-00') = '0000-00-00'
				ORDER BY schedule_date, idx
			""", [opportunities], as_dict=1)

			for d in follow_ups:
				self.follow_up_map.setdefault(d.opportunity, []).append(d)

	def process_data(self):
		for d in self.data:
			d.disable_item_formatter = 1
			d.contact_no = d.contact_mobile or d.contact_phone

			if not d.variant_of_name:
				d.variant_of_name = d.item_name

			if not d.customer:
				d.customer = d.vehicle_customer
				d.customer_name = d.vehicle_customer_name

			if not d.contact_no:
				contact_id = get_default_contact('Customer', d.customer)
				d.contact_no = frappe.db.get_value("Contact", contact_id, "mobile_no", cache=1)

			d.age = self.get_formatted_duration(getdate(), d.delivery_date)
			d.reminder_date = add_days(d.due_date, -1 * self.maintenance_reminder_days)

			if not d.license_plate and d.unregistered:
				d.license_plate = 'Unreg'

			if d.opportunity:
				contact_list = []

				if self.communication_map.get(d.opportunity):
					communications = self.communication_map.get(d.opportunity)
					for c in communications:
						contact_list.append(frappe._dict({
							"communication": c.content,
							"communication_date": c.contact_date,
						}))

				if self.follow_up_map.get(d.opportunity):
					follow_ups = self.follow_up_map.get(d.opportunity)
					for c in follow_ups:
						contact_list.append(frappe._dict({
							"communication_date": c.schedule_date,
						}))

				for i, c in enumerate(contact_list):
					idx = str(i + 1)
					d["communication_" + idx] = c.communication
					d["communication_date_" + idx] = c.communication_date

				self.communication_columns = max(self.communication_columns, len(contact_list))

		self.data = sorted(self.data, key=lambda d: (getdate(d.due_date), getdate(d.delivery_date)))

	def get_formatted_duration(self, start_date, end_date):
		delta = relativedelta(getdate(start_date), getdate(end_date))

		template = ['Y', 'M', 'D']
		data = [delta.years, delta.months, delta.days]

		duration = " ".join([str(x) + y for x, y in zip(data, template) if x or y == 'D'])
		if duration == '0D':
			duration = '-'

		return duration

	def get_columns(self):
		columns = [
			{
				"label": _("Due Date"),
				"fieldname": "due_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Reminder Date"),
				"fieldname": "reminder_date",
				"fieldtype": "Date",
				"width": 90
			},
			# {
			# 	"label": _("Model"),
			# 	"fieldname": "variant_of_name",
			# 	"fieldtype": "Data",
			# 	"width": 120
			# },
			{
				"label": _("Variant Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 120
			},
			# {
			# 	"label": _("Engine No"),
			# 	"fieldname": "engine_no",
			# 	"fieldtype": "Data",
			# 	"width": 115
			# },
			{
				"label": _("Template"),
				"fieldname": "project_template",
				"fieldtype": "Link",
				"options": "Project Template",
				"width": 100
			},
			# {
			# 	"label": _("Template Name"),
			# 	"fieldname": "project_template_name",
			# 	"fieldtype": "Data",
			# 	"width": 180
			# },
			{
				"label": _("Delivery Date"),
				"fieldname": "delivery_date",
				"fieldtype": "Date",
				"width": 90
			},
			{
				"label": _("Age"),
				"fieldname": "age",
				"fieldtype": "Data",
				"width": 80
			},
			{
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 80
			},
			{
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Contact No"),
				"fieldname": "contact_no",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Status"),
				"fieldname": "status",
				"fieldtype": "Data",
				"width": 90
			},
		]

		for i in range(self.communication_columns):
			idx = str(i + 1)
			columns += [
				{
					"label": _("Contact {0}").format(idx),
					"fieldname": "communication_date_" + idx,
					"fieldtype": "Date",
					"width": 80,
					"is_communication": "communcation_date",
				},
				{
					"label": _("Communication {0}").format(idx),
					"fieldname": "communication_" + idx,
					"fieldtype": "Data",
					"options": "Opportunity",
					"width": 200,
					"editable": 1,
					"is_communication": "remarks",
				},
			]

		columns += [
			{
				"label": _("Vehicle"),
				"fieldname": "vehicle",
				"fieldtype": "Link",
				"options": "Vehicle",
				"width": 70
			},
			{
				"label": _("Reg No"),
				"fieldname": "license_plate",
				"fieldtype": "Data",
				"width": 80
			},
			{
				"label": _("Chassis No"),
				"fieldname": "chassis_no",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Schedule"),
				"fieldname": "maintenance_schedule",
				"fieldtype": "Link",
				"options": "Maintenance Schedule",
				"width": 80
			},
			{
				"label": _("Opportunity"),
				"fieldname": "opportunity",
				"fieldtype": "Link",
				"options": "Opportunity",
				"width": 80
			},
		]

		if self.filters.date_type != "Follow Up Date":
			columns = [d for d in columns if d.get('fieldname') != 'reminder_date']

		self.columns = columns


@frappe.whitelist()
def submit_communication_with_action(remarks, action, opportunity=None, follow_up_date=None, lost_reason=None,
		maintenance_schedule=None, maintenance_schedule_row=None, filters=None):
	from erpnext.crm.doctype.opportunity.opportunity import submit_communication_with_action

	out = submit_communication_with_action(remarks, action,
		opportunity=opportunity, follow_up_date=follow_up_date, lost_reason=lost_reason,
		maintenance_schedule=maintenance_schedule, maintenance_schedule_row=maintenance_schedule_row)

	if filters is not None:
		if isinstance(filters, str):
			filters = json.loads(filters)

		filters['opportunity'] = out.opportunity
		out['updated_row'] = execute(filters)
		out['updated_row'] = out['updated_row'][1][0]

	return out
