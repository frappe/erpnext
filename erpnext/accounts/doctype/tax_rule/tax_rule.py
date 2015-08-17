# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class IncorrectCustomerGroup(frappe.ValidationError): pass

class TaxRule(Document):
	def validate(self):
		self.validate_tax_template()
		self.validate_customer_group()
		self.validate_date()
		self.validate_filters()
		
	def validate_tax_template(self):
		if not (self.sales_tax_template or self.purchase_tax_template):
			frappe.throw(_("Tax Template is mandatory."))
		if self.tax_type=="Sales":
			self.purchase_tax_template= None
		else:
			self.sales_tax_template= None

	def validate_customer_group(self):
		if self.customer and self.customer_group:
			if not frappe.db.get_value("Customer", self.customer, "customer_group") == self.customer_group:
				frappe.throw(_("Customer {0} does not belong to customer group {1}"). \
					format(self.customer, self.customer_group), IncorrectCustomerGroup)
				
	def validate_date(self):
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be greater than To Date"))

	def validate_filters(self):
		filters = {
			"customer": 		self.customer,
			"customer_group": 	self.customer_group,
			"billing_city":		self.billing_city,
			"billing_country":	self.billing_country,
			"shipping_city":	self.shipping_city,
			"shipping_country":	self.shipping_country,
			"tax_type":			self.tax_type,
			"company":			self.company
		}
		
		conds=""
		for d in filters:
			if conds:
				conds += " and "
			conds += """{0} = '{1}'""".format(d, filters[d])
			
		conds += """ and ((from_date > '{from_date}' and from_date < '{to_date}') or
				(to_date > '{from_date}' and to_date < '{to_date}') or
				('{from_date}' > from_date and '{from_date}' < to_date) or
				('{from_date}' = from_date and '{to_date}' = to_date))""".format(from_date=self.from_date, to_date=self.to_date)
		
		tax_rule = frappe.db.sql("select name, priority \
			from `tabTax Rule` where {0} and name != '{1}'".format(conds, self.name), as_dict=1) 
		
		if tax_rule:
			if tax_rule[0].priority == self.priority:
				frappe.throw(_("Tax Rule Conflicts with {0}".format(tax_rule[0].name)))