# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub, unscrub
from frappe.utils import cint, flt, cstr, getdate, nowdate
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from frappe.desk.query_report import group_report_data


class VehicleRegistrationRegisterReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"
		self.show_customer_name = frappe.defaults.get_global_default('cust_master_name') == "Naming Series"

		self.group_by = []

	def run(self):
		self.get_data()
		self.prepare_data()

		data = self.get_grouped_data()
		columns = self.get_columns()

		return columns, data

	def get_data(self):
		filter_conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select m.name, m.vehicle_booking_order,
				m.transaction_date, m.registration_receipt_date, m.call_date,
				m.invoice_delivered_date, m.invoice_issue_date, m.invoice_return_date,
				m.customer, m.customer_name,
				m.registration_customer, m.registration_customer_name,
				m.agent, m.agent_name,
				m.tax_cnic, m.tax_id, m.tax_status,
				m.item_code, m.item_name, item.variant_of, item.item_group, item.brand,
				m.vehicle, m.vehicle_chassis_no, m.vehicle_engine_no, m.vehicle_license_plate,
				m.contact_person, m.contact_mobile, m.contact_phone,
				m.customer_total, m.customer_payment, m.customer_authority_payment, m.customer_outstanding,
				m.authority_total, m.authority_payment, m.authority_outstanding,
				m.agent_total, m.agent_payment, m.agent_outstanding,
				m.margin_amount, m.status, m.remarks
			from `tabVehicle Registration Order` m
			left join `tabItem` item on item.name = m.item_code
			where m.docstatus = 1 {conditions}
			group by m.name
			order by {order_by}
		""".format(conditions=filter_conditions, order_by=self.order_by), self.filters, as_dict=1)

		return self.data

	def prepare_data(self):
		for d in self.data:
			d.reference_type = 'Vehicle Registration Order'
			d.reference = d.name

			d.disable_item_formatter = cint(self.show_item_name)

			d.is_leased = d.financer and d.finance_type == "Leased"
			d.tax_cnic_ntn = d.tax_cnic or d.tax_id
			d.contact_number = d.contact_mobile or d.contact_phone

		return self.data

	def get_grouped_data(self):
		data = self.data

		self.group_by = [None]
		for i in range(3):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue
			elif group_label == "Variant":
				group_field = "item_code"
			elif group_label == "Model":
				group_field = "variant_of"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		if len(self.group_by) <= 1:
			return data

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		# Sum
		sum_fields = [
			'customer_total', 'authority_total', 'agent_total',
			'customer_payment', 'authority_payment', 'agent_payment',
			'customer_outstanding', 'authority_outstanding', 'agent_outstanding',
			'margin_amount'
		]
		for f in sum_fields:
			totals[f] = sum([flt(d.get(f)) for d in data])

		group_reference_doctypes = {
			"item_code": "Item",
			"variant_of": "Item",
			"status": None,
		}

		# set reference field
		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['reference_type'] = reference_dt
		if not group_field:
			totals['reference'] = "'Total'"
		elif not reference_dt:
			totals['reference'] = "'{0}'".format(grouped_by.get(reference_field))
		else:
			totals['reference'] = grouped_by.get(reference_field)

		if not group_field and self.group_by == [None]:
			totals['reference'] = "'Total'"

		# set item_code from model
		if "variant_of" in grouped_by:
			totals['item_code'] = totals['variant_of']

		totals['disable_item_formatter'] = cint(self.show_item_name)

		if totals.get('item_code'):
			totals['item_name'] = frappe.get_cached_value("Item", totals.get('item_code'), 'item_name')

		return totals

	def get_conditions(self):
		conditions = []

		# Date Field and sorting
		date_field = 'm.transaction_date'
		if self.filters.date_type == "Registration Receipt Date":
			self.order_by = "m.registration_receipt_date, m.transaction_date, m.name"
			date_field = "m.registration_receipt_date"
		elif self.filters.date_type == "Call Date":
			self.order_by = "m.call_date, m.transaction_date, m.name"
			date_field = "m.call_date"
		elif self.filters.date_type == "Invoice Delivered Date":
			self.order_by = "m.invoice_delivered_date, m.transaction_date, m.name"
			date_field = "m.invoice_delivered_date"
		elif self.filters.date_type == "Invoice Issue Date":
			self.order_by = "m.invoice_issue_date, m.transaction_date, m.name"
			date_field = "m.invoice_issue_date"
		elif self.filters.date_type == "Invoice Return Date":
			self.order_by = "m.invoice_return_date, m.transaction_date, m.name"
			date_field = "m.invoice_return_date"
		else:
			self.order_by = "m.transaction_date, m.name"
			date_field = "m.transaction_date"

		# Date filter
		if self.filters.from_date:
			conditions.append('{0} >= %(from_date)s'.format(date_field))
		if self.filters.to_date:
			conditions.append('{0} <= %(to_date)s'.format(date_field))

		# Order Status
		if self.filters.order_status == "Open Orders":
			conditions.append("m.status != 'Completed'")
		elif self.filters.order_status == "Closed Orders":
			conditions.append("m.status = 'Completed'")

		# Registration Status
		if self.filters.registration_status == "Registered":
			conditions.append("ifnull(m.vehicle_license_plate, '') != ''")
		elif self.filters.registration_status == "Unregistered":
			conditions.append("ifnull(m.vehicle_license_plate, '') = ''")

		# Invoice Status
		if self.filters.invoice_status:
			conditions.append("m.invoice_status = %(invoice_status)s")

		# Rest of the filters
		if self.filters.company:
			conditions.append("m.company = %(company)s")

		if self.filters.variant_of:
			conditions.append("item.variant_of = %(variant_of)s")

		if self.filters.item_code:
			conditions.append("item.name = %(item_code)s")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		if self.filters.brand:
			conditions.append("item.brand = %(brand)s")

		if self.filters.vehicle:
			conditions.append("m.vehicle = %(vehicle)s")

		if self.filters.vehicle_booking_order:
			conditions.append("m.vehicle_booking_order = %(vehicle_booking_order)s")

		if self.filters.customer:
			conditions.append("m.customer = %(customer)s")

		if self.filters.registration_customer:
			conditions.append("m.registration_customer = %(registration_customer)s")

		if self.filters.agent:
			conditions.append("m.agent = %(agent)s")

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		columns = []

		if self.group_by and len(self.group_by) > 1:
			columns.append({"label": _("Reference"), "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_type", "width": 200})
		else:
			columns.append({"label": _("Registration Order"), "fieldname": "name", "fieldtype": "Link", "options": "Vehicle Registration Order", "width": 140})

		columns += [
			{"label": _("Order Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 80},
			{"label": _("Registration Customer"), "fieldname": "registration_customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 105},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Reg No"), "fieldname": "vehicle_license_plate", "fieldtype": "Data", "width": 70},
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
			{"label": _("Customer Total"), "fieldname": "customer_total", "fieldtype": "Currency", "width": 110},
			{"label": _("Customer Payment"), "fieldname": "customer_payment", "fieldtype": "Currency", "width": 110},
			{"label": _("Customer Outstanding"), "fieldname": "customer_outstanding", "fieldtype": "Currency", "width": 110},
			{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150},
			{"label": _("Agent"), "fieldname": "agent", "fieldtype": "Link", "options": "Supplier", "width": 100},
			{"label": _("Authority Total"), "fieldname": "authority_total", "fieldtype": "Currency", "width": 110},
			{"label": _("Agent Total"), "fieldname": "agent_total", "fieldtype": "Currency", "width": 110},
			{"label": _("Margin"), "fieldname": "margin_amount", "fieldtype": "Currency", "width": 100},
			{"label": _("Registration Date"), "fieldname": "registration_receipt_date", "fieldtype": "Date", "width": 120},
			{"label": _("Call Date"), "fieldname": "call_date", "fieldtype": "Date", "width": 80},
			{"label": _("Invoice Issue Date"), "fieldname": "invoice_issue_date", "fieldtype": "Date", "width": 120},
			{"label": _("Invoice Return Date"), "fieldname": "invoice_return_date", "fieldtype": "Date", "width": 120},
			{"label": _("Invoice Delivered Date"), "fieldname": "invoice_delivered_date", "fieldtype": "Date", "width": 120},
			{"label": _("Vehicle"), "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
			{"label": _("Chassis No"), "fieldname": "vehicle_chassis_no", "fieldtype": "Data", "width": 150},
			{"label": _("Engine No"), "fieldname": "vehicle_engine_no", "fieldtype": "Data", "width": 115},
			{"label": _("Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 110},
			{"label": _("Payment Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		]

		return columns


def execute(filters=None):
	return VehicleRegistrationRegisterReport(filters).run()
