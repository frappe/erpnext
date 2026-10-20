# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random

import frappe

from erpnext.manufacturing.doctype.routing.test_routing import create_routing
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestBOMCreator(ERPNextTestSuite):
	def setUp(self) -> None:
		create_items()

	def test_bom_sub_assembly(self):
		final_product = "Bicycle"
		make_item(
			final_product,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)

		doc = make_bom_creator(
			name="Bicycle BOM with Sub Assembly",
			company="_Test Company",
			item_code=final_product,
			qty=1,
			rm_cosy_as_per="Valuation Rate",
			currency="INR",
			plc_conversion_rate=1,
			conversion_rate=1,
		)

		doc.add_sub_assembly(
			fg_item=final_product,
			fg_reference_id=doc.name,
			bom_item={
				"item_code": "Frame Assembly",
				"qty": 1,
				"items": [
					{
						"item_code": "Frame",
						"qty": 1,
					},
					{
						"item_code": "Fork",
						"qty": 1,
					},
				],
			},
		)

		doc.reload()
		self.assertEqual(doc.items[0].item_code, "Frame Assembly")

		fg_valuation_rate = 0
		for row in doc.items:
			if row.fg_item == final_product:
				fg_valuation_rate += row.amount

			if not row.is_expandable:
				self.assertEqual(row.fg_item, "Frame Assembly")
				self.assertEqual(row.fg_reference_id, doc.items[0].name)

		self.assertEqual(doc.items[0].amount, fg_valuation_rate)

	def test_bom_raw_material(self):
		final_product = "Bicycle"
		make_item(
			final_product,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)

		doc = make_bom_creator(
			name="Bicycle BOM with Raw Material",
			company="_Test Company",
			item_code=final_product,
			qty=1,
			rm_cosy_as_per="Valuation Rate",
			currency="INR",
			plc_conversion_rate=1,
			conversion_rate=1,
		)

		doc.add_item(
			fg_item=final_product,
			fg_reference_id=doc.name,
			item_code="Pedal Assembly",
			qty=2,
		)

		doc.reload()
		self.assertEqual(doc.items[0].item_code, "Pedal Assembly")
		self.assertEqual(doc.items[0].qty, 2)

		fg_valuation_rate = 0
		for row in doc.items:
			if row.fg_item == final_product:
				fg_valuation_rate += row.amount

			if not row.is_expandable:
				self.assertEqual(row.fg_item, "Bicycle")
				self.assertEqual(row.fg_reference_id, doc.name)

		self.assertEqual(doc.raw_material_cost, fg_valuation_rate)

	def test_convert_to_sub_assembly(self):
		final_product = "Bicycle"
		make_item(
			final_product,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)

		doc = make_bom_creator(
			name="Bicycle BOM",
			company="_Test Company",
			item_code=final_product,
			qty=1,
			rm_cosy_as_per="Valuation Rate",
			currency="INR",
			plc_conversion_rate=1,
			conversion_rate=1,
		)

		doc.add_item(
			fg_item=final_product,
			fg_reference_id=doc.name,
			item_code="Pedal Assembly",
			qty=2,
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 0)

		doc.add_sub_assembly(
			convert_to_sub_assembly=1,
			fg_item=final_product,
			fg_reference_id=doc.items[0].name,
			bom_item={
				"item_code": "Pedal Assembly",
				"qty": 2,
				"items": [
					{
						"item_code": "Pedal Body",
						"qty": 2,
					},
					{
						"item_code": "Pedal Axle",
						"qty": 2,
					},
				],
			},
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 1)

		fg_valuation_rate = 0
		for row in doc.items:
			if row.fg_item == final_product:
				fg_valuation_rate += row.amount

			if not row.is_expandable:
				self.assertEqual(row.fg_item, "Pedal Assembly")
				self.assertEqual(row.qty, 2.0)
				self.assertEqual(row.fg_reference_id, doc.items[0].name)

		self.assertEqual(doc.raw_material_cost, fg_valuation_rate)

	def test_make_boms_from_bom_creator(self):
		final_product = "Bicycle Test"
		make_item(
			final_product,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)

		doc = make_bom_creator(
			name="Bicycle BOM Test",
			company="_Test Company",
			item_code=final_product,
			qty=1,
			rm_cosy_as_per="Valuation Rate",
			currency="INR",
			plc_conversion_rate=1,
			conversion_rate=1,
		)

		doc.add_item(
			fg_item=final_product,
			fg_reference_id=doc.name,
			item_code="Pedal Assembly",
			qty=2,
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 0)

		doc.add_sub_assembly(
			convert_to_sub_assembly=1,
			fg_item=final_product,
			fg_reference_id=doc.items[0].name,
			bom_item={
				"item_code": "Pedal Assembly",
				"qty": 2,
				"items": [
					{
						"item_code": "Pedal Body",
						"qty": 2,
					},
					{
						"item_code": "Pedal Axle",
						"qty": 2,
					},
				],
			},
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 1)

		doc.submit()
		doc.create_boms()
		doc.reload()

		data = frappe.get_all("BOM", filters={"bom_creator": doc.name, "docstatus": 1})
		self.assertEqual(len(data), 2)

		doc.create_boms()
		data = frappe.get_all("BOM", filters={"bom_creator": doc.name, "docstatus": 1})
		self.assertEqual(len(data), 2)

	def test_repeated_sub_assembly_keeps_own_raw_materials(self):
		doc, first_wheel, second_wheel = make_repeated_sub_assembly_bom(
			"Bicycle BOM with Repeated Sub Assembly"
		)

		self.assertEqual(child_items(doc, doc.name), ["Frame Assembly", "Seat Assembly"])
		self.assertEqual(child_items(doc, first_wheel), ["Rim", "Spokes"])
		self.assertEqual(child_items(doc, second_wheel), ["Hub"])

	def test_delete_repeated_sub_assembly_keeps_sibling_raw_materials(self):
		doc, first_wheel, second_wheel = make_repeated_sub_assembly_bom(
			"Bicycle BOM with Deleted Sub Assembly"
		)

		doc.delete_node(doctype="BOM Creator Item", docname=second_wheel)
		doc.reload()

		self.assertEqual(child_items(doc, first_wheel), ["Rim", "Spokes"])
		self.assertFalse([row for row in doc.items if row.item_code == "Hub"])

	def test_parent_row_edit_moves_a_material_between_repeated_sub_assemblies(self):
		doc, first_wheel, second_wheel = make_repeated_sub_assembly_bom("Bicycle BOM with Moved Material")
		first_wheel_idx = next(row.idx for row in doc.items if row.name == first_wheel)
		hub = next(row for row in doc.items if row.item_code == "Hub")

		hub.parent_row_no = str(first_wheel_idx)
		doc.save()
		doc.reload()

		self.assertEqual(child_items(doc, first_wheel), ["Hub", "Rim", "Spokes"])
		self.assertEqual(child_items(doc, second_wheel), [])

	def test_edit_and_delete_reject_unknown_item(self):
		final_product = "Bicycle"
		make_item(
			final_product,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)

		doc = make_bom_creator(
			name="Bicycle BOM Guarded",
			company="_Test Company",
			item_code=final_product,
			qty=1,
			rm_cosy_as_per="Valuation Rate",
			currency="INR",
			plc_conversion_rate=1,
			conversion_rate=1,
		)

		# Editing a row that does not belong to this BOM Creator must be rejected.
		self.assertRaises(
			frappe.ValidationError,
			doc.edit_bom_creator,
			docname="non-existent-row",
			data={"qty": 5},
		)

		# Deleting a row that does not belong to this BOM Creator must be rejected.
		self.assertRaises(
			frappe.ValidationError,
			doc.delete_node,
			fg_item=final_product,
			docname="non-existent-row",
		)

	def make_creator_with_item(self, operation=None, **kwargs):
		doc = make_bom_creator(
			name="Routing Check BOM Creator",
			company="_Test Company",
			item_code="_Test Item",
			qty=1,
			currency="INR",
			conversion_rate=1,
			plc_conversion_rate=1,
			**kwargs,
		)
		doc.add_item(
			fg_item="_Test Item",
			fg_reference_id=doc.name,
			item_code="_Test Item Home Desktop 100",
			qty=1,
			operation=operation,
		)
		return doc

	def test_submit_rejects_item_operation_without_routing(self):
		doc = self.make_creator_with_item(operation="_Test Operation 1")
		self.assertRaisesRegex(frappe.ValidationError, "Set a Routing", doc.submit)

	def test_submit_allows_item_operation_with_routing(self):
		routing = create_routing(
			routing_name="BOM Creator Routing",
			operations=[
				{"operation": "_Test Operation 1", "workstation": "_Test Workstation 1", "time_in_mins": 10}
			],
		)
		doc = self.make_creator_with_item(operation="_Test Operation 1", routing=routing.name)
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_submit_allows_items_without_operation(self):
		doc = self.make_creator_with_item()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_repeated_sub_assembly_is_costed_with_its_own_raw_materials(self):
		doc, first_wheel, second_wheel = make_repeated_sub_assembly_bom("Bicycle BOM with Repeated Costing")
		rows = {row.name: row for row in doc.items}
		rate = {row.item_code: row.rate for row in doc.items if not row.is_expandable}

		self.assertEqual(rows[first_wheel].amount, rate["Rim"] + rate["Spokes"])
		self.assertEqual(rows[second_wheel].amount, rate["Hub"])
		self.assertEqual(
			doc.raw_material_cost, rate["Frame"] + rate["Rim"] + rate["Spokes"] + rate["Seat"] + rate["Hub"]
		)

	def test_sub_assembly_reused_as_raw_material_is_not_expandable(self):
		make_item("Tricycle", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Tricycle BOM Reused Sub Assembly",
			company="_Test Company",
			item_code="Tricycle",
			qty=1,
			currency="INR",
			conversion_rate=1,
		)
		frame = add_test_sub_assembly(doc, "Tricycle", doc.name, "Frame Assembly", ["Frame"])
		seat = add_test_sub_assembly(doc, "Tricycle", doc.name, "Seat Assembly", ["Seat"])
		doc.add_item(fg_item="Seat Assembly", fg_reference_id=seat, item_code="Frame Assembly", qty=1)
		doc.reload()

		reused = next(row for row in doc.items if row.item_code == "Frame Assembly" and row.name != frame)
		self.assertEqual(reused.is_expandable, 0)

		doc.submit()
		doc.create_boms()
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "status"), "Completed")

	def test_sub_assembly_cycle_is_refused(self):
		make_item("Unicycle", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Unicycle BOM Cycle", company="_Test Company", item_code="Unicycle", qty=1, currency="INR"
		)
		frame = add_test_sub_assembly(doc, "Unicycle", doc.name, "Frame Assembly", ["Frame"])

		self.assertRaisesRegex(
			frappe.ValidationError,
			"inside its own sub-assembly",
			add_test_sub_assembly,
			doc,
			"Frame Assembly",
			frame,
			"Wheel Assembly",
			["Frame Assembly"],
		)

	def test_deleting_a_grid_row_keeps_the_tree(self):
		make_item("Scooter", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Scooter BOM Grid Delete",
			company="_Test Company",
			item_code="Scooter",
			qty=1,
			currency="INR",
		)
		frame = add_test_sub_assembly(doc, "Scooter", doc.name, "Frame Assembly", ["Frame", "Fork"])
		seat = add_test_sub_assembly(doc, "Scooter", doc.name, "Seat Assembly", ["Seat"])

		doc.items = [row for row in doc.items if row.item_code != "Frame"]
		for idx, row in enumerate(doc.items, start=1):
			row.idx = idx
		doc.save()
		doc.reload()

		self.assertEqual(child_items(doc, frame), ["Fork"])
		self.assertEqual(child_items(doc, seat), ["Seat"])

		doc.submit()
		doc.create_boms()
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "status"), "Completed")

	def test_boms_are_created_from_the_saved_creator(self):
		import json
		from unittest.mock import patch

		from frappe.handler import run_doc_method

		make_item("Kick Scooter", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Kick Scooter BOM Saved",
			company="_Test Company",
			item_code="Kick Scooter",
			qty=1,
			currency="INR",
		)
		doc.add_item(fg_item="Kick Scooter", fg_reference_id=doc.name, item_code="Frame", qty=1)
		doc.reload()
		doc.submit()

		posted = doc.as_dict()
		posted["qty"] = 7
		posted["items"][0]["qty"] = 50
		frappe.local.request = frappe._dict(method="POST")
		self.addCleanup(delattr, frappe.local, "request")

		with patch.object(frappe, "enqueue_doc") as enqueue_doc:
			frappe.local.response = frappe._dict(docs=[])
			run_doc_method("enqueue_create_boms", docs=json.dumps(posted, default=str))

		self.assertEqual(enqueue_doc.call_args.args, ("BOM Creator", doc.name, "create_boms"))

	def test_raw_material_keeps_its_own_bom(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		make_item("Balance Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		semi_bom = make_bom(item="Pedal Assembly", raw_materials=["Pedal Body"], currency="INR")
		doc = make_bom_creator(
			name="Balance Bike BOM Semi",
			company="_Test Company",
			item_code="Balance Bike",
			qty=1,
			currency="INR",
		)
		doc.add_item(fg_item="Balance Bike", fg_reference_id=doc.name, item_code="Pedal Assembly", qty=1)
		doc.reload()
		doc.items[0].do_not_explode = 0
		doc.items[0].bom_no = semi_bom.name
		doc.save()
		doc.submit()
		doc.create_boms()

		top_bom = frappe.db.get_value(
			"BOM", {"bom_creator": doc.name, "item": "Balance Bike", "docstatus": 1}
		)
		row = frappe.db.get_value(
			"BOM Item",
			{"parent": top_bom, "item_code": "Pedal Assembly"},
			["bom_no", "do_not_explode"],
			as_dict=True,
		)
		self.assertEqual((row.bom_no, row.do_not_explode), (semi_bom.name, 0))

	def test_rates_are_converted_to_the_creator_currency(self):
		make_item("Cargo Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		make_item("_Test BOM Creator USD RM", {"item_group": "Raw Material", "valuation_rate": 800})
		doc = make_bom_creator(
			name="Cargo Bike BOM USD",
			company="_Test Company",
			item_code="Cargo Bike",
			qty=1,
			currency="USD",
			conversion_rate=80,
			rm_cost_as_per="Valuation Rate",
		)
		doc.add_item(
			fg_item="Cargo Bike", fg_reference_id=doc.name, item_code="_Test BOM Creator USD RM", qty=1
		)
		doc.reload()

		self.assertEqual(doc.items[0].rate, 10)
		self.assertEqual(doc.raw_material_cost, 10)

	def test_recreated_bom_keeps_its_own_sub_assembly(self):
		doc, _first_wheel, second_wheel = make_repeated_sub_assembly_bom("Bicycle BOM Recreated Children")
		doc.submit()
		doc.create_boms()

		top_bom = frappe.get_doc("BOM", {"bom_creator": doc.name, "item": "Bicycle", "docstatus": 1})
		seat_bom = frappe.get_doc("BOM", {"bom_creator": doc.name, "item": "Seat Assembly", "docstatus": 1})
		second_wheel_bom = frappe.db.get_value(
			"BOM", {"bom_creator": doc.name, "bom_creator_item": second_wheel, "docstatus": 1}
		)
		top_bom.cancel()
		seat_bom.cancel()

		doc.reload()
		doc.create_boms()
		new_seat_bom = frappe.get_doc(
			"BOM", {"bom_creator": doc.name, "item": "Seat Assembly", "docstatus": 1}
		)
		self.assertEqual(
			[row.bom_no for row in new_seat_bom.items if row.item_code == "Wheel Assembly"],
			[second_wheel_bom],
		)

	def test_currency_change_refreshes_the_exchange_rate(self):
		if not frappe.db.exists("Currency", "TSR"):
			frappe.get_doc({"doctype": "Currency", "currency_name": "TSR", "enabled": 1}).insert()
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": frappe.utils.today(),
				"from_currency": "TSR",
				"to_currency": "INR",
				"exchange_rate": 50,
				"for_buying": 1,
				"for_selling": 1,
			}
		).insert()

		make_item("Cargo Bike Currency", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Cargo Bike BOM Currency Change",
			company="_Test Company",
			item_code="Cargo Bike Currency",
			qty=1,
			currency="USD",
			conversion_rate=80,
		)
		doc.currency = "TSR"
		doc.save()
		self.assertEqual(doc.conversion_rate, 50)

	def test_get_children_follows_user_permissions(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user
		from frappe.permissions import add_user_permission

		from erpnext.manufacturing.doctype.bom_creator.bom_creator import get_children

		for item in ("Allowed Bike", "Restricted Bike"):
			make_item(item, {"item_group": "Raw Material", "stock_uom": "Nos"})

		make_bom_creator(
			name="Allowed Bike BOM", company="_Test Company", item_code="Allowed Bike", qty=1, currency="INR"
		)
		restricted = make_bom_creator(
			name="Restricted Bike BOM",
			company="_Test Company",
			item_code="Restricted Bike",
			qty=1,
			currency="INR",
		)
		restricted.add_item(
			fg_item="Restricted Bike", fg_reference_id=restricted.name, item_code="Frame", qty=3
		)

		user = create_user("bom-creator-restricted@example.com", "Manufacturing User")
		add_user_permission("Item", "Allowed Bike", user.name)

		with self.set_user(user.name):
			self.assertRaises(
				frappe.PermissionError, get_children, parent=restricted.name, parent_id=restricted.name
			)

	def test_delete_node_saves_the_cost_without_the_deleted_rows(self):
		make_item("Tandem Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Tandem Bike BOM Delete",
			company="_Test Company",
			item_code="Tandem Bike",
			qty=1,
			currency="INR",
		)
		frame = add_test_sub_assembly(doc, "Tandem Bike", doc.name, "Frame Assembly", ["Frame", "Fork"])
		doc.add_item(fg_item="Tandem Bike", fg_reference_id=doc.name, item_code="Seat", qty=1)
		doc.reload()

		result = doc.delete_node(doctype="BOM Creator Item", docname=frame)
		seat = next(row for row in doc.items if row.item_code == "Seat")

		self.assertEqual([row.item_code for row in result.items], ["Seat"])
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "raw_material_cost"), seat.amount)

	def test_rate_is_taken_from_the_default_warehouse(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_item("Fat Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		rm_item = make_item("_Test BOM Creator Warehouse RM", {"is_stock_item": 1}).name
		make_stock_entry(item_code=rm_item, target="Stores - _TC", qty=10, basic_rate=100)
		make_stock_entry(item_code=rm_item, target="Finished Goods - _TC", qty=10, basic_rate=300)

		doc = make_bom_creator(
			name="Fat Bike BOM Warehouse",
			company="_Test Company",
			item_code="Fat Bike",
			qty=1,
			currency="INR",
			rm_cost_as_per="Valuation Rate",
			set_rate_based_on_warehouse=1,
			default_warehouse="Stores - _TC",
		)
		doc.add_item(fg_item="Fat Bike", fg_reference_id=doc.name, item_code=rm_item, qty=1)
		doc.reload()

		self.assertEqual(doc.items[0].rate, 100)

	def test_cancelling_the_top_bom_reopens_the_creator(self):
		make_item("Gravel Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Gravel Bike BOM Status",
			company="_Test Company",
			item_code="Gravel Bike",
			qty=1,
			currency="INR",
		)
		doc.add_item(fg_item="Gravel Bike", fg_reference_id=doc.name, item_code="Frame", qty=1)
		doc.reload()
		doc.submit()
		doc.create_boms()
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "status"), "Completed")

		top_bom = frappe.get_doc("BOM", {"bom_creator": doc.name, "item": "Gravel Bike", "docstatus": 1})
		top_bom.cancel()
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "status"), "Submitted")

	def test_successful_run_clears_the_error_log(self):
		make_item("Road Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		doc = make_bom_creator(
			name="Road Bike BOM Error Log",
			company="_Test Company",
			item_code="Road Bike",
			qty=1,
			currency="INR",
		)
		doc.add_item(fg_item="Road Bike", fg_reference_id=doc.name, item_code="Frame", qty=1)
		doc.reload()
		doc.submit()
		doc.db_set({"status": "Failed", "error_log": "Disabled Item Frame cannot be used in BOMs"})

		doc.reload()
		doc.create_boms()
		self.assertEqual(
			frappe.db.get_value("BOM Creator", doc.name, ["status", "error_log"]), ("Completed", None)
		)
		self.assertTrue(frappe.get_meta("BOM Creator").get_field("error_log").no_copy)

	def test_edit_root_qty_and_row_uom(self):
		make_item("Touring Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})
		rm_item = make_item(
			"_Test BOM Creator Box RM",
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
				"valuation_rate": 10,
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			},
		).name
		doc = make_bom_creator(
			name="Touring Bike BOM Edit",
			company="_Test Company",
			item_code="Touring Bike",
			qty=1,
			currency="INR",
		)
		doc.edit_bom_creator(docname=doc.name, data={"qty": 5})
		self.assertEqual(frappe.db.get_value("BOM Creator", doc.name, "qty"), 5)

		doc.add_item(fg_item="Touring Bike", fg_reference_id=doc.name, item_code=rm_item, qty=3)
		doc.reload()
		self.assertEqual(doc.items[0].stock_qty, 3)

		doc.edit_bom_creator(docname=doc.items[0].name, data={"uom": "Box"})
		doc.reload()
		row = doc.items[0]
		self.assertEqual((row.conversion_factor, row.stock_qty, row.amount), (12, 36, 360))

	def test_tree_is_validated_on_insert(self):
		make_item("City Bike", {"item_group": "Raw Material", "stock_uom": "Nos"})

		def new_creator(name, items):
			return frappe.get_doc(
				{
					"doctype": "BOM Creator",
					"name": name,
					"company": "_Test Company",
					"item_code": "City Bike",
					"qty": 1,
					"currency": "INR",
					"items": items,
				}
			)

		duplicate = new_creator(
			"City Bike BOM Duplicate",
			[
				{"item_code": "Frame", "fg_item": "City Bike", "qty": 1},
				{"item_code": "Frame", "fg_item": "City Bike", "qty": 1},
			],
		)
		self.assertRaisesRegex(frappe.ValidationError, "added multiple times", duplicate.insert)

		wrong_parent = new_creator(
			"City Bike BOM Wrong Parent",
			[
				{"item_code": "Frame Assembly", "fg_item": "City Bike", "qty": 1},
				{"item_code": "Fork", "fg_item": "City Bike", "qty": 1},
				{"item_code": "Frame", "fg_item": "Frame Assembly", "parent_row_no": "2", "qty": 1},
			],
		)
		self.assertRaisesRegex(frappe.ValidationError, "points to item", wrong_parent.insert)


