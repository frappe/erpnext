# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, random, json, erpnext
from frappe.utils.make_random import how_many, get_random
from frappe.desk import query_report
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.party import get_party_account_currency
from erpnext.exceptions import InvalidCurrency
from erpnext.stock.doctype.material_request.material_request import make_request_for_quotation
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import \
			 make_supplier_quotation_from_rfq

def work():
	frappe.set_user(frappe.db.get_global('demo_purchase_user'))

	if random.random() < 0.6:
		report = "Items To Be Requested"
		for row in query_report.run(report)["result"][:random.randint(1, 5)]:
			item_code, qty = row[0], abs(row[-1])

			mr = make_material_request(item_code, qty)

	if random.random() < 0.6:
		for mr in frappe.get_all('Material Request',
			filters={'material_request_type': 'Purchase', 'status': 'Open'},
			limit=random.randint(1,6)):
			if not frappe.get_all('Request for Quotation',
				filters={'material_request': mr.name}, limit=1):
				rfq = make_request_for_quotation(mr.name)
				rfq.transaction_date = frappe.flags.current_date
				add_suppliers(rfq)
				rfq.save()
				rfq.submit()

	# Make suppier quotation from RFQ against each supplier.
	if random.random() < 0.6:
		for rfq in frappe.get_all('Request for Quotation',
			filters={'status': 'Open'}, limit=random.randint(1, 6)):
			if not frappe.get_all('Supplier Quotation',
				filters={'request_for_quotation': rfq.name}, limit=1):
				rfq = frappe.get_doc('Request for Quotation', rfq.name)

				for supplier in rfq.suppliers:
					supplier_quotation = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier.supplier)
					supplier_quotation.save()
					supplier_quotation.submit()

	# get supplier details
	supplier = get_random("Supplier")

	company_currency = frappe.get_cached_value('Company', erpnext.get_default_company(), "default_currency")
	party_account_currency = get_party_account_currency("Supplier", supplier, erpnext.get_default_company())
	if company_currency == party_account_currency:
		exchange_rate = 1
	else:
		exchange_rate = get_exchange_rate(party_account_currency, company_currency, args="for_buying")

	# make supplier quotations
	if random.random() < 0.5:
		from erpnext.stock.doctype.material_request.material_request import make_supplier_quotation

		report = "Material Requests for which Supplier Quotations are not created"
		for row in query_report.run(report)["result"][:random.randint(1, 3)]:
			if row[0] != "Total":
				sq = frappe.get_doc(make_supplier_quotation(row[0]))
				sq.transaction_date = frappe.flags.current_date
				sq.supplier = supplier
				sq.currency = party_account_currency or company_currency
				sq.conversion_rate = exchange_rate
				sq.insert()
				sq.submit()
				frappe.db.commit()

	# make purchase orders
	if random.random() < 0.5:
		from erpnext.stock.doctype.material_request.material_request import make_purchase_order
		report = "Requested Items To Be Ordered"
		for row in query_report.run(report)["result"][:how_many("Purchase Order")]:
			if row[0] != "Total":
				try:
					po = frappe.get_doc(make_purchase_order(row[0]))
					po.supplier = supplier
					po.currency = party_account_currency or company_currency
					po.conversion_rate = exchange_rate
					po.transaction_date = frappe.flags.current_date
					po.insert()
					po.submit()
				except Exception:
					pass
				else:
					frappe.db.commit()

	if random.random() < 0.5:
		make_subcontract()

def make_material_request(item_code, qty):
	mr = frappe.new_doc("Material Request")

	variant_of = frappe.db.get_value('Item', item_code, 'variant_of') or item_code

	if frappe.db.get_value('BOM', {'item': variant_of, 'is_default': 1, 'is_active': 1}):
		mr.material_request_type = 'Manufacture'
	else:
		mr.material_request_type = "Purchase"

	mr.transaction_date = frappe.flags.current_date
	mr.schedule_date = frappe.utils.add_days(mr.transaction_date, 7)

	mr.append("items", {
		"doctype": "Material Request Item",
		"schedule_date": frappe.utils.add_days(mr.transaction_date, 7),
		"item_code": item_code,
		"qty": qty
	})
	mr.insert()
	mr.submit()
	return mr

def add_suppliers(rfq):
	for i in range(2):
		supplier = get_random("Supplier")
		if supplier not in [d.supplier for d in rfq.get('suppliers')]:
			rfq.append("suppliers", { "supplier": supplier })

def make_subcontract():
	from erpnext.buying.doctype.purchase_order.purchase_order import make_rm_stock_entry
	item_code = get_random("Item", {"is_sub_contracted_item": 1})
	if item_code:
		# make sub-contract PO
		po = frappe.new_doc("Purchase Order")
		po.is_subcontracted = "Yes"
		po.supplier = get_random("Supplier")
		po.transaction_date = frappe.flags.current_date # added
		po.schedule_date = frappe.utils.add_days(frappe.flags.current_date, 7)

		item_code = get_random("Item", {"is_sub_contracted_item": 1})

		po.append("items", {
			"item_code": item_code,
			"schedule_date": frappe.utils.add_days(frappe.flags.current_date, 7),
			"qty": random.randint(10, 30)
		})
		po.set_missing_values()
		try:
			po.insert()
		except InvalidCurrency:
			return

		po.submit()

		# make material request for
		make_material_request(po.items[0].item_code, po.items[0].qty)

		# transfer material for sub-contract
		rm_items = get_rm_item(po.items[0], po.supplied_items[0])
		stock_entry = frappe.get_doc(make_rm_stock_entry(po.name, json.dumps([rm_items])))
		stock_entry.from_warehouse = "Stores - WPL"
		stock_entry.to_warehouse = "Supplier - WPL"
		stock_entry.insert()

def get_rm_item(items, supplied_items):
	return {
		"item_code": items.get("item_code"),
		"rm_item_code": supplied_items.get("rm_item_code"),
		"item_name": supplied_items.get("rm_item_code"),
		"qty": supplied_items.get("required_qty") + random.randint(3,10),
		"amount": supplied_items.get("amount"),
		"warehouse": supplied_items.get("reserve_warehouse"),
		"rate": supplied_items.get("rate"),
		"stock_uom": supplied_items.get("stock_uom")
	}
