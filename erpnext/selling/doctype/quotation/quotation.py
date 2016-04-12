# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.mapper import get_mapped_doc
from frappe import _
import json
from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class Quotation(SellingController):
	def validate(self):
		super(Quotation, self).validate()
		self.set_status()
		self.validate_order_type()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.validate_quotation_to()
		if self.items:
			self.with_items = 1

	def has_sales_order(self):
		return frappe.db.get_value("Sales Order Item", {"prevdoc_docname": self.name, "docstatus": 1})

	def validate_order_type(self):
		super(Quotation, self).validate_order_type()

		for d in self.get('items'):
			if not frappe.db.get_value("Item", d.item_code, "is_sales_item"):
				frappe.throw(_("Item {0} must be Sales Item").format(d.item_code))

	def validate_quotation_to(self):
		if self.customer:
			self.quotation_to = "Customer"
			self.lead = None
		elif self.lead:
			self.quotation_to = "Lead"

	def update_opportunity(self):
		for opportunity in list(set([d.prevdoc_docname for d in self.get("items")])):
			if opportunity:
				frappe.get_doc("Opportunity", opportunity).set_status(update=True)

	def declare_order_lost(self, arg):
		if not self.has_sales_order():
			frappe.db.set(self, 'status', 'Lost')
			frappe.db.set(self, 'order_lost_reason', arg)
			self.update_opportunity()
		else:
			frappe.throw(_("Cannot set as Lost as Sales Order is made."))

	def check_item_table(self):
		if not self.get('items'):
			frappe.throw(_("Please enter item details"))

	def on_submit(self):
		self.check_item_table()

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.base_grand_total, self)

		#update enquiry status
		self.update_opportunity()

	def on_cancel(self):
		#update enquiry status
		self.set_status()
		self.update_opportunity()

	def print_other_charges(self,docname):
		print_lst = []
		for d in self.get('taxes'):
			lst1 = []
			lst1.append(d.description)
			lst1.append(d.total)
			print_lst.append(lst1)
		return print_lst


@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
	return _make_sales_order(source_name, target_doc)

def _make_sales_order(source_name, target_doc=None, ignore_permissions=False):
	customer = _make_customer(source_name, ignore_permissions)

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doclist = get_mapped_doc("Quotation", source_name, {
			"Quotation": {
				"doctype": "Sales Order",
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {
					"parent": "prevdoc_docname"
				}
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"add_if_empty": True
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"add_if_empty": True
			}
		}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	# postprocess: fetch shipping address, set missing values

	return doclist

def _make_customer(source_name, ignore_permissions=False):
	quotation = frappe.db.get_value("Quotation", source_name, ["lead", "order_type", "customer"])
	if quotation and quotation[0] and not quotation[2]:
		lead_name = quotation[0]
		customer_name = frappe.db.get_value("Customer", {"lead_name": lead_name},
			["name", "customer_name"], as_dict=True)
		if not customer_name:
			from erpnext.crm.doctype.lead.lead import _make_customer
			customer_doclist = _make_customer(lead_name, ignore_permissions=ignore_permissions)
			customer = frappe.get_doc(customer_doclist)
			customer.flags.ignore_permissions = ignore_permissions
			if quotation[1] == "Shopping Cart":
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


@frappe.whitelist()
def get_relative_items(item_code,item_name):
	relative_items = {
					"Suggested Items":common_query(item_code,item_name,"Suggested Items"),
					"Alternate Items":common_query(item_code,item_name,"Alternate Items"),
					"Accessory Items":common_query(item_code,item_name,"Accessory Items")
					}
	if len(relative_items["Suggested Items"]) > 0 or len(relative_items["Alternate Items"]) > 0 or len(relative_items["Accessory Items"]) > 0:				
		return relative_items	

def common_query(item_code,item_name,type):
	return frappe.db.sql("""select t1.item_code 
							from `tabItemType`t1,`tabItem`t2 
							where t1.parent = t2.name 
							and t1.item_type = '{0}' 
							and t2.name = '{1}' 
							and t2.item_code = '{2}' """.format(type,item_name,item_code),as_dict=1)	
	
@frappe.whitelist()
def items_details(item_list,item_code):
	current_list = json.loads(item_list)
	list2 = tuple([x.encode('UTF8') for x in list(current_list) if x])
	if len(current_list) == 1:
		cond = "t1.item_code =  {0} ".format(item_list[1:len(item_list) - 1])
	elif len(current_list) > 1:
		cond = "t1.item_code in {0}".format(list2)
	
	items_details = frappe.db.sql("""select t1.item_code,t1.item_name,t1.item_type,t2.name 
									from `tabItemType`t1,
									`tabItem`t2
									where {0} 
									and t1.parent = t2.name
									and t2.name = '{1}' """.format(cond,item_code),as_dict=1)
	return items_details
