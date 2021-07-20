# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today, add_days
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation \
	import create_stock_reconciliation
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import create_landed_cost_voucher
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import BackDatedStockTransaction
from frappe.core.page.permission_manager.permission_manager import reset

class TestStockLedgerEntry(unittest.TestCase):
	def setUp(self):
		items = create_items()
		reset('Stock Entry')

		# delete SLE and BINs for all items
		frappe.db.sql("delete from `tabStock Ledger Entry` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)
		frappe.db.sql("delete from `tabBin` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)

	def test_item_cost_reposting(self):
		company = "_Test Company"

		# _Test Item for Reposting at Stores warehouse on 10-04-2020: Qty = 50, Rate = 100
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=100,
			company=company,
			expense_account = "Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-10',
			posting_time='14:00'
		)

		# _Test Item for Reposting at FG warehouse on 20-04-2020: Qty = 10, Rate = 200
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Finished Goods - _TC",
			qty=10,
			rate=200,
			company=company,
			expense_account="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-20',
			posting_time='14:00'
		)

		# _Test Item for Reposting transferred from Stores to FG warehouse on 30-04-2020
		se = make_stock_entry(
			item_code="_Test Item for Reposting",
			source="Stores - _TC",
			target="Finished Goods - _TC",
			company=company,
			qty=10,
			expense_account="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-30',
			posting_time='14:00'
		)
		target_wh_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": se.name
		}, ["valuation_rate"], as_dict=1)

		self.assertEqual(target_wh_sle.get("valuation_rate"), 150)

		# Repack entry on 5-5-2020
		repack = create_repack_entry(company=company, posting_date='2020-05-05', posting_time='14:00')

		finished_item_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": repack.name
		}, ["incoming_rate", "valuation_rate"], as_dict=1)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 540)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 540)

		# Reconciliation for _Test Item for Reposting at Stores on 12-04-2020: Qty = 50, Rate = 150
		sr = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=150,
			company=company,
			expense_account ="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-12',
			posting_time='14:00'
		)


		# Check valuation rate of finished goods warehouse after back-dated entry at Stores
		target_wh_sle = get_previous_sle({
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"posting_date": '2020-04-30',
			"posting_time": '14:00'
		})
		self.assertEqual(target_wh_sle.get("incoming_rate"), 150)
		self.assertEqual(target_wh_sle.get("valuation_rate"), 175)

		# Check valuation rate of repacked item after back-dated entry at Stores
		finished_item_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": repack.name
		}, ["incoming_rate", "valuation_rate"], as_dict=1)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 790)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 790)

		# Check updated rate in Repack entry
		repack.reload()
		self.assertEqual(repack.items[0].get("basic_rate"), 150)
		self.assertEqual(repack.items[1].get("basic_rate"), 750)

	def test_purchase_return_valuation_reposting(self):
		pr = make_purchase_receipt(company="_Test Company", posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code="_Test Item for Reposting", qty=5, rate=100)

		return_pr = make_purchase_receipt(company="_Test Company", posting_date='2020-04-15',
			warehouse="Stores - _TC", item_code="_Test Item for Reposting", is_return=1, return_against=pr.name, qty=-2)

		# check sle
		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 100)
		self.assertEqual(stock_value_difference, -200)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 110)
		self.assertEqual(stock_value_difference, -220)

	def test_sales_return_valuation_reposting(self):
		company = "_Test Company"
		item_code="_Test Item for Reposting"

		# Purchase Return: Qty = 5, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=item_code, qty=5, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=item_code, qty=5, rate=150, warehouse="Stores - _TC",
			company=company, expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5)

		self.assertEqual(dn.items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=item_code, qty=-2, rate=150,
			company=company, warehouse="Stores - _TC", expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

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
		company = "_Test Company"
		packed_item_code="_Test Item for Reposting"
		bundled_item = "_Test Bundled Item for Reposting"
		create_product_bundle_item(bundled_item, [[packed_item_code, 4]])

		# Purchase Return: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=packed_item_code, qty=50, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=bundled_item, qty=5, rate=150, warehouse="Stores - _TC",
			company=company, expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 20)

		self.assertEqual(dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=bundled_item, qty=-2, rate=150,
			company=company, warehouse="Stores - _TC", expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

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

		company = "_Test Company"
		rm_item_code="_Test Item for Reposting"
		subcontracted_item = "_Test Subcontracted Item for Reposting"

		frappe.db.set_value("Buying Settings", None, "backflush_raw_materials_of_subcontract_based_on", "BOM")
		make_bom(item = subcontracted_item, raw_materials =[rm_item_code], currency="INR")

		# Purchase raw materials on supplier warehouse: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=rm_item_code, qty=10, rate=100)

		# Purchase Receipt for subcontracted item
		pr1 = make_purchase_receipt(company=company, posting_date='2020-04-20',
			warehouse="Finished Goods - _TC", supplier_warehouse="Stores - _TC",
			item_code=subcontracted_item, qty=10, rate=20, is_subcontracted="Yes")

		self.assertEqual(pr1.items[0].valuation_rate, 120)

		# Update raw material's valuation via LCV, Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

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

	def test_back_dated_entry_not_allowed(self):
		# Back dated stock transactions are only allowed to stock managers
		frappe.db.set_value("Stock Settings", None,
			"role_allowed_to_create_edit_back_dated_transactions", "Stock Manager")

		# Set User with Stock User role but not Stock Manager
		try:
			user = frappe.get_doc("User", "test@example.com")
			user.add_roles("Stock User")
			user.remove_roles("Stock Manager")

			frappe.set_user(user.name)

			stock_entry_on_today = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
			back_dated_se_1 = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100,
				posting_date=add_days(today(), -1), do_not_submit=True)

			# Block back-dated entry
			self.assertRaises(BackDatedStockTransaction, back_dated_se_1.submit)

			frappe.set_user("Administrator")
			user.add_roles("Stock Manager")
			frappe.set_user(user.name)

			# Back dated entry allowed to Stock Manager
			back_dated_se_2 = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100,
				posting_date=add_days(today(), -1))

			back_dated_se_2.cancel()
			stock_entry_on_today.cancel()

		finally:
			frappe.db.set_value("Stock Settings", None, "role_allowed_to_create_edit_back_dated_transactions", None)
			frappe.set_user("Administrator")
			user.remove_roles("Stock Manager")


def create_repack_entry(**args):
	args = frappe._dict(args)
	repack = frappe.new_doc("Stock Entry")
	repack.stock_entry_type = "Repack"
	repack.company = args.company or "_Test Company"
	repack.posting_date = args.posting_date
	repack.set_posting_time = 1
	repack.append("items", {
		"item_code": "_Test Item for Reposting",
		"s_warehouse": "Stores - _TC",
		"qty": 5,
		"conversion_factor": 1,
		"expense_account": "Stock Adjustment - _TC",
		"cost_center": "Main - _TC"
	})

	repack.append("items", {
		"item_code": "_Test Finished Item for Reposting",
		"t_warehouse": "Finished Goods - _TC",
		"qty": 1,
		"conversion_factor": 1,
		"expense_account": "Stock Adjustment - _TC",
		"cost_center": "Main - _TC"
	})

	repack.append("additional_costs", {
		"expense_account": "Freight and Forwarding Charges - _TC",
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
