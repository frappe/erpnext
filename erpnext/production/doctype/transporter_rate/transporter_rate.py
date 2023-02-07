# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from frappe import _, qb, throw, bold

class TransporterRate(Document):
	def validate(self):
		self.validate_data()

	def validate_data(self):
		if self.from_date > self.to_date:
			throw("From Date cannot be greater than To Date",title="Invalid Date")
		
		dup = frappe._dict()
		tr = qb.DocType("Transporter Rate")
		tri = qb.DocType("Transporter Rate Item")
		tdr = qb.DocType("Transporter Distance Rate")
		for a in self.items:
			if flt(a.lower_rate) <= 0 or flt(a.higher_rate) <= 0:
				throw("Rate cannot be smaller than 0 for row {0}".format(frappe.bold(a.idx)))

			if cint(a.threshold_trip) <= 0:
				throw("Threshold Trip should be greater than 0 for row {0}".format(frappe.bold(a.idx)))

			# validation for duplicate entry for equipment type
			if a.equipment_category in dup:
				if a.item_code in dup.get(a.equipment_category):
					throw(_("Row#{}: Duplicate entry for item {} under Equipment Type {}")\
						.format(a.idx, frappe.bold(a.item_code), frappe.bold(a.equipment_category)))
				else:
					dup.setdefault(a.equipment_category, []).append(a.item_code)
			else:
				dup.setdefault(a.equipment_category, []).append(a.item_code)

			# check for duplicate rate
			for d in ( qb.from_(tr)
						.inner_join(tri)
						.on(tr.name == tri.parent)
						.select(tr.name)
						.where((tr.from_warehouse == self.from_warehouse ) 
							& (tr.receiving_warehouse == self.receiving_warehouse) 
							& ((tr.from_date[self.from_date:self.to_date]) |(tr.to_date[self.from_date:self.to_date]) | ((self.from_date <= tr.to_date) & (self.to_date >= tr.from_date))) 
							& (tr.name != self.name) 
							& ( tri.equipment_category == a.equipment_category)	
							& ( tri.item_code == a.item_code))
						).run(as_dict =True):
				throw(_("Rate already defined via {}").format(frappe.get_desk_link('Transporter Rate', d.name), title="Duplicate Entry"))
		
		if self.rate_base == "Location" and self.distance_rate:
			distance = []
			for a in self.distance_rate:
				if str(a.distance + a.location) in distance:
					throw("Distance {} cannot be repeated at row {}".format(bold(a.distance),bold(a.idx)),title="Duplicate Distance")
				else:
					distance.append(str(a.distance + a.location))
				# check duplicate in other transaction
				dup = (qb.from_(tr)
						.inner_join(tdr)
						.on(tr.name == tdr.parent)
						.select(tr.name)
						.where((tr.name != self.name)
							& (tr.from_warehouse == self.from_warehouse)
							& ((tr.from_date[self.from_date:self.to_date]) |(tr.to_date[self.from_date:self.to_date]) | ((self.from_date <= tr.to_date) & (self.to_date >= tr.from_date))) 
							& (tdr.location == a.location)
							& (tdr.distance == a.distance))
						.limit(1)
						).run()
				if dup:
					throw(_("Rate already defined via {}").format(frappe.get_desk_link('Transporter Rate', dup[0][0]), title="Duplicate Entry"))

@frappe.whitelist()
def get_transporter_rate(from_warehouse, receiving_warehouse, date, equipment_category, item_code):
	tr = qb.DocType("Transporter Rate")
	tri = qb.DocType("Transporter Rate Item")
	rate = (qb.from_(tr)
				.inner_join(tri)
				.on(tr.name == tri.parent )
				.select(tr.name, tri.threshold_trip, tri.lower_rate, tri.higher_rate, tri.unloading_rate, tr.expense_account)
				.where((tr.from_warehouse == from_warehouse) 
						&(tr.receiving_warehouse == receiving_warehouse) 
						&(tr.from_date <= date) 
						&(tr.to_date >= date)
						&(tri.item_code == item_code)
						&(tri.equipment_category == equipment_category))
				).run(as_dict=True)
		
	if not rate:
		frappe.throw(_("""No Transporter Rate defined between source warehouse {} and receiving warehouse {}
					for Equipment Type {} and  Material {} for the date {}""")\
				.format(frappe.bold(from_warehouse), frappe.bold(receiving_warehouse), 
					frappe.bold(equipment_category), frappe.bold(item_code), frappe.bold(date)),title="No Data Found")

	return rate[0]