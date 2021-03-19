# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import cint, cstr


class VehicleBookingDepositSummaryReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.get_data()
		data = self.prepare_data()
		columns = self.get_columns()

		return columns, data

	def get_data(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select
				dep_m.name as deposit_doc, rec_m.name as receipt_doc,
				dep_m.posting_date as deposit_date, rec_m.posting_date as receipt_date,
				dep_i.amount, dep_i.instrument_no, dep_i.bank, dep_m.deposit_slip_no,
				rec_m.party_name as customer_name, dep_m.vehicle_booking_order,
				vbo.tax_id, vbo.tax_cnic, vbo.finance_type, vbo.item_code, i.item_name
			from `tabVehicle Booking Payment Detail` dep_i
			inner join `tabVehicle Booking Payment` dep_m on dep_m.name = dep_i.parent
			inner join `tabVehicle Booking Payment Detail` rec_i on rec_i.name = dep_i.vehicle_booking_payment_row
				and rec_i.parent = dep_i.vehicle_booking_payment
			inner join `tabVehicle Booking Payment` rec_m on rec_m.name = rec_i.parent
			inner join `tabVehicle Booking Order` vbo on vbo.name = dep_m.vehicle_booking_order
			inner join `tabItem` i on i.name = vbo.item_code
			where dep_m.docstatus = 1 {0}
		""".format(conditions), self.filters, as_dict=1)

		return self.data

	def prepare_data(self):
		for d in self.data:
			if d.finance_type == "Leased":
				d.tax_cnic_ntn = d.tax_id
			else:
				d.tax_cnic_ntn = d.tax_cnic or d.tax_id

		return self.data

	def get_conditions(self):
		conditions = []

		if self.filters.company:
			conditions.append("dep_m.company = %(company)s")

		if self.filters.from_date:
			conditions.append("dep_m.posting_date >= %(from_date)s")

		if self.filters.to_date:
			conditions.append("dep_m.posting_date <= %(to_date)s")

		if self.filters.supplier:
			conditions.append("dep_m.party_type = 'Supplier' and dep_m.party = %(party)s")

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		return [
			{"label": _("Deposit Document"), "fieldname": "deposit_doc", "fieldtype": "Link", "options": "Vehicle Booking Payment", "width": 90},
			{"label": _("Receipt Document"), "fieldname": "receipt_doc", "fieldtype": "Link", "options": "Vehicle Booking Payment", "width": 90},
			{"label": _("Receipt Date"), "fieldname": "receipt_date", "fieldtype": "Date", "width": 90},
			{"label": _("Deposit Date"), "fieldname": "deposit_date", "fieldtype": "Date", "width": 90},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
			{"label": _("Instrument #"), "fieldname": "instrument_no", "fieldtype": "Data", "width": 110},
			{"label": _("Bank"), "fieldname": "bank", "fieldtype": "Link", "options": "Bank", "width": 110},
			{"label": _("Deposit Slip"), "fieldname": "deposit_slip_no", "fieldtype": "Data", "width": 90},
			{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
			{"label": _("CNIC/NTN"), "fieldname": "tax_cnic_ntn", "fieldtype": "Data", "width": 100},
			{"label": _("Booking #"), "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order", "width": 100},
			{"label": _("Variant Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
			{"label": _("Variant Name"), "fieldname": "item_name", "fieldtype": "Link", "options": "Item", "width": 150},
		]


def execute(filters=None):
	return VehicleBookingDepositSummaryReport(filters).run()
