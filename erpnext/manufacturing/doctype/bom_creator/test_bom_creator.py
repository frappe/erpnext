# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random

import frappe

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