def create_items():
	raw_materials = [
		"Frame",
		"Fork",
		"Rim",
		"Spokes",
		"Hub",
		"Tube",
		"Tire",
		"Pedal Body",
		"Pedal Axle",
		"Ball Bearings",
		"Chain Links",
		"Chain Pins",
		"Seat",
		"Seat Post",
		"Seat Clamp",
	]

	for item in raw_materials:
		valuation_rate = random.choice([100, 200, 300, 500, 333, 222, 44, 20, 10])
		make_item(
			item,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
				"valuation_rate": valuation_rate,
			},
		)

	sub_assemblies = [
		"Frame Assembly",
		"Wheel Assembly",
		"Pedal Assembly",
		"Chain Assembly",
		"Seat Assembly",
	]

	for item in sub_assemblies:
		make_item(
			item,
			{
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			},
		)


def make_repeated_sub_assembly_bom(name):
	"""Bicycle > (Frame Assembly > Wheel Assembly > Rim, Spokes), (Seat Assembly > Wheel Assembly > Hub)"""
	final_product = "Bicycle"
	make_item(final_product, {"item_group": "Raw Material", "stock_uom": "Nos"})

	doc = make_bom_creator(
		name=name,
		company="_Test Company",
		item_code=final_product,
		qty=1,
		rm_cosy_as_per="Valuation Rate",
		currency="INR",
		plc_conversion_rate=1,
		conversion_rate=1,
	)

	def add_sub_assembly(fg_item, fg_reference_id, item_code, raw_materials):
		doc.add_sub_assembly(
			fg_item=fg_item,
			fg_reference_id=fg_reference_id,
			bom_item={
				"item_code": item_code,
				"qty": 1,
				"items": [{"item_code": item, "qty": 1} for item in raw_materials],
			},
		)
		doc.reload()

		return next(
			row.name
			for row in doc.items
			if row.item_code == item_code and row.fg_reference_id == fg_reference_id
		)

	frame = add_sub_assembly(final_product, doc.name, "Frame Assembly", ["Frame"])
	first_wheel = add_sub_assembly("Frame Assembly", frame, "Wheel Assembly", ["Rim", "Spokes"])

	seat = add_sub_assembly(final_product, doc.name, "Seat Assembly", ["Seat"])
	second_wheel = add_sub_assembly("Seat Assembly", seat, "Wheel Assembly", ["Hub"])

	return doc, first_wheel, second_wheel


def child_items(doc, parent):
	from erpnext.manufacturing.doctype.bom_creator.bom_creator import get_children

	return sorted(row.item_code for row in get_children(parent=parent, parent_id=doc.name))


def make_bom_creator(**kwargs):
	if isinstance(kwargs, str) or isinstance(kwargs, dict):
		kwargs = frappe.parse_json(kwargs)

	doc = frappe.new_doc("BOM Creator")
	doc.update(kwargs)
	doc.save()

	return doc


def add_test_sub_assembly(doc, fg_item, fg_reference_id, item_code, raw_materials):
	doc.add_sub_assembly(
		fg_item=fg_item,
		fg_reference_id=fg_reference_id,
		bom_item={
			"item_code": item_code,
			"qty": 1,
			"items": [{"item_code": item, "qty": 1} for item in raw_materials],
		},
	)
	doc.reload()

	return next(
		row.name for row in doc.items if row.item_code == item_code and row.fg_reference_id == fg_reference_id
	)
