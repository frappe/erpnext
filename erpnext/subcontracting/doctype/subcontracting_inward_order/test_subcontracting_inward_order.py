# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as make_stock_entry_from_wo
from erpnext.selling.doctype.sales_order.sales_order import make_subcontracting_inward_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class IntegrationTestSubcontractingInwardOrder(IntegrationTestCase):
	"""
	Integration tests for SubcontractingInwardOrder.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		create_test_data()
		make_stock_entry(
			item_code="Self RM", qty=100, to_warehouse="Stores - _TC", purpose="Material Receipt"
		)
		return super().setUp()

	def test_customer_provided_item_cost_field(self):
		so, scio = create_so_scio()

		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		rm_in.save()
		for item in rm_in.get("items"):
			item.basic_rate = 10
		rm_in.append(
			"additional_costs",
			{
				"expense_account": "Freight and Forwarding Charges - _TC",
				"description": "Test",
				"amount": 100,
			},
		)
		rm_in.submit()

		for item in rm_in.get("items"):
			self.assertEqual(item.customer_provided_item_cost, 15)

	def test_add_extra_customer_provided_item(self):
		so, scio = create_so_scio()

		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		rm_in.save()
		rm_in.append(
			"items",
			{
				"item_code": "Basic RM 2",
				"qty": 5,
				"t_warehouse": rm_in.items[0].t_warehouse,
				"basic_rate": 10,
				"transfer_qty": 5,
				"uom": "Nos",
				"conversion_factor": 1,
				"against_fg": scio.items[0].name,
			},
		)
		rm_in.submit()

		scio.reload()
		self.assertTrue(
			next((item for item in scio.received_items if item.rm_item_code == "Basic RM 2"), None)
		)

	def test_add_extra_item_during_manufacture(self):
		make_stock_entry(
			item_code="Self RM 2", qty=5, to_warehouse="Stores - _TC", purpose="Material Receipt"
		)
		so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()

		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		next(
			item for item in wo.required_items if item.item_code == "Self RM"
		).source_warehouse = "Stores - _TC"
		wo.submit()

		manufacture = frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture"))
		manufacture.save()
		frappe.new_doc(
			"Stock Entry Detail",
			parent=manufacture.name,
			parenttype="Stock Entry",
			parentfield="items",
			idx=6,
			item_code="Self RM 2",
			qty=5,
			s_warehouse="Stores - _TC",
			basic_rate=10,
			transfer_qty=5,
			uom="Nos",
			conversion_factor=1,
			cost_center="Main - _TC",
		).insert()
		manufacture.reload()
		manufacture.submit()
		scio.reload()
		self.assertTrue(
			next((item for item in scio.received_items if item.rm_item_code == "Self RM 2"), None)
		)

	def test_work_order_creation_qty(self):
		new_bom = frappe.copy_doc(frappe.get_doc("BOM", "BOM-Basic FG Item-001"))
		new_bom.items = new_bom.items[:3]
		new_bom.items[1].qty = 2
		new_bom.items[2].qty = 3
		new_bom.submit()
		sc_bom = frappe.get_doc("Subcontracting BOM", "SB-0001")
		sc_bom.finished_good_bom = new_bom.name
		sc_bom.save()

		so, scio = create_so_scio()

		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		rm_in.items[0].qty = 3
		rm_in.items[1].qty = 5
		rm_in.items[2].qty = 12
		rm_in.submit()

		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		self.assertEqual(wo.qty, 2)

	def test_rm_return(self):
		from erpnext.stock.serial_batch_bundle import get_batch_nos, get_serial_nos

		so, scio = create_so_scio()

		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		rm_in.items[3].qty = 2
		rm_in.submit()

		serial_nos = get_serial_nos(rm_in.items[3].serial_and_batch_bundle)
		batch_nos = list(get_batch_nos(rm_in.items[3].serial_and_batch_bundle).keys())

		scio.reload()
		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		backup = rm_in.items[-1]
		rm_in.items.clear()
		rm_in.items.append(backup)

		rm_in.items[0].qty = 1
		rm_in.submit()

		serial_nos += get_serial_nos(rm_in.items[0].serial_and_batch_bundle)
		batch_nos += list(get_batch_nos(rm_in.items[0].serial_and_batch_bundle).keys())

		scio.reload()
		rm_return = frappe.new_doc("Stock Entry").update(scio.make_rm_return())
		rm_return.submit()

		self.assertEqual(
			sorted(get_serial_nos(rm_return.items[-1].serial_and_batch_bundle)), sorted(serial_nos)
		)
		self.assertEqual(
			sorted(list(get_batch_nos(rm_return.items[-1].serial_and_batch_bundle).keys())), sorted(batch_nos)
		)

	def test_subcontracting_delivery(self):
		from erpnext.stock.serial_batch_bundle import get_serial_batch_list_from_item

		extra_serial, _ = get_serial_batch_list_from_item(
			make_stock_entry(
				item_code="FG Item with Serial",
				qty=1,
				to_warehouse="Stores - _TC",
				purpose="Material Receipt",
			).items[0]
		)
		so, scio = create_so_scio(service_item="Service Item 2", fg_item="FG Item with Serial")
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()

		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.submit()

		manufacture = frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture"))
		manufacture.submit()

		serial_list, _ = get_serial_batch_list_from_item(
			next(item for item in manufacture.items if item.is_finished_item)
		)

		scio.reload()
		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		delivery.items[0].use_serial_batch_fields = 1
		delivery.save()
		delivery_serial_list, _ = get_serial_batch_list_from_item(delivery.items[0])
		self.assertEqual(sorted(serial_list), sorted(delivery_serial_list))

		delivery_serial_list[-1] = extra_serial[0]
		delivery.items[0].serial_no = "\n".join(delivery_serial_list)
		self.assertRaises(frappe.ValidationError, delivery.submit)

	def test_fg_item_fields(self):
		so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()

		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.submit()

		manufacture = frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture"))
		manufacture.save()
		manufacture.fg_completed_qty = 5
		manufacture.process_loss_qty = 1
		manufacture.items[-1].qty = 4
		manufacture.submit()

		scio.reload()
		self.assertEqual(scio.items[0].qty, 5)
		self.assertEqual(scio.items[0].process_loss_qty, 1)
		self.assertEqual(scio.items[0].produced_qty, 4)
		rm_in = scio.make_rm_stock_entry_inward()
		for item in rm_in.get("items"):
			self.assertEqual(item.qty, 1)

		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		delivery.items[0].qty = 5
		self.assertRaises(frappe.ValidationError, delivery.submit)
		delivery.items[0].qty = 2
		delivery.submit()

		scio.reload()
		fg_return = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_return())
		self.assertEqual(fg_return.items[0].qty, 2)
		fg_return.items[0].qty = 1
		fg_return.items[0].t_warehouse = "Stores - _TC"
		fg_return.submit()

		scio.reload()
		self.assertEqual(scio.items[0].delivered_qty, 2)
		self.assertEqual(scio.items[0].returned_qty, 1)

	@IntegrationTestCase.change_settings("Selling Settings", {"allow_delivery_of_overproduced_qty": 1})
	@IntegrationTestCase.change_settings(
		"Manufacturing Settings", {"overproduction_percentage_for_work_order": 20}
	)
	def test_over_production_delivery(self):
		so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()

		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.submit()

		manufacture = frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture"))
		manufacture.items[-1].qty = 6
		manufacture.fg_completed_qty = 6
		manufacture.submit()

		scio.reload()
		self.assertEqual(scio.items[0].produced_qty, 6)

		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		self.assertEqual(delivery.items[0].qty, 6)
		delivery.submit()

		frappe.db.set_single_value("Selling Settings", "allow_delivery_of_overproduced_qty", 0)
		delivery.cancel()
		scio.reload()
		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		self.assertEqual(delivery.items[0].qty, 5)
		delivery.items[0].qty = 6
		self.assertRaises(frappe.ValidationError, delivery.submit)

	@IntegrationTestCase.change_settings("Selling Settings", {"deliver_scrap_items": 1})
	def test_scrap_delivery(self):
		new_bom = frappe.copy_doc(frappe.get_doc("BOM", "BOM-Basic FG Item-001"))
		new_bom.scrap_items.append(frappe.new_doc("BOM Scrap Item", item_code="Basic RM 2", qty=1))
		new_bom.submit()
		sc_bom = frappe.get_doc("Subcontracting BOM", "SB-0001")
		sc_bom.finished_good_bom = new_bom.name
		sc_bom.save()

		so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()
		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.submit()

		frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture")).submit()

		scio.reload()
		self.assertEqual(scio.scrap_items[0].item_code, "Basic RM 2")

		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		self.assertEqual(delivery.items[-1].item_code, "Basic RM 2")

		frappe.db.set_single_value("Selling Settings", "deliver_scrap_items", 0)
		delivery = frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery())
		self.assertNotEqual(delivery.items[-1].item_code, "Basic RM 2")

	def test_self_rm_billed_qty(self):
		so, scio = create_so_scio()
		frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward()).submit()
		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.submit()
		frappe.new_doc("Stock Entry").update(make_stock_entry_from_wo(wo.name, "Manufacture")).submit()
		scio.reload()
		frappe.new_doc("Stock Entry").update(scio.make_subcontracting_delivery()).submit()
		scio.reload()

		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		si = make_sales_invoice(so.name)
		self.assertEqual(si.items[-1].item_code, "Self RM")
		self.assertEqual(si.items[-1].qty, 5)
		si.items[-1].qty = 3
		si.submit()
		scio.reload()
		self.assertEqual(scio.received_items[-1].billed_qty, 3)

		si = make_sales_invoice(so.name)
		self.assertEqual(si.items[-1].qty, 2)
		si.submit()
		scio.reload()
		self.assertEqual(scio.received_items[-1].billed_qty, 5)

		scio.reload()
		si = make_sales_invoice(so.name)
		self.assertEqual(len(si.items), 1)

	def test_extra_items_reservation_transfer(self):
		so, scio = create_so_scio()
		rm_in = frappe.new_doc("Stock Entry").update(scio.make_rm_stock_entry_inward())
		rm_in.items[-2].qty = 7
		rm_in.submit()

		wo_list = []
		scio.reload()
		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.qty = 3
		wo.submit()
		wo_list.append(wo.name)
		self.assertEqual(wo.required_items[-2].stock_reserved_qty, 3)

		scio.reload()
		self.assertEqual(scio.received_items[-2].work_order_qty, 3)

		wo = frappe.get_doc("Work Order", scio.make_work_order()[0])
		wo.skip_transfer = 1
		wo.required_items[-1].source_warehouse = "Stores - _TC"
		wo.qty = 2
		wo.submit()
		wo_list.append(wo.name)

		from frappe.query_builder.functions import Sum

		table = frappe.qb.DocType("Stock Reservation Entry")
		query = (
			frappe.qb.from_(table)
			.select(Sum(table.reserved_qty))
			.where(
				(table.voucher_type == "Work Order")
				& (table.item_code == rm_in.items[-2].item_code)
				& (table.voucher_no.isin(wo_list))
			)
		)
		reserved_qty = query.run()[0][0]
		self.assertEqual(reserved_qty, 7)


def create_so_scio(service_item="Service Item 1", fg_item="Basic FG Item"):
	item_list = [{"item_code": service_item, "qty": 5, "fg_item": fg_item, "fg_item_qty": 5}]
	so = make_sales_order(is_subcontracted=1, item_list=item_list)
	scio = make_subcontracting_inward_order(so.name)
	scio.items[0].delivery_warehouse = "_Test Warehouse - _TC"
	scio.submit()
	scio.reload()
	return so, scio


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
	customer_provided_raw_materials = {
		"Basic RM": {},
		"Basic RM 2": {},
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

	for item, properties in customer_provided_raw_materials.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1, "is_purchase_item": 0, "is_customer_provided_item": 1})
			make_item(item, properties)

	self_raw_materials = {
		"Self RM": {},
		"Self RM 2": {},
	}

	for item, properties in self_raw_materials.items():
		if not frappe.db.exists("Item", item):
			properties.update({"is_stock_item": 1, "valuation_rate": 10})
			make_item(item, properties)


def make_service_items():
	from erpnext.controllers.tests.test_subcontracting_controller import make_service_item

	service_items = {
		"Service Item 1": {},
		"Service Item 2": {},
		"Service Item 3": {},
		"Service Item 4": {},
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
			"Self RM",
		],
		"FG Item with Serial": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
			"Self RM",
		],
		"FG Item with Batch": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
			"Self RM",
		],
		"FG Item with Serial and Batch": [
			"Basic RM",
			"RM with Serial",
			"RM with Batch",
			"RM with Serial and Batch",
			"Self RM",
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
