import frappe
from frappe.utils import cint
from frappe.model.utils.rename_field import rename_field
from frappe.model.rename_doc import rename_doc
from six import iteritems

custom_scripts = {
	"Sales Invoice-Client": """frappe.ui.form.on("Sales Invoice", {
  validate: function(frm) {
    if (frm.doc.territory == "All Territories") {
      frappe.throw(__("Territory cannot be 'All Territories'"))
    }
  }
});""",
	"Delivery Note-Client": """frappe.ui.form.on("Delivery Note", {
  validate: function(frm) {
    if (frm.doc.territory == "All Territories") {
      frappe.throw(__("Territory cannot be 'All Territories'"))
    }
  }
});"""
}

to_delete = {
	"Custom Script": ['Payment Entry-Client']
}

naming_series_to_hide = ['Sales Invoice', 'Delivery Note', 'Sales Order', 'Payment Entry',
	'Purchase Order', 'Purchase Receipt', 'Purchase Invoice']

doctype_naming_series = {
	"Stock Entry": "STE-.CO.-.YYYY.-",
	"Sales Order": "SO-.CO.-.YYYY.-",
	"Delivery Note": "DO-.CO.-.YYYY.-\nDR-.CO.-.YYYY.-",
	"Journal Entry": "\nJV-.CO.-.YYYY.-\nBBP-.CO.-.YYYY.-\nBBR-.CO.-.YYYY.-\nCBP-.CO.-.YYYY.-\nCBR-.CO.-.YYYY.-",
	"Purchase Receipt": "PREC-.CO.-.YYYY.-",
	"Purchase Order": "PO-.CO.-.YYYY.-",
	"Sales Invoice": "SB-.CO.-.YYYY.-\nSBR-.CO.-.YYYY.-\nCO.-\nCO.-S-\nCO.-SR-\nCO.-S-SR-",
	"Purchase Invoice": "PINV-.CO.-.YYYY.-",
	"Payment Entry": "PE-.CO.-.YYYY.-\nBP-.CO.-.YYYY.-\nBR-.CO.-.YYYY.-\nCP-.CO.-.YYYY.-\nCR-.CO.-.YYYY.-",
}

auto_value_setters = [
	{
		"document_type": "Sales Invoice",
		"field_name": "naming_series",
		"conditions": [
			{"value": "CO.-S-SR-", "condition": "doc.has_stin and doc.order_type == 'Maintenance' and doc.is_return"},
			{"value": "CO.-S-", "condition": "doc.has_stin and doc.order_type == 'Maintenance'"},
			{"value": "CO.-SR-", "condition": "doc.has_stin and doc.is_return"},
			{"value": "CO.-", "condition": "doc.has_stin"},
			{"value": "SBR-.CO.-.YYYY.-", "condition": "doc.is_return"},
			{"value": "SB-.CO.-.YYYY.-", "condition": ""},
		]
	},
	{
		"document_type": "Sales Invoice",
		"field_name": "select_print_heading",
		"conditions": [
			{"value": "Credit Note (Service)", "condition": "doc.has_stin and doc.order_type == 'Maintenance' and doc.is_return"},
			{"value": "Sales Tax Invoice (Service)", "condition": "doc.has_stin and doc.order_type == 'Maintenance'"},
			{"value": "Credit Note", "condition": "doc.has_stin and doc.is_return"},
			{"value": "Sales Tax Invoice", "condition": "doc.has_stin"},
			{"value": "Credit Note", "condition": "doc.is_return"},
			{"value": "", "condition": "1"},
		]
	},
	{
		"document_type": "Delivery Note",
		"field_name": "naming_series",
		"conditions": [
			{"value": "DR-.CO.-.YYYY.-", "condition": "doc.is_return"},
			{"value": "DO-.CO.-.YYYY.-", "condition": ""},
		]
	},
	{
		"document_type": "Delivery Note",
		"field_name": "select_print_heading",
		"conditions": [
			{"value": "Sales Return", "condition": "doc.is_return"},
			{"value": "", "condition": "1"},
		]
	},
	{
		"document_type": "Payment Entry",
		"field_name": "naming_series",
		"conditions": [
			{"value": "CP-.CO.-.YYYY.-", "condition": "doc.payment_type == 'Pay' and frappe.get_cached_value('Account', doc.paid_from, 'account_type') == 'Cash'"},
			{"value": "BP-.CO.-.YYYY.-", "condition": "doc.payment_type == 'Pay'"},
			{"value": "CR-.CO.-.YYYY.-", "condition": "doc.payment_type == 'Receive' and frappe.get_cached_value('Account', doc.paid_to, 'account_type') == 'Cash'"},
			{"value": "BR-.CO.-.YYYY.-", "condition": "doc.payment_type == 'Receive'"},
			{"value": "PE-.CO.-.YYYY.-", "condition": ""},
		]
	},
	{
		"document_type": "Payment Entry",
		"field_name": "print_heading",
		"conditions": [
			{"value": "Cash Payment Voucher", "condition": "doc.payment_type == 'Pay' and frappe.get_cached_value('Account', doc.paid_from, 'account_type') == 'Cash'"},
			{"value": "Bank Payment Voucher", "condition": "doc.payment_type == 'Pay'"},
			{"value": "Cash Receipt Voucher", "condition": "doc.payment_type == 'Receive' and frappe.get_cached_value('Account', doc.paid_to, 'account_type') == 'Cash'"},
			{"value": "Bank Receipt Voucher", "condition": "doc.payment_type == 'Receive'"},
			{"value": "", "condition": "1"},
		]
	}
]

