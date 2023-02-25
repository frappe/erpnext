import frappe


def execute():
	doctypes = [
		"Supplier",
		"Activity Type",
		"Bank Transaction Mapping",
		"Bank",
		"Branch",
		"Brand",
		"Designation",
		"Driving License Category",
		"Employee Education",
		"Employee External Work History",
		"Holiday",
		"Holiday List",
		"Item Website Specification",
		"Print Heading",
		"Supplier Group",
		"Terms and Conditions",
		"UOM",
		"UOM Conversion Detail",
		"Customs Tariff Number",
		"Industry Type",
		"Item Attribute Value",
		"Item Attribute",
		"Item Barcode",
		"Item Group",
		"Item Supplier",
		"Location",
	]
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)
