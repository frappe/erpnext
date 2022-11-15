# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate, getdate
from frappe import _
from erpnext.crm.doctype.lead.lead import get_customer_from_lead

from erpnext.controllers.selling_controller import SellingController

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}


class Quotation(SellingController):
	def __init__(self, *args, **kwargs):
		super(Quotation, self).__init__(*args, **kwargs)
		self.status_map = [
			["Draft", None],
			["Open", "eval:self.docstatus==1"],
			["Lost", "eval:self.status=='Lost'"],
			["Ordered", "has_sales_order_or_invoice"],
			["Cancelled", "eval:self.docstatus==2"],
		]

	def validate(self):
		super(Quotation, self).validate()
		self.validate_uom_is_integer("stock_uom", "qty")
		self.validate_quotation_valid_till()
		self.set_customer_name()

		if self.items:
			self.with_items = 1

		self.set_ordered_status()
		self.set_status()

	def on_submit(self):
		# Check for Approving Authority
		frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
			self.company, self.base_grand_total, self)

		# update enquiry status
		self.update_opportunity()
		self.update_lead()

	def on_cancel(self):
		if self.lost_reasons:
			self.lost_reasons = []

		super(Quotation, self).on_cancel()

		# update enquiry status
		self.set_status(update=True)
		self.update_opportunity()
		self.update_lead()

	def onload(self):
		super(Quotation, self).onload()
		if self.quotation_to == "Customer":
			self.set_onload('customer', self.party_name)
		elif self.quotation_to == "Lead":
			self.set_onload('customer', get_customer_from_lead(self.party_name))

	def set_indicator(self):
		if self.docstatus == 1:
			self.indicator_color = 'blue'
			self.indicator_title = 'Submitted'
		if self.valid_till and getdate(self.valid_till) < getdate(nowdate()):
			self.indicator_color = 'darkgrey'
			self.indicator_title = 'Expired'

	def set_ordered_status(self, update=False, update_modified=True):
		ordered_qty_map = self.get_ordered_qty_map()
		for d in self.items:
			d.ordered_qty = flt(ordered_qty_map.get(d.name))
			if update:
				d.db_set({
					'ordered_qty': d.ordered_qty,
				}, update_modified=update_modified)

	def get_ordered_qty_map(self):
		ordered_qty_map = {}

		if self.docstatus == 1:
			row_names = [d.name for d in self.items]

			if row_names:
				ordered_qty_map = dict(frappe.db.sql("""
					select i.quotation_item, sum(i.qty)
					from `tabSales Order Item` i
					inner join `tabSales Order` p on p.name = i.parent
					where p.docstatus = 1 and i.quotation_item in %s
					group by i.quotation_item
				""", [row_names]))

			unordered_rows = list(set(row_names) - set(ordered_qty_map.keys()))
			if unordered_rows:
				billed_qty_map = dict(frappe.db.sql("""
					select i.quotation_item, sum(i.qty)
					from `tabSales Invoice Item` i
					inner join `tabSales Invoice` p on p.name = i.parent
					where p.docstatus = 1 and i.quotation_item in %s
					group by i.quotation_item
				""", [row_names]))

				for quotation_item, billed_qty in billed_qty_map.items():
					if quotation_item not in ordered_qty_map:
						ordered_qty_map[quotation_item] = billed_qty

		return ordered_qty_map

	def update_lead(self):
		if self.quotation_to == "Lead" and self.party_name:
			doc = frappe.get_doc("Lead", self.party_name)
			doc.set_status(update=True)
			doc.notify_update()

	def update_opportunity(self):
		for opportunity in list(set([d.prevdoc_docname for d in self.get("items")])):
			if opportunity:
				self.update_opportunity_status(opportunity)

		if self.opportunity:
			self.update_opportunity_status()

	def update_opportunity_status(self, opportunity=None):
		if not opportunity:
			opportunity = self.opportunity

		opp = frappe.get_doc("Opportunity", opportunity)
		opp.set_status(update=True)
		opp.notify_update()

	def has_sales_order_or_invoice(self):
		return frappe.db.get_value("Sales Order Item", {"quotation": self.name, "docstatus": 1})\
			or frappe.db.get_value("Sales Invoice Item", {"quotation": self.name, "docstatus": 1})

	def declare_enquiry_lost(self, lost_reasons_list, detailed_reason=None):
		if not self.has_sales_order_or_invoice():
			frappe.db.set(self, 'status', 'Lost')

			if detailed_reason:
				frappe.db.set(self, 'order_lost_reason', detailed_reason)

			for reason in lost_reasons_list:
				self.append('lost_reasons', reason)

			self.update_opportunity()
			self.update_lead()
			self.save()

		else:
			frappe.throw(_("Cannot set as Lost as Sales Order is made."))

	def set_customer_name(self):
		if self.party_name and self.quotation_to == 'Customer':
			self.customer_name = frappe.get_cached_value("Customer", self.party_name, "customer_name")
		elif self.party_name and self.quotation_to == 'Lead':
			lead_name, company_name = frappe.db.get_value("Lead", self.party_name, ["lead_name", "company_name"])
			self.customer_name = company_name or lead_name

	def print_other_charges(self,docname):
		print_lst = []
		for d in self.get('taxes'):
			lst1 = []
			lst1.append(d.description)
			lst1.append(d.total)
			print_lst.append(lst1)
		return print_lst

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.valid_till = None


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Quotations'),
	})

	return list_context


