# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from six import iteritems
from frappe.utils import flt, getdate

class GSTR3BReport(Document):
	def before_save(self):
		self.get_data()

	def get_data(self):
		self.report_dict = {
			"gstin": "",
			"ret_period": "",
			"inward_sup": {
				"isup_details": [
					{
						"ty": "GST",
						"intra": 0,
						"inter": 0
					},
					{
						"ty": "NONGST",
						"inter": 0,
						"intra": 0
					}
				]
			},
			"sup_details": {
				"osup_zero": {
					"csamt": 0,
					"txval": 0,
					"iamt": 0
				},
				"osup_nil_exmp": {
					"txval": 0
				},
				"osup_det": {
					"samt": 0,
					"csamt": 0,
					"txval": 0,
					"camt": 0,
					"iamt": 0
				},
				"isup_rev": {
					"samt": 0,
					"csamt": 0,
					"txval": 0,
					"camt": 0,
					"iamt": 0
				},
				"osup_nongst": {
					"txval": 0,
				}
			},
			"inter_sup": {
				"unreg_details": [],
				"comp_details": [],
				"uin_details": []
			},
			"itc_elg": {
				"itc_avl": [
					{
						"csamt": 0,
						"samt": 0,
						"ty": "IMPG",
						"camt": 0,
						"iamt": 0
					},
					{
						"csamt": 0,
						"samt": 0,
						"ty": "IMPS",
						"camt": 0,
						"iamt": 0
					},
					{
						"samt": 0,
						"csamt": 0,
						"ty": "ISRC",
						"camt": 0,
						"iamt": 0
					},
					{
						"ty": "ISD",
						"iamt": 1,
						"camt": 1,
						"samt": 1,
						"csamt": 1
					},
					{
						"samt": 0,
						"csamt": 0,
						"ty": "OTH",
						"camt": 0,
						"iamt": 0
					}
				],
				"itc_net": {
					"samt": 0,
					"csamt": 0,
					"camt": 0,
					"iamt": 0
				},
				"itc_inelg": [
					{
						"ty": "RUL",
						"iamt": 0,
						"camt": 0,
						"samt": 0,
						"csamt": 0
					},
					{
						"ty": "OTH",
						"iamt": 0,
						"camt": 0,
						"samt": 0,
						"csamt": 0
					}
				]
			}
		}

		gst_details = get_company_gst_details(self.company_address)
		self.report_dict["gstin"] = gst_details.get("gstin")
		self.report_dict["ret_period"] = get_period(self.month, with_year=True)

		self.account_heads = get_account_heads(self.company)

		outward_supply_tax_amounts = get_tax_amounts("Sales Invoice", self.month)
		inward_supply_tax_amounts = get_tax_amounts("Purchase Invoice", self.month, reverse_charge="Y")
		itc_details = get_itc_details()

		self.prepare_data("Sales Invoice", outward_supply_tax_amounts, "sup_details", "osup_det", ["Registered Regular"])
		self.prepare_data("Sales Invoice", outward_supply_tax_amounts, "sup_details", "osup_zero", ["SEZ", "Deemed Export", "Overseas"])
		self.prepare_data("Purchase Invoice", inward_supply_tax_amounts, "sup_details", "isup_rev", ["Registered Regular"], reverse_charge="Y")
		self.report_dict["sup_details"]["osup_nil_exmp"]["txval"] = get_nil_rated_supply_value()
		self.set_itc_details(itc_details)


		self.json_output = frappe.as_json(self.report_dict)

	def set_itc_details(self, itc_details):

		itc_type_map = {
			'IMPG': 'Import Of Capital Goods',
			'IMPS': 'Import Of Service',
			'ISD': 'Input Service Distributor',
			'OTH': 'Others'
		}

		for d in self.report_dict["itc_elg"]["itc_avl"]:
			d["iamt"] = flt(itc_details.get(itc_type_map.get(d["ty"]), {}).get("itc_iamt"))
			d["camt"] = flt(itc_details.get(itc_type_map.get(d["ty"]), {}).get("itc_camt"))
			d["samt"] = flt(itc_details.get(itc_type_map.get(d["ty"]), {}).get("itc_samt"))
			d["csamt"] = flt(itc_details.get(itc_type_map.get(d["ty"]), {}).get("itc_csamt"))


	def prepare_data(self, doctype, tax_details, supply_type, supply_category, gst_category_list, reverse_charge="N"):

		account_map = {
			'sgst_account': 'samt',
			'cess_account': 'csamt',
			'cgst_account': 'camt',
			'igst_account': 'iamt'
		}

		total_taxable_value = get_total_taxable_value(doctype, self.month, reverse_charge)

		for gst_category in gst_category_list:
			for k, v in iteritems(account_map):
				if v in self.report_dict.get(supply_type).get(supply_category):
					self.report_dict[supply_type][supply_category][v] += \
						flt(tax_details.get((self.account_heads.get(k), gst_category), {}).get("amount"))

			self.report_dict[supply_type][supply_category]["txval"] += \
				flt(total_taxable_value.get(gst_category, 0))

