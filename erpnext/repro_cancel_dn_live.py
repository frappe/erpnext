import time

import frappe
from frappe.utils import nowdate


def run():
	item_code = "TEST-CANCEL-SAME-TS-ITEM"
	warehouse = "Stores - TC"
	company = "Test Company"
	customer = frappe.db.get_value("Customer", {}, "name") or "Rakesh M"

	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_stock_item": 1,
				"stock_uom": "Nos",
			}
		).insert(ignore_permissions=True)
		print(f"Created Item {item_code}")

	posting_date = nowdate()
	posting_time = "10:00:00"

	# Bring in enough opening stock ahead of the DN cluster.
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"posting_date": posting_date,
			"posting_time": "09:00:00",
			"set_posting_time": 1,
			"items": [
				{
					"item_code": item_code,
					"t_warehouse": warehouse,
					"qty": 100,
					"basic_rate": 10,
					"conversion_factor": 1,
				}
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	print(f"Submitted opening Stock Entry {se.name}: +100 into {warehouse}")

	dns = []
	for i in range(5):
		dn = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": company,
				"customer": customer,
				"set_posting_time": 1,
				"posting_date": posting_date,
				"posting_time": posting_time,
				"items": [
					{
						"item_code": item_code,
						"warehouse": warehouse,
						"qty": 20,
						"rate": 10,
						"conversion_factor": 1,
						"allow_zero_valuation_rate": 1,
						"expense_account": frappe.get_cached_value(
							"Company", company, "default_expense_account"
						),
						"cost_center": frappe.get_cached_value("Company", company, "cost_center"),
					}
				],
			}
		)
		dn.insert(ignore_permissions=True)
		dn.submit()
		dns.append(dn)
		print(f"Submitted DN {i + 1}/5: {dn.name}")
		time.sleep(1)

	def qty_after(dn):
		return frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": dn.name, "is_cancelled": 0}, "qty_after_transaction"
		)

	print("\nqty_after_transaction before cancellation:")
	for dn in dns:
		print(" ", dn.name, "->", qty_after(dn))

	target = dns[1]
	print(f"\nCancelling {target.name} (2nd DN, same posting_datetime as the rest) ...")
	try:
		target.cancel()
		print("Cancel completed without error.")
	except Exception as e:
		print(f"Cancel RAISED: {type(e).__name__}: {e}")

	print("\nqty_after_transaction after cancellation:")
	for dn in dns:
		if dn.name == target.name:
			continue
		print(" ", dn.name, "->", qty_after(dn))

	frappe.db.commit()
	print("\nDone. Records left in place on site new-frappe-v16 for inspection.")
	print(f"Item: {item_code}, Warehouse: {warehouse}, Opening Stock Entry: {se.name}")
	print("Delivery Notes:", ", ".join(d.name for d in dns), f"(cancelled: {target.name})")
