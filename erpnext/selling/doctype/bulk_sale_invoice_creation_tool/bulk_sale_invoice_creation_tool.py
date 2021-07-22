# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

class BulkSaleInvoiceCreationTool(Document):
	@frappe.whitelist()
	def get_options(self, arg=None):
		if frappe.get_meta("Sales Invoice").get_field("naming_series"):
			return frappe.get_meta("Sales Invoice").get_field("naming_series").options
	@frappe.whitelist()
	def create_sales_invoice(self):
		lst = []
		for itm in self.items:
			lst.append(itm.customer)
		for customer in set(lst):
			doc = frappe.new_doc("Sales Invoice")
			doc.company = self.company
			doc.customer = customer
			doc.due_date = self.posting_date
			doc.currency = frappe.get_cached_value('Company', self.company, "default_currency")
			lst1 = []
			for itm in self.items:
				if customer == itm.customer:
					if self.is_nil_exempt == "Yes":
						if itm.is_nil_exempt:
							doc.append("items",{
								"item_name": itm.item_name,
								"item_code": itm.item_code,
								"description": itm.description,
								"qty": itm.qty,
								"uom": itm.uom,
								"stock_uom": itm.stock_uom,
								"conversion_factor": itm.conversion_factor,
								"rate": itm.rate,
								"warehouse": itm.warehouse,
								"income_account": itm.income_account,
								"item_tax_template": itm.item_tax_template,
								"sales_order": itm.sales_order,
								"so_detail": itm.so_detail,
								"delivery_note": itm.delivery_note,
								"dn_detail": itm.dn_detail,
								"cost_center": itm.cost_center,
								"is_nil_exempt": itm.is_nil_exempt,
								"is_free_item": itm.is_free_item,
								"price_list_rate": 0 if itm.is_free_item else itm.price_list_rate
							})
							if itm.item_tax_template:
								tax = frappe.get_doc("Item Tax Template",itm.item_tax_template)
								for t_id in tax.taxes:
									if t_id.tax_type not in lst1:
										doc.append("taxes", {
											"charge_type": "On Net Total",
											"account_head": t_id.tax_type,
											"description": t_id.tax_type,
											"rate": 0,
											"tax_amount": (t_id.tax_rate / 100.0) * itm.net_amount
										})
										lst1.append(t_id.tax_type)
					elif self.is_nil_exempt == "No":
						if not itm.is_nil_exempt:
							doc.append("items",{
								"item_name": itm.item_name,
								"item_code": itm.item_code,
								"description": itm.description,
								"qty": itm.qty,
								"uom": itm.uom,
								"stock_uom": itm.stock_uom,
								"conversion_factor": itm.conversion_factor,
								"rate": itm.rate,
								"warehouse": itm.warehouse,
								"income_account": itm.income_account,
								"item_tax_template": itm.item_tax_template,
								"sales_order": itm.sales_order,
								"so_detail": itm.so_detail,
								"delivery_note": itm.delivery_note,
								"dn_detail": itm.dn_detail,
								"cost_center": itm.cost_center,
								"is_nil_exempt": itm.is_nil_exempt,
								"is_free_item": itm.is_free_item,
								"price_list_rate": 0 if itm.is_free_item else itm.price_list_rate
							})
							if itm.item_tax_template:
								tax = frappe.get_doc("Item Tax Template",itm.item_tax_template)
								for t_id in tax.taxes:
									if t_id.tax_type not in lst1:
										doc.append("taxes", {
											"charge_type": "On Net Total",
											"account_head": t_id.tax_type,
											"description": t_id.tax_type,
											"rate": 0,
											"tax_amount": (t_id.tax_rate / 100.0) * itm.net_amount
										})
										lst1.append(t_id.tax_type)
					else:
						doc.append("items", {
							"item_name": itm.item_name,
							"item_code": itm.item_code,
							"description": itm.description,
							"qty": itm.qty,
							"uom": itm.uom,
							"stock_uom": itm.stock_uom,
							"conversion_factor": itm.conversion_factor,
							"rate": itm.rate,
							"warehouse": itm.warehouse,
							"income_account": itm.income_account,
							"item_tax_template": itm.item_tax_template,
							"sales_order": itm.sales_order,
							"so_detail": itm.so_detail,
							"delivery_note": itm.delivery_note,
							"dn_detail": itm.dn_detail,
							"cost_center": itm.cost_center,
							"is_nil_exempt": itm.is_nil_exempt,
							"is_free_item": itm.is_free_item,
							"price_list_rate": 0 if itm.is_free_item else itm.price_list_rate
						})
						if itm.item_tax_template:
							tax = frappe.get_doc("Item Tax Template", itm.item_tax_template)
							for t_id in tax.taxes:
								if t_id.tax_type not in lst1:
									doc.append("taxes", {
										"charge_type": "On Net Total",
										"account_head": t_id.tax_type,
										"description": t_id.tax_type,
										"rate": 0,
										"tax_amount": (t_id.tax_rate / 100.0) * itm.net_amount
									})
									lst1.append(t_id.tax_type)
			doc.naming_series = self.name_series
			doc.set_missing_values()
			doc.insert()
			doc.validate()
			doc.submit()