print_headings = [
	'Sales Tax Invoice', 'Sales Tax Invoice (Service)',
	'Credit Note', 'Credit Note (Service)',
	'Cash Payment Voucher', 'Bank Payment Voucher', 'Cash Receipt Voucher', 'Bank Receipt Voucher',
	'Sales Return'
]

def execute():
	is_dev_mode = frappe.conf.developer_mode
	frappe.conf.developer_mode = 0
	rename_doc("DocType", "Order Type", "Transaction Type", 1, 0, 1)
	frappe.conf.developer_mode = is_dev_mode

	frappe.reload_doc("selling", "doctype", "transaction_type")
	frappe.reload_doc("selling", "doctype", "sales_order")
	frappe.reload_doc("stock", "doctype", "delivery_note")
	frappe.reload_doc("accounts", "doctype", "sales_invoice")
	frappe.reload_doc("accounts", "doctype", "tax_rule")
	frappe.reload_doc("core", "doctype", "auto_value_setter")
	frappe.reload_doc("core", "doctype", "auto_value_setter_condition")

	rename_field("Transaction Type", "order_type_name", "transaction_type_name")
	rename_field("Transaction Type", "type", "order_type")

	rename_field("Sales Order", "order_type_name", "transaction_type")
	rename_field("Delivery Note", "order_type_name", "transaction_type")
	rename_field("Sales Invoice", "order_type_name", "transaction_type")

	rename_field("Tax Rule", "stin", "has_stin")
	rename_field("Tax Rule", "order_type", "transaction_type")

	frappe.db.sql("""update `tabTax Rule` set has_stin = 'Yes' where has_stin = 'Set'""")
	frappe.db.sql("""update `tabTax Rule` set has_stin = 'No' where has_stin = 'Not Set'""")

	frappe.db.sql("""update `tabSales Invoice` set has_stin = if(ifnull(stin, 0) = 0, 0, 1)""")

	site_name = frappe.utils.get_site_name(frappe.utils.get_host_name())
	if site_name in ('tar.time.net.pk', 'time.time.net.pk', 'tti.time.net.pk', 'ct.time.net.pk', 'atc.time.net.pk',
			'pc.time.net.pk', 'personal.time.net.pk', 'tar'):
		for dt, names in iteritems(to_delete):
			for dn in names:
				frappe.delete_doc_if_exists(dt, dn)

		for dn, script in iteritems(custom_scripts):
			if frappe.db.exists("Custom Script", dn):
				frappe.db.set_value("Custom Script", dn, 'script', script)

		for company in frappe.get_all("Company", fields=['name', 'abbr']):
			max_fbr_stin = frappe.db.sql("""
				select max(stin)
				from `tabSales Invoice`
				where company = %s and transaction_type != 'Service' and docstatus=1 and is_return=0
			""", company.name)
			max_srb_stin = frappe.db.sql("""
				select max(stin)
				from `tabSales Invoice`
				where company = %s and transaction_type = 'Service' and docstatus=1 and is_return=0
			""", company.name)

			if max_fbr_stin and max_fbr_stin[0][0]:
				prefix = "{0}-".format(company.abbr)
				frappe.db.sql("replace into `tabSeries` (name, current) values (%s, %s)", [prefix, max_fbr_stin[0][0]])
			if max_srb_stin and max_srb_stin[0][0]:
				prefix = "{0}-S-".format(company.abbr)
				frappe.db.sql("replace into `tabSeries` (name, current) values (%s, %s)", [prefix, max_srb_stin[0][0]])

		naming_series_controller = frappe.new_doc("Naming Series")
		for dt, series in iteritems(doctype_naming_series):
			naming_series_controller.user_must_always_select = cint(series.startswith("\n"))
			naming_series_controller.set_series_for(dt, series.split("\n"))

		for dt in naming_series_to_hide:
			frappe.make_property_setter({'doctype': dt, 'fieldname': 'naming_series', 'property': 'hidden', 'value': 1})

		for d in auto_value_setters:
			doc = frappe.new_doc("Auto Value Setter")
			doc.update(d)
			doc.save()

		for name in print_headings:
			if not frappe.db.exists("Print Heading", name):
				doc = frappe.new_doc("Print Heading")
				doc.print_heading = name
				doc.save()
