import frappe
from frappe.tests import IntegrationTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestSubcontractingInwardController(IntegrationTestCase):
	def setUp(self):
		create_test_data()


def create_test_data():
	make_subcontracted_items()
	make_raw_materials()
	make_service_items()
	make_bom_for_subcontracted_items()
	make_subcontracting_boms()
	create_warehouse("_Test Customer Warehouse - _TC", {"customer": "_Test Customer"})


def make_subcontracted_items():
	sub_contracted_items = {
		"Basic FG Item": {},
		"FG Item with Serial": {
			"has_serial_no": 1,
			"serial_no_series": "FGS.####",
		},
		"FG Item with Batch": {
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_series": "FGB.####",
		},
		"FG Item with Serial and Batch": {
			"has_serial_no": 1,
			"serial_no_series": "FGS.####",
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_series": "FGB.####",
		},
	}

	for item, properties in sub_contracted_items.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1, "is_sub_contracted_item": 1})
			make_item(item, properties)


def make_raw_materials():
	raw_materials = {
		"Basic RM": {},
		"RM with Serial": {"has_serial_no": 1, "serial_no_series": "RMS.####"},
		"RM with Batch": {
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "RMB.####",
		},
		"RM with Serial and Batch": {
			"has_serial_no": 1,
			"serial_no_series": "RMS.####",
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "RMB.####",
		},
	}

	for item, properties in raw_materials.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1, "is_purchase_item": 0, "is_customer_provided_item": 1})
			make_item(item, properties)


def make_service_items():
	from erpnext.controllers.tests.test_subcontracting_controller import make_service_item

	service_items = {
		"Service Item 1": {},
		"Service Item 2": {},
		"Service Item 3": {},
		"Service Item 4": {},
		"Service Item 5": {},  # No Subcontracting BOM
	}

	for item, properties in service_items.items():
		make_service_item(item, properties)


def make_bom_for_subcontracted_items():
	from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

	boms = {
		"Basic FG Item": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
		],
		"FG Item with Serial": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
		],
		"FG Item with Batch": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
		],
		"FG Item with Serial and Batch": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
		],
	}

	for item_code, raw_materials in boms.items():
		if not frappe.db.exists("BOM", {"item": item_code}):
			make_bom(
				item=item_code, raw_materials=raw_materials, rate=100, currency="INR", set_as_default_bom=1
			)


def make_subcontracting_boms():
	subcontracting_boms = [
		{
			"finished_good": "Basic FG Item",
			"service_item": "Service Item 1",
		},
		{
			"finished_good": "FG Item with Serial",
			"service_item": "Service Item 2",
		},
		{
			"finished_good": "FG Item with Batch",
			"service_item": "Service Item 3",
		},
		{
			"finished_good": "FG Item with Serial and Batch",
			"service_item": "Service Item 4",
		},
	]

	for subcontracting_bom in subcontracting_boms:
		if not frappe.db.exists("Subcontracting BOM", {"finished_good": subcontracting_bom["finished_good"]}):
			doc = frappe.get_doc(
				{
					"doctype": "Subcontracting BOM",
					"finished_good": subcontracting_bom["finished_good"],
					"service_item": subcontracting_bom["service_item"],
					"is_active": 1,
				}
			)
			doc.insert()
			doc.save()
