# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, nowtime, flt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.utils import get_incoming_rate
from erpnext import set_perpetual_inventory
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation \
	import create_stock_reconciliation
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.stock_ledger import get_previous_sle, repost_future_sle
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import create_landed_cost_voucher
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

class TestStockLedgerEntry(unittest.TestCase):
	def setUp(self):
		items = create_items()

		# delete SLE and BINs for all items
		frappe.db.sql("delete from `tabStock Ledger Entry` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)
		frappe.db.sql("delete from `tabBin` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)

		set_perpetual_inventory(0, "_Test Company with perpetual inventory")

	def test_item_cost_reposting(self):
		company = "_Test Company with perpetual inventory"

		# _Test Item for Reposting at Stores warehouse on 10-04-2020: Qty = 50, Rate = 100
		reco1 = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - TCP1",
			qty=50,
			rate=100,
			company=company,
			expense_account = "Stock Adjustment - TCP1",
			posting_date='2020-04-10'
		)

		# _Test Item for Reposting at FG warehouse on 20-04-2020: Qty = 10, Rate = 200
		reco2 = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Finished Goods - TCP1",
			qty=10,
			rate=200,
			company=company,
			expense_account = "Stock Adjustment - TCP1",
			posting_date='2020-04-20'
		)

		# _Test Item for Reposting trasnferred from Stores to FG warehouse on 30-04-2020
		transfer1 = make_stock_entry(
			item_code="_Test Item for Reposting",
			source="Stores - TCP1",
			target="Finished Goods - TCP1",
			company=company,
			qty=10,
			expense_account="Stock Adjustment - TCP1",
			posting_date='2020-04-30'
		)
		target_wh_sle = get_previous_sle({
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - TCP1",
			"posting_date": '2020-04-30',
			"posting_time": nowtime()
		})

		self.assertEqual(target_wh_sle.get("valuation_rate"), 150)

		# Repack entry on 5-5-2020
		repack = create_repack_entry(company=company, posting_date='2020-05-05')

		finished_item_sle = get_previous_sle({
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - TCP1",
			"posting_date": '2020-05-05',
			"posting_time": nowtime()
		})
		self.assertEqual(finished_item_sle.get("incoming_rate"), 540)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 540)

		# Reconciliation for _Test Item for Reposting at Stores on 12-04-2020: Qty = 50, Rate = 150
		reco3 = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - TCP1",
			qty=50,
			rate=150,
			company=company,
			expense_account = "Stock Adjustment - TCP1",
			posting_date='2020-04-12'
		)

		repost_future_sle("Stock Reconciliation", reco3.name)

		# Check valuation rate of finished goods warehouse after back-dated entry at Stores
		target_wh_sle = get_previous_sle({
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - TCP1",
			"posting_date": '2020-04-30',
			"posting_time": nowtime()
		})
		self.assertEqual(target_wh_sle.get("incoming_rate"), 150)
		self.assertEqual(target_wh_sle.get("valuation_rate"), 175)

		# Check valuation rate of repacked item after back-dated entry at Stores
		finished_item_sle = get_previous_sle({
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - TCP1",
			"posting_date": '2020-05-05',
			"posting_time": nowtime()
		})
		self.assertEqual(finished_item_sle.get("incoming_rate"), 790)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 790)

		# Check updated rate in Repack entry
		repack.reload()
		self.assertEqual(repack.items[0].get("basic_rate"), 150)
		self.assertEqual(repack.items[1].get("basic_rate"), 750)

	def test_purchase_return_valuation_reposting(self):
		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", posting_date='2020-04-10',
			warehouse="Stores - TCP1", item_code="_Test Item for Reposting", qty=5, rate=100)

		return_pr = make_purchase_receipt(company="_Test Company with perpetual inventory", posting_date='2020-04-15', 
			warehouse="Stores - TCP1", item_code="_Test Item for Reposting", is_return=1, return_against=pr.name, qty=-2)

		# check sle
		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 100)
		self.assertEqual(stock_value_difference, -200)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)
		repost_future_sle("Purchase Receipt", pr.name)

		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 110)
		self.assertEqual(stock_value_difference, -220)

	def test_sales_return_valuation_reposting(self):
		company = "_Test Company with perpetual inventory"
		item_code="_Test Item for Reposting"

		# Purchase Return: Qty = 5, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - TCP1", item_code=item_code, qty=5, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=item_code, qty=5, rate=150, warehouse="Stores - TCP1",
			company=company, expense_account="Cost of Goods Sold - TCP1", cost_center="Main - TCP1")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5)

		self.assertEqual(dn.items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=item_code, qty=-2, rate=150,
			company=company, warehouse="Stores - TCP1", expense_account="Cost of Goods Sold - TCP1", cost_center="Main - TCP1")

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(return_dn.items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 200)

		#-------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# Repost future SLE for Purchase Receipt
		repost_future_sle("Purchase Receipt", pr.name)


		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5)
		self.assertEqual(outgoing_rate, 110)

		dn.reload()
		self.assertEqual(dn.items[0].incoming_rate, 110)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(incoming_rate, 110)
		self.assertEqual(stock_value_difference, 220)

		return_dn.reload()
		self.assertEqual(return_dn.items[0].incoming_rate, 110)

		# Cleanup data
		return_dn.cancel()
		dn.cancel()
		lcv.cancel()
		pr.cancel()

	def test_reposting_of_sales_return_for_packed_item(self):
		company = "_Test Company with perpetual inventory"
		packed_item_code="_Test Item for Reposting"
		bundled_item = "_Test Bundled Item for Reposting"
		create_product_bundle_item(bundled_item, [[packed_item_code, 4]])

		# Purchase Return: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - TCP1", item_code=packed_item_code, qty=50, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=bundled_item, qty=5, rate=150, warehouse="Stores - TCP1",
			company=company, expense_account="Cost of Goods Sold - TCP1", cost_center="Main - TCP1")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 20)

		self.assertEqual(dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=bundled_item, qty=-2, rate=150,
			company=company, warehouse="Stores - TCP1", expense_account="Cost of Goods Sold - TCP1", cost_center="Main - TCP1")

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(return_dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 800)

		#-------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# Repost future SLE for Purchase Receipt
		repost_future_sle("Purchase Receipt", pr.name)


		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 20)
		self.assertEqual(outgoing_rate, 101)

		dn.reload()
		self.assertEqual(dn.packed_items[0].incoming_rate, 101)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(incoming_rate, 101)
		self.assertEqual(stock_value_difference, 808)

		return_dn.reload()
		self.assertEqual(return_dn.packed_items[0].incoming_rate, 101)

		# Cleanup data
		return_dn.cancel()
		dn.cancel()
		lcv.cancel()
		pr.cancel()

	def test_sub_contracted_item_costing(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		company = "_Test Company with perpetual inventory"
		rm_item_code="_Test Item for Reposting"
		subcontracted_item = "_Test Subcontracted Item for Reposting"

		bom = make_bom(item = subcontracted_item, raw_materials =[rm_item_code], currency="INR")
		
		# Purchase raw materials on supplier warehouse: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - TCP1", item_code=rm_item_code, qty=10, rate=100)

		# Purchase Receipt for subcontracted item
		pr1 = make_purchase_receipt(company=company, posting_date='2020-04-20',
			warehouse="Finished Goods - TCP1", supplier_warehouse="Stores - TCP1",
			item_code=subcontracted_item, qty=10, rate=20, is_subcontracted="Yes")

		self.assertEqual(pr1.items[0].valuation_rate, 120)

		# Update raw material's valuation via LCV, Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# Repost future SLE for Purchase Receipt
		repost_future_sle("Purchase Receipt", pr.name)

		pr1.reload()
		self.assertEqual(pr1.items[0].valuation_rate, 125)

		# check outgoing_rate for DN after reposting
		incoming_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": pr1.name, "item_code": subcontracted_item}, "incoming_rate")
		self.assertEqual(incoming_rate, 125)

		# cleanup data
		pr1.cancel()
		lcv.cancel()
		pr.cancel()


def create_repack_entry(**args):
	args = frappe._dict(args)
	repack = frappe.new_doc("Stock Entry")
	repack.stock_entry_type = "Repack"
	repack.company = args.company or "_Test Company"
	repack.posting_date = args.posting_date
	repack.set_posting_time = 1
	repack.append("items", {
		"item_code": "_Test Item for Reposting",
		"s_warehouse": "Stores - TCP1",
		"qty": 5,
		"conversion_factor": 1
	})

	repack.append("items", {
		"item_code": "_Test Finished Item for Reposting",
		"t_warehouse": "Finished Goods - TCP1",
		"qty": 1,
		"conversion_factor": 1
	})

	repack.append("additional_costs", {
		"expense_account": "Freight and Forwarding Charges - TCP1",
		"description": "transport cost",
		"amount": 40
	})

	repack.save()
	repack.submit()

	return repack

def create_product_bundle_item(new_item_code, packed_items):
	if not frappe.db.exists("Product Bundle", new_item_code):
		item = frappe.new_doc("Product Bundle")
		item.new_item_code = new_item_code

		for d in packed_items:
			item.append("items", {
				"item_code": d[0],
				"qty": d[1]
			})

		item.save()

def create_items():
	items = ["_Test Item for Reposting", "_Test Finished Item for Reposting",
		"_Test Subcontracted Item for Reposting", "_Test Bundled Item for Reposting"]
	for d in items:
		properties = {"valuation_method": "FIFO"}
		if d == "_Test Bundled Item for Reposting":
			properties.update({"is_stock_item": 0})
		elif d == "_Test Subcontracted Item for Reposting":
			properties.update({"is_sub_contracted_item": 1})

		make_item(d, properties=properties)

	return items