@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
	quotation = frappe.db.get_value("Quotation", source_name, ["transaction_date", "valid_till"], as_dict = 1)
	if quotation.valid_till and (quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())):
		frappe.throw(_("Validity period of this quotation has ended."))
	return _make_sales_order(source_name, target_doc)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		customer = get_customer_from_quotation(source)
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		if source.referral_sales_partner:
			target.sales_partner=source.referral_sales_partner
			target.commission_rate=frappe.get_value('Sales Partner', source.referral_sales_partner, 'commission_rate')

		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_payment_schedule")

	def update_item(obj, target, source_parent, target_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

	doclist = get_mapped_doc("Quotation", source_name, {
			"Quotation": {
				"doctype": "Sales Order",
				"validation": {
					"docstatus": ["=", 1]
				},
				"field_map": {
					"remarks": "remarks"
				}
			},
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {
					"parent": "quotation",
					"name": "quotation_item",
					"project_template": "project_template",
				},
				"postprocess": update_item
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"add_if_empty": True
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"add_if_empty": True
			},
			"Payment Schedule": {
				"doctype": "Payment Schedule",
				"add_if_empty": True
			}
		}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

	# postprocess: fetch shipping address, set missing values

	return doclist


def set_expired_status():
	frappe.db.sql("""
		UPDATE
			`tabQuotation` SET `status` = 'Expired'
		WHERE
			`status` not in ('Ordered', 'Expired', 'Lost', 'Cancelled') AND `valid_till` < %s
		""", (nowdate()))


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	return _make_sales_invoice(source_name, target_doc)


def _make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		customer = get_customer_from_quotation(source)
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_payment_schedule")
		target.run_method("set_due_date")

	def update_item(source, target, source_parent, target_parent):
		target.project = source_parent.get('project')
		target.cost_center = None
		target.stock_qty = flt(source.qty) * flt(source.conversion_factor)
		target.depreciation_percentage = None

		if target_parent:
			target_parent.set_rate_zero_for_claim_item(source, target)

	doclist = get_mapped_doc("Quotation", source_name, {
			"Quotation": {
				"doctype": "Sales Invoice",
				"validation": {
					"docstatus": ["=", 1]
				},
				"field_no_map": [
					"has_stin",
				],
				"field_map": {
					"remarks": "remarks"
				}
			},
			"Quotation Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"parent": "quotation",
					"name": "quotation_item",
				},
				"postprocess": update_item
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

	return doclist


def get_customer_from_quotation(quotation):
	if quotation and quotation.get('party_name'):
		if quotation.get('quotation_to') == 'Lead':
			customer = get_customer_from_lead(quotation.get("party_name"), throw=True)
			return frappe.get_cached_doc("Customer", customer)

		elif quotation.get('quotation_to') == 'Customer':
			return frappe.get_cached_doc("Customer", quotation.get("party_name"))
