# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import cint, flt, cstr, getdate, nowdate
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order import get_booking_payments,\
	separate_customer_and_supplier_payments, separate_advance_and_balance_payments
from frappe.desk.query_report import group_report_data


class VehicleBookingDetailsReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

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
			select m.name, m.transaction_date, m.vehicle_delivered_date,
				m.customer, m.financer, m.customer_name, m.finance_type, m.tax_id, m.tax_cnic, m.supplier,
				m.item_code, m.item_name, m.previous_item_code, item.variant_of, item.item_group, item.brand,
				m.allocation_period, m.delivery_period, m.priority, m.allocation_title,
				m.contact_person, m.contact_mobile, m.contact_phone,
				m.color_1, m.color_2, m.color_3, m.previous_color,
				1 as qty_booked, m.invoice_total, m.status,
				m.customer_advance, m.supplier_advance, m.customer_advance - m.supplier_advance as undeposited_amount,
				m.payment_adjustment, m.customer_outstanding, m.supplier_outstanding,
				GROUP_CONCAT(DISTINCT sp.sales_person SEPARATOR ', ') as sales_person,
				sum(ifnull(sp.allocated_percentage, 100)) as allocated_percentage
			from `tabVehicle Booking Order` m
			inner join `tabItem` item on item.name = m.item_code
			left join `tabVehicle Allocation Period` ap on ap.name = m.allocation_period
			left join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period
			left join `tabSales Team` sp on sp.parent = m.name and sp.parenttype = 'Vehicle Booking Order'
			where m.docstatus = 1 {conditions}
			group by m.name
			order by {order_by}
		""".format(conditions=filter_conditions, order_by=self.order_by), self.filters, as_dict=1)

		return self.data

	def prepare_data(self):
		for d in self.data:
			d.reference_type = 'Vehicle Booking Order'
			d.reference = d.name

			d.disable_item_formatter = cint(self.show_item_name)

			d.qty_delivered = 1 if d.get('vehicle_delivered_date') else 0

			is_leased = d.financer and d.finance_type == "Leased"

			d.vehicle_color = d.vehicle_color or d.color_1 or d.color_2 or d.color_3
			d.tax_cnic_ntn = d.tax_id or d.tax_cnic if is_leased else d.tax_cnic or d.tax_id
			d.contact_number = d.contact_mobile or d.contact_phone

			d.original_item_code = d.get('previous_item_code') or d.item_code

			self.apply_sales_person_contribution(d)

		self.set_payment_details()

		return self.data

	def apply_sales_person_contribution(self, row):
		if self.filters.sales_person:
			row['actual_invoice_total'] = row["invoice_total"]

			fields = ['qty_booked', 'qty_delivered', 'invoice_total']
			for f in fields:
				row[f] *= row.allocated_percentage / 100

	def set_payment_details(self):
		self.get_payment_data()
		for d in self.data:
			booking_payment_entries = self.payment_by_booking.get(d.name) or []

			customer_payments, supplier_payments = separate_customer_and_supplier_payments(booking_payment_entries)
			advance_payments, balance_payments = separate_advance_and_balance_payments(customer_payments, supplier_payments)

			if advance_payments:
				d.advance_payment_date = advance_payments[0].deposit_date
				d.advance_payment_amount = sum([d.amount for d in advance_payments])
			if balance_payments:
				d.balance_payment_date = balance_payments[-1].deposit_date
				d.balance_payment_amount = sum([d.amount for d in balance_payments])

	def get_payment_data(self):
		booking_numbers = list(set([d.name for d in self.data if d.name]))
		payment_entries = get_booking_payments(booking_numbers)

		self.payment_by_booking = {}
		for d in payment_entries:
			self.payment_by_booking.setdefault(d.vehicle_booking_order, []).append(d)

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
		sum_fields = ['invoice_total', 'qty_booked', 'qty_delivered', 'actual_invoice_total',
			'customer_advance', 'supplier_advance', 'advance_payment_amount', 'balance_payment_amount',
			'payment_adjustment', 'customer_outstanding', 'supplier_outstanding', 'undeposited_amount']
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
		if "item_code" in grouped_by:
			totals['original_item_code'] = totals['item_code']
		elif "variant_of" in grouped_by:
			totals['item_code'] = totals['variant_of']
			totals['original_item_code'] = totals['variant_of']

		totals['disable_item_formatter'] = cint(self.show_item_name)

		if totals.get('item_code'):
			totals['item_name'] = frappe.get_cached_value("Item", totals.get('item_code'), 'item_name')

		# Calculate sales person contribution percentage
		if totals.get('actual_invoice_total'):
			totals['allocated_percentage'] = totals['invoice_total'] / totals['actual_invoice_total'] * 100

		return totals

	def get_conditions(self):
		conditions = []

		if self.filters.date_type == "Vehicle Delivered Date":
			self.order_by = "m.vehicle_delivered_date, m.transaction_date, m.name"
			conditions.append('m.vehicle_delivered_date between %(from_date)s and %(to_date)s')
		elif self.filters.date_type == "Delivery Period":
			self.order_by = "dp.from_date, m.transaction_date, m.name"
			conditions.append('((dp.from_date <= %(to_date)s) and (dp.to_date >= %(from_date)s))')
		else:
			self.order_by = "m.transaction_date, m.name"
			conditions.append('m.transaction_date between %(from_date)s and %(to_date)s')

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

		if self.filters.customer:
			conditions.append("vbo.customer = %(customer)s")

		if self.filters.financer:
			conditions.append("vbo.financer = %(financer)s")

		if self.filters.supplier:
			conditions.append("m.supplier = %(supplier)s")

		if self.filters.priority:
			conditions.append("m.priority = 1")

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		return "and {}".format(" and ".join(conditions)) if conditions else ""


	def get_columns(self):
		columns = []

		if self.group_by:
			columns.append({"label": _("Reference"), "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_type", "width": 200})
		else:
			columns.append({"label": _("Booking #"), "fieldname": "name", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 105})

		columns += [
			{"label": _("Booked"), "fieldname": "qty_booked", "fieldtype": "Float", "width": 65, "precision": "1" if self.filters.sales_person else "0"},
			{"label": _("Delivered"), "fieldname": "qty_delivered", "fieldtype": "Float", "width": 75, "precision": "1" if self.filters.sales_person else "0"},
			{"label": _("Booking Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
			{"label": _("Delivery Date"), "fieldname": "vehicle_delivered_date", "fieldtype": "Date", "width": 100},
			# {"label": _("Customer (User)"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 100},
			# {"label": _("Financer"), "fieldname": "financer", "fieldtype": "Link", "options": "Customer", "width": 100},
			{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
			{"label": _("Color"), "fieldname": "vehicle_color", "fieldtype": "Link", "options": "Vehicle Color", "width": 120},
			{"label": _("Delivery Period"), "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period", "width": 110},
		]

		columns.append({"label": _("Sales Person"), "fieldtype": "Data", "fieldname": "sales_person", "width": 150})
		if self.filters.sales_person:
			columns.append({"label": _("% Contribution"), "fieldtype": "Percent", "fieldname": "allocated_percentage", "width": 60})

		columns += [
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
			{"label": _("CNIC/NTN"), "fieldname": "tax_cnic_ntn", "fieldtype": "Data", "width": 110},
			{"label": _("Contact"), "fieldname": "contact_number", "fieldtype": "Data", "width": 110},
			{"label": _("Allocation"), "fieldname": "allocation_title", "fieldtype": "Data", "width": 200},
			{"label": _("Invoice Total"), "fieldname": "invoice_total", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Received"), "fieldname": "customer_advance", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Deposited"), "fieldname": "supplier_advance", "fieldtype": "Currency", "width": 120},
			{"label": _("Undeposited Amount"), "fieldname": "undeposited_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Payment Adjustment"), "fieldname": "payment_adjustment", "fieldtype": "Currency", "width": 120},
			{"label": _("Customer Outstanding"), "fieldname": "customer_outstanding", "fieldtype": "Currency", "width": 120},
			{"label": _("Supplier Outstanding"), "fieldname": "supplier_outstanding", "fieldtype": "Currency", "width": 120},
			{"label": _("Advance Payment Date"), "fieldname": "advance_payment_date", "fieldtype": "Date", "width": 100},
			{"label": _("Advance Payment Amount"), "fieldname": "advance_payment_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Balance Payment Date"), "fieldname": "balance_payment_date", "fieldtype": "Date", "width": 100},
			{"label": _("Balance Payment Amount"), "fieldname": "balance_payment_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("Previous Variant"), "fieldname": "previous_item_code", "fieldtype": "Link", "options": "Item", "width": 120},
			{"label": _("Previous Color"), "fieldname": "previous_color", "fieldtype": "Link", "options": "Vehicle Color", "width": 120},
			{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Data", "width": 100},
		]

		return columns


def execute(filters=None):
	return VehicleBookingDetailsReport(filters).run()
