# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import random

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.bom_creator.bom_creator import (
	add_item,
	add_sub_assembly,
)
from erpnext.stock.doctype.item.test_item import make_item


class TestBOMCreator(FrappeTestCase):
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

		add_sub_assembly(
			parent=doc.name,
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
			if not row.is_expandable:
				fg_valuation_rate += row.amount
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

		add_item(
			parent=doc.name,
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
			if not row.is_expandable:
				fg_valuation_rate += row.amount
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

		add_item(
			parent=doc.name,
			fg_item=final_product,
			fg_reference_id=doc.name,
			item_code="Pedal Assembly",
			qty=2,
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 0)

		add_sub_assembly(
			convert_to_sub_assembly=1,
			parent=doc.name,
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
			if not row.is_expandable:
				fg_valuation_rate += row.amount
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

		add_item(
			parent=doc.name,
			fg_item=final_product,
			fg_reference_id=doc.name,
			item_code="Pedal Assembly",
			qty=2,
		)

		doc.reload()
		self.assertEqual(doc.items[0].is_expandable, 0)

		add_sub_assembly(
			convert_to_sub_assembly=1,
			parent=doc.name,
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


def make_bom_creator(**kwargs):
	if isinstance(kwargs, str) or isinstance(kwargs, dict):
		kwargs = frappe.parse_json(kwargs)

	doc = frappe.new_doc("BOM Creator")
	doc.update(kwargs)
	doc.save()

	return doc
