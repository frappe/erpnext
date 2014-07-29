# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr
from frappe.model.mapper import get_mapped_doc
from frappe import _

from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {
	"quotation_details": "templates/form_grid/item_grid.html"
}

class Quotation(SellingController):
	tname = 'Quotation Item'
	fname = 'quotation_details'

	def validate(self):
		super(Quotation, self).validate()
		self.set_status()
		self.validate_order_type()
		self.validate_for_items()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.quotation_to = "Customer" if self.customer else "Lead"

	def has_sales_order(self):
		return frappe.db.get_value("Sales Order Item", {"prevdoc_docname": self.name, "docstatus": 1})

	def validate_for_items(self):
		chk_dupl_itm = []
		for d in self.get('quotation_details'):
			if [cstr(d.item_code),cstr(d.description)] in chk_dupl_itm:
				frappe.throw(_("Item {0} with same description entered twice").format(d.item_code))
			else:
				chk_dupl_itm.append([cstr(d.item_code),cstr(d.description)])

	def validate_order_type(self):
		super(Quotation, self).validate_order_type()

		if self.order_type in ['Maintenance', 'Service']:
			for d in self.get('quotation_details'):
				is_service_item = frappe.db.sql("select is_service_item from `tabItem` where name=%s", d.item_code)
				is_service_item = is_service_item and is_service_item[0][0] or 'No'

				if is_service_item == 'No':
					frappe.throw(_("Item {0} must be Service Item").format(d.item_code))
		else:
			for d in self.get('quotation_details'):
				is_sales_item = frappe.db.sql("select is_sales_item from `tabItem` where name=%s", d.item_code)
				is_sales_item = is_sales_item and is_sales_item[0][0] or 'No'

				if is_sales_item == 'No':
					frappe.throw(_("Item {0} must be Sales Item").format(d.item_code))

	def update_opportunity(self):
		for opportunity in list(set([d.prevdoc_docname for d in self.get("quotation_details")])):
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
		if not self.get('quotation_details'):
			frappe.throw(_("Please enter item details"))

	def on_submit(self):
		self.check_item_table()

		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype, self.company, self.grand_total, self)

		#update enquiry status
		self.update_opportunity()

	def on_cancel(self):
		#update enquiry status
		self.set_status()
		self.update_opportunity()

	def print_other_charges(self,docname):
		print_lst = []
		for d in self.get('other_charges'):
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
		target.ignore_permissions = ignore_permissions
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
	quotation = frappe.db.get_value("Quotation", source_name, ["lead", "order_type"])
	if quotation and quotation[0]:
		lead_name = quotation[0]
		customer_name = frappe.db.get_value("Customer", {"lead_name": lead_name},
			["name", "customer_name"], as_dict=True)
		if not customer_name:
			from erpnext.selling.doctype.lead.lead import _make_customer
			customer_doclist = _make_customer(lead_name, ignore_permissions=ignore_permissions)
			customer = frappe.get_doc(customer_doclist)
			customer.ignore_permissions = ignore_permissions
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
				from frappe.utils import get_url_to_form
				frappe.throw(_("Please create Customer from Lead {0}").format(lead_name))
		else:
			return customer_name
