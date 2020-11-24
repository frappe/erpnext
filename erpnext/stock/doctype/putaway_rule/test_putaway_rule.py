# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import add_days, nowdate
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

class TestPutawayRule(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Item", "_Rice"):
			make_item("_Rice", {
				'is_stock_item': 1,
				'has_batch_no' : 1,
				'create_new_batch': 1,
				'stock_uom': 'Kg'
			})

		if not frappe.db.exists("Warehouse", {"warehouse_name": "Rack 1"}):
			create_warehouse("Rack 1")
		if not frappe.db.exists("Warehouse", {"warehouse_name": "Rack 2"}):
			create_warehouse("Rack 2")

		if not frappe.db.exists("UOM", "Bag"):
			new_uom = frappe.new_doc("UOM")
			new_uom.uom_name = "Bag"
			new_uom.save()

	def test_putaway_rules_priority(self):
		"""Test if rule is applied by priority, irrespective of free space."""
		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=200,
			uom="Kg")
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=300,
			uom="Kg", priority=2)

		po = create_purchase_order(item_code="_Rice", qty=300)
		self.assertEqual(len(po.items), 1)

		pr = make_purchase_receipt(po.name)
		self.assertEqual(len(pr.items), 2)
		self.assertEqual(pr.items[0].qty, 200)
		self.assertEqual(pr.items[0].warehouse, warehouse_1)
		self.assertEqual(pr.items[1].qty, 100)
		self.assertEqual(pr.items[1].warehouse, warehouse_2)

		po.cancel()
		rule_1.delete()
		rule_2.delete()

	def test_putaway_rules_with_same_priority(self):
		"""Test if rule with more free space is applied,
		among two rules with same priority and capacity."""
		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=500,
			uom="Kg")
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=500,
			uom="Kg")

		# out of 500 kg capacity, occupy 100 kg in warehouse_1
		stock_receipt = make_stock_entry(item_code="_Rice", target=warehouse_1, qty=100, basic_rate=50)

		po = create_purchase_order(item_code="_Rice", qty=700)
		self.assertEqual(len(po.items), 1)

		pr = make_purchase_receipt(po.name)
		self.assertEqual(len(pr.items), 2)
		self.assertEqual(pr.items[0].qty, 500)
		# warehouse_2 has 500 kg free space, it is given priority
		self.assertEqual(pr.items[0].warehouse, warehouse_2)
		self.assertEqual(pr.items[1].qty, 200)
		# warehouse_1 has 400 kg free space, it is given less priority
		self.assertEqual(pr.items[1].warehouse, warehouse_1)

		po.cancel()
		stock_receipt.cancel()
		rule_1.delete()
		rule_2.delete()

	def test_putaway_rules_with_insufficient_capacity(self):
		"""Test if qty exceeding capacity, is handled."""
		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=100,
			uom="Kg")
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=200,
			uom="Kg")

		po = create_purchase_order(item_code="_Rice", qty=350)
		self.assertEqual(len(po.items), 1)

		pr = make_purchase_receipt(po.name)

		self.assertEqual(len(pr.items), 3)
		self.assertEqual(pr.items[0].qty, 200)
		self.assertEqual(pr.items[0].warehouse, warehouse_2)
		self.assertEqual(pr.items[1].qty, 100)
		self.assertEqual(pr.items[1].warehouse, warehouse_1)
		# extra qty has no warehouse assigned
		self.assertEqual(pr.items[2].qty, 50)
		self.assertEqual(pr.items[2].warehouse, '')

		po.cancel()
		rule_1.delete()
		rule_2.delete()

	def test_putaway_rules_multi_uom(self):
		"""Test rules applied on uom other than stock uom."""
		item = frappe.get_doc("Item", "_Rice")
		if not frappe.db.get_value("UOM Conversion Detail", {"parent": "_Rice", "uom": "Bag"}):
			item.append("uoms", {
				"uom": "Bag",
				"conversion_factor": 1000
			})
			item.save()

		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=3,
			uom="Bag")
		self.assertEqual(rule_1.stock_capacity, 3000)
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=4,
			uom="Bag")
		self.assertEqual(rule_2.stock_capacity, 4000)

		stock_receipt = make_stock_entry(item_code="_Rice", target=warehouse_1, qty=1000, basic_rate=50)

		po = create_purchase_order(item_code="_Rice", qty=6, do_not_save=True)
		po.items[0].uom = "Bag"
		po.save()
		po.submit()

		self.assertEqual(po.items[0].stock_qty, 6000)

		pr = make_purchase_receipt(po.name)
		self.assertEqual(len(pr.items), 2)
		self.assertEqual(pr.items[0].qty, 4)
		self.assertEqual(pr.items[0].warehouse, warehouse_2)
		self.assertEqual(pr.items[1].qty, 2)
		self.assertEqual(pr.items[1].warehouse, warehouse_1)

		po.cancel()
		stock_receipt.cancel()
		rule_1.delete()
		rule_2.delete()

	def test_putaway_rules_multi_uom_whole_uom(self):
		"""Test if whole UOMs are handled."""
		item = frappe.get_doc("Item", "_Rice")
		if not frappe.db.get_value("UOM Conversion Detail", {"parent": "_Rice", "uom": "Bag"}):
			item.append("uoms", {
				"uom": "Bag",
				"conversion_factor": 1000
			})
			item.save()

		frappe.db.set_value("UOM", "Bag", "must_be_whole_number", 1)

		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		# Putaway Rule in different UOM
		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=1,
			uom="Bag")
		self.assertEqual(rule_1.stock_capacity, 1000)
		# Putaway Rule in Stock UOM
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=500)
		self.assertEqual(rule_2.stock_capacity, 500)
		# total capacity is 1500 Kg

		po = create_purchase_order(item_code="_Rice", qty=2, do_not_save=True)
		# PO for 2 Bags (2000 Kg)
		po.items[0].uom = "Bag"
		po.save()
		po.submit()

		self.assertEqual(po.items[0].stock_qty, 2000)

		pr = make_purchase_receipt(po.name)
		self.assertEqual(len(pr.items), 2)
		self.assertEqual(pr.items[0].qty, 1)
		self.assertEqual(pr.items[0].warehouse, warehouse_1)
		# leftover space was for 500 kg (0.5 Bag)
		# Since Bag is a whole UOM, 1(out of 2) Bag will be unassigned
		self.assertEqual(pr.items[1].qty, 1)
		self.assertEqual(pr.items[1].warehouse, '')

		po.cancel()
		rule_1.delete()
		rule_2.delete()

	def test_putaway_rules_with_reoccurring_item(self):
		"""Test rules on same item entered multiple times."""
		warehouse_1 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 1"})
		warehouse_2 = frappe.db.get_value("Warehouse", {"warehouse_name": "Rack 2"})

		rule_1 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_1, capacity=200,
			uom="Kg")
		rule_2 = create_putaway_rule(item_code="_Rice", warehouse=warehouse_2, capacity=100,
			uom="Kg", priority=2)
		# total capacity is 300 Kg

		po = create_purchase_order(item_code="_Rice", qty=200, rate=100, do_not_save=True)
		po.append("items", {
			"item_code":"_Rice",
			"warehouse": "_Test Warehouse - _TC",
			"qty": 300,
			"rate": 120,
			"schedule_date": add_days(nowdate(), 1),
		})
		po.save()
		po.submit()
		# PO for 500 Kg (two rows of same item, different rates)
		self.assertEqual(len(po.items), 2)

		pr = make_purchase_receipt(po.name)
		self.assertEqual(len(pr.items), 3)
		self.assertEqual(pr.items[0].qty, 200)
		self.assertEqual(pr.items[0].warehouse, warehouse_1)
		# same rules applied to second item row
		# with previous assignment considered
		self.assertEqual(pr.items[1].qty, 100)
		self.assertEqual(pr.items[1].warehouse, warehouse_2)
		# unassigned 200 Kg
		self.assertEqual(pr.items[2].qty, 200)
		self.assertEqual(pr.items[2].warehouse, '')

		po.cancel()
		rule_1.delete()
		rule_2.delete()

def create_putaway_rule(**args):
	args = frappe._dict(args)
	putaway = frappe.new_doc("Putaway Rule")

	putaway.disable = args.disable or 0
	putaway.company = args.company or "_Test Company"
	putaway.item_code = args.item or args.item_code or "_Test Item"
	putaway.warehouse = args.warehouse
	putaway.priority = args.priority or 1
	putaway.capacity = args.capacity or 1
	putaway.stock_uom = frappe.db.get_value("Item", putaway.item_code, "stock_uom")
	putaway.uom = args.uom or putaway.stock_uom
	putaway.conversion_factor = get_conversion_factor(putaway.item_code, putaway.uom)['conversion_factor']

	if not args.do_not_save:
		putaway.save()

	return putaway