def get_total_taxable_value(doctype, month, reverse_charge):

	month_no = get_period(month)

	return frappe._dict(frappe.db.sql("""
		select gst_category, sum(grand_total) as total
		from `tab{doctype}`
		where docstatus = 1 and month(posting_date) = %s and reverse_charge = %s
		group by gst_category
		"""
		.format(doctype = doctype), (month_no, reverse_charge)))

def get_itc_details(reverse_charge='N'):

	itc_amount = frappe.db.sql("""
		select sum(itc_integrated_tax) as itc_iamt, sum(itc_central_tax) as itc_camt,
		sum(itc_state_tax) as itc_samt, sum(itc_cess_amount) as itc_csamt, eligibility_for_itc,
		reverse_charge
		from `tabPurchase Invoice`
		where docstatus = 1
		group by eligibility_for_itc, reverse_charge""", as_dict=1)

	# itc_amount = frappe.get_all('Purchase Invoice',
	# 	fields = ["sum(itc_integrated_tax) as itc_iamt",
	# 		"sum(itc_central_tax) as itc_camt",
	# 		"sum(itc_state_tax) as itc_samt",
	# 		"sum(itc_cess_amount) as itc_csamt",
	# 		"eligibility_for_itc"
	# 	],
	# 	filters = {
	# 		"docstatus":1,
	# 	},
	# 	group_by = ['eligibility_for_itc', 'reverse_charge'])

	itc_details = {}

	for d in itc_amount:
		itc_details.setdefault((d.eligibility_for_itc, d.reverse_charge),{
			"itc_iamt": d.itc_iamt,
			"itc_camt": d.itc_camt,
			"itc_samt": d.itc_samt,
			"itc_csamt": d.itc_csamt
		})

	return itc_details

def get_nil_rated_supply_value():

	return frappe.db.sql("""
		select sum(base_amount) as total from
		`tabSales Invoice Item` i, `tabSales Invoice` s
		where
		s.docstatus = 1 and
		i.parent = s.name and
		i.item_tax_rate = '{}' and
		s.taxes_and_charges IS NULL""", as_dict=1)[0].total


def get_tax_amounts(doctype, month, reverse_charge="N"):

	month_no = get_period(month)

	if doctype == "Sales Invoice":
		tax_template = 'Sales Taxes and Charges'
	elif doctype == "Purchase Invoice":
		tax_template = 'Purchase Taxes and Charges'

	tax_amounts = frappe.db.sql("""
		select s.gst_category, sum(t.tax_amount) as tax_amount, t.account_head
		from `tab{doctype}` s , `tab{template}` t
		where s.docstatus = 1 and t.parent = s.name and s.reverse_charge = %s and month(s.posting_date) = %s
		group by t.account_head, s.gst_category
		""".format(doctype=doctype, template=tax_template), (reverse_charge, month_no), as_dict=1)

	tax_details = {}

	for d in tax_amounts:
		tax_details.setdefault(
			(d.account_head,d.gst_category),{
				"amount": d.get("tax_amount"),
			}
		)

	return tax_details

def get_period(month, with_year=False):

	month_no = {
		"January": 1,
		"February": 2,
		"March": 3,
		"April": 4,
		"May": 5,
		"June": 6,
		"July": 7,
		"August": 8,
		"September": 9,
		"October": 10,
		"November": 11,
		"December": 12
	}.get(month)

	if with_year:
		return str(month_no).zfill(2) + str(getdate().year)
	else:
		return month_no

def get_company_gst_details(address):

	return frappe.get_all("Address",
		fields=["gstin", "gst_state", "gst_state_number"],
		filters={
			"name":address
		})[0]

def get_account_heads(company):

	return frappe.get_all("GST Account",
		fields=["cgst_account", "sgst_account", "igst_account", "cess_account"],
		filters={
			"company":company
		})[0]


@frappe.whitelist()
def view_report(name):

	json_data = frappe.get_value("GSTR 3B Report", name, 'json_output')
	return json.loads(json_data)

@frappe.whitelist()
def make_json(name):

	json_data = frappe.get_value("GSTR 3B Report", name, 'json_output')
	file_name = "GST3B.json"
	frappe.local.response.filename = file_name
	frappe.local.response.filecontent = json_data
	frappe.local.response.type = "download"
