from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
test_records = frappe.get_test_records('Sales Invoice')

si = frappe.copy_doc(test_records[1])
si.items[0].uom = "_Test UOM 1"
si.items[0].conversion_factor = None

si.save()

item = si.items[0]

si = frappe.copy_doc(test_records[1])

si.items[0].uom = "_Test UOM 1"
si.items[0].conversion_factor = None
si.items[0].price_list_rate = None
si.save()

expected_values = {
	"keys": ["price_list_rate", "stock_uom", "uom", "conversion_factor", "rate", "amount",
		"base_price_list_rate", "base_rate", "base_amount"],
	"_Test Item": [1000, "_Test UOM", "_Test UOM 1", 10.0, 1000, 1000, 1000, 1000, 1000]
}

# check if the conversion_factor and price_list_rate is calculated according to uom
for d in si.get("items"):
	for i, k in enumerate(expected_values["keys"]):
		print k, d.get(k)==expected_values[d.item_code][i], d.get(k), expected_values[d.item_code][i]