# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class AppointmentType(Document):
	def validate(self):
		if self.items and self.price_list:
			for item in self.items:
				existing_op_item_price = frappe.db.exists(
					"Item Price", {"item_code": item.op_consulting_charge_item, "price_list": self.price_list}
				)

				if not existing_op_item_price and item.op_consulting_charge_item and item.op_consulting_charge:
					make_item_price(self.price_list, item.op_consulting_charge_item, item.op_consulting_charge)

				existing_ip_item_price = frappe.db.exists(
					"Item Price", {"item_code": item.inpatient_visit_charge_item, "price_list": self.price_list}
				)

				if (
					not existing_ip_item_price
					and item.inpatient_visit_charge_item
					and item.inpatient_visit_charge
				):
					make_item_price(
						self.price_list, item.inpatient_visit_charge_item, item.inpatient_visit_charge
					)


@frappe.whitelist()
def get_service_item_based_on_department(appointment_type, department):
	item_list = frappe.db.get_value(
		"Appointment Type Service Item",
		filters={"medical_department": department, "parent": appointment_type},
		fieldname=[
			"op_consulting_charge_item",
			"inpatient_visit_charge_item",
			"op_consulting_charge",
			"inpatient_visit_charge",
		],
		as_dict=1,
	)

	# if department wise items are not set up
	# use the generic items
	if not item_list:
		item_list = frappe.db.get_value(
			"Appointment Type Service Item",
			filters={"parent": appointment_type},
			fieldname=[
				"op_consulting_charge_item",
				"inpatient_visit_charge_item",
				"op_consulting_charge",
				"inpatient_visit_charge",
			],
			as_dict=1,
		)

	return item_list


def make_item_price(price_list, item, item_price):
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": price_list,
			"item_code": item,
			"price_list_rate": item_price,
		}
	).insert(ignore_permissions=True, ignore_mandatory=True)