@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1

	def update_item(source, target, source_parent):

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			cost_center = item.get("selling_cost_center") \
				or item_group.get("selling_cost_center")
			income_account = frappe.get_cached_value('Company',source_parent.company, "default_income_account")
			if income_account:
				target.income_account = income_account
			if cost_center:
				target.cost_center = cost_center
			if source_parent.customer:
				target.customer = source_parent.customer

	doclist = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Bulk Sale Invoice Creation Tool",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Bulk Invoice Item",
			"field_map": {
				"name": "so_detail",
				"parent": "sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.qty and (doc.base_amount==0 or abs(doc.billed_amt) < abs(doc.amount))
		}
	}, target_doc, postprocess, ignore_permissions=ignore_permissions)

	return doclist

@frappe.whitelist()
def make_sales_invoice_quotation(source_name, target_doc=None, ignore_permissions=False):
	customer = _make_customer(source_name, ignore_permissions)

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		target.cost_center = None
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)
		if target.item_code:
			cost_center = frappe.get_cached_value('Company',source_parent.company, "cost_center")
			income_account = frappe.get_cached_value('Company',source_parent.company, "default_income_account")
			if income_account:
				target.income_account = income_account
			if cost_center:
				target.cost_center = cost_center
			if source_parent.quotation_to == "Customer":
				target.customer = source_parent.party_name


	doclist = get_mapped_doc("Quotation", source_name, {
			"Quotation": {
				"doctype": "Bulk Sale Invoice Creation Tool",
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Quotation Item": {
				"doctype": "Bulk Invoice Item",
				"postprocess": update_item
			}
		}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	return doclist


def _make_customer(source_name, ignore_permissions=False):
	quotation = frappe.db.get_value("Quotation",
		source_name, ["order_type", "party_name", "customer_name"], as_dict=1)

	if quotation and quotation.get('party_name'):
		if not frappe.db.exists("Customer", quotation.get("party_name")):
			lead_name = quotation.get("party_name")
			customer_name = frappe.db.get_value("Customer", {"lead_name": lead_name},
				["name", "customer_name"], as_dict=True)
			if not customer_name:
				from erpnext.crm.doctype.lead.lead import _make_customer
				customer_doclist = _make_customer(lead_name, ignore_permissions=ignore_permissions)
				customer = frappe.get_doc(customer_doclist)
				customer.flags.ignore_permissions = ignore_permissions
				if quotation.get("party_name") == "Shopping Cart":
					customer.customer_group = frappe.db.get_value("Shopping Cart Settings", None,
						"default_customer_group")

				try:
					customer.insert()
					return customer
				except frappe.NameError:
					if frappe.defaults.get_global_default('cust_master_name') == "Customer Name":
						customer.run_method("autoname")
						customer.name += "-" + lead_name
						customer.insert()
						return customer
					else:
						raise
				except frappe.MandatoryError:
					frappe.local.message_log = []
					frappe.throw(_("Please create Customer from Lead {0}").format(lead_name))
			else:
				return customer_name
		else:
			return frappe.get_doc("Customer", quotation.get("party_name"))


def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(frappe.db.sql("""select dn_item.item_code, sum(abs(dn_item.qty)) as qty
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
		group by dn_item.item_code
	""", delivery_note))

	return returned_qty_map

def get_invoiced_qty_map(delivery_note):
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

@frappe.whitelist()
def make_sales_invoice_delivery(source_name, target_doc=None):
	doc = frappe.get_doc('Delivery Note', source_name)

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been invoiced"))

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		if target_doc.item_code:
			cost_center = frappe.get_cached_value('Company', source_parent.company, "cost_center")
			income_account = frappe.get_cached_value('Company', source_parent.company, "default_income_account")
			if income_account:
				target_doc.income_account = income_account
			if cost_center:
				target_doc.cost_center = cost_center
			if source_parent.customer:
				target_doc.customer = source_parent.customer

	doc = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Bulk Sale Invoice Creation Tool",
			"field_map": {
				"is_return": "is_return"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Bulk Invoice Item",
			"field_map": {
				"name": "dn_detail",
				"parent": "delivery_note",
				"so_detail": "so_detail",
				"against_sales_order": "sales_order",
				"serial_no": "serial_no",
				"cost_center": "cost_center"
			},
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doc