# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import json
from six import iteritems
from frappe.utils import flt, getdate, cstr
from erpnext.regional.india import state_numbers

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
						"iamt": 0,
						"camt": 0,
						"samt": 0,
						"csamt": 0
					},
					{
						"samt": 0,
						"csamt": 0,
						"ty": "OTH",
						"camt": 0,
						"iamt": 0
					}
				],
				"itc_rev": [
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

		self.gst_details = self.get_company_gst_details()
		self.report_dict["gstin"] = self.gst_details.get("gstin")
		self.report_dict["ret_period"] = get_period(self.month, self.year)
		self.month_no = get_period(self.month)
		self.account_heads = self.get_account_heads()

		outward_supply_tax_amounts = self.get_tax_amounts("Sales Invoice")
		inward_supply_tax_amounts = self.get_tax_amounts("Purchase Invoice", reverse_charge="Y")
		itc_details = self.get_itc_details()

		self.prepare_data("Sales Invoice", outward_supply_tax_amounts, "sup_details", "osup_det", ["Registered Regular"])
		self.prepare_data("Sales Invoice", outward_supply_tax_amounts, "sup_details", "osup_zero", ["SEZ", "Deemed Export", "Overseas"])
		self.prepare_data("Purchase Invoice", inward_supply_tax_amounts, "sup_details", "isup_rev", ["Unregistered", "Overseas", "Registered Regular"], reverse_charge="Y")
		self.report_dict["sup_details"]["osup_nil_exmp"]["txval"] = flt(self.get_nil_rated_supply_value(), 2)
		self.set_itc_details(itc_details)

		inter_state_supplies = self.get_inter_state_supplies(self.gst_details.get("gst_state_number"))
		inward_nil_exempt = self.get_inward_nil_exempt(self.gst_details.get("gst_state"))
		self.set_inter_state_supply(inter_state_supplies)
		self.set_inward_nil_exempt(inward_nil_exempt)

		self.missing_field_invoices = self.get_missing_field_invoices()

		self.json_output = frappe.as_json(self.report_dict)

	def set_inward_nil_exempt(self, inward_nil_exempt):

		self.report_dict["inward_sup"]["isup_details"][0]["inter"] = flt(inward_nil_exempt.get("gst").get("inter"), 2)
		self.report_dict["inward_sup"]["isup_details"][0]["intra"] = flt(inward_nil_exempt.get("gst").get("intra"), 2)
		self.report_dict["inward_sup"]["isup_details"][1]["inter"] = flt(inward_nil_exempt.get("non_gst").get("inter"), 2)
		self.report_dict["inward_sup"]["isup_details"][1]["intra"] = flt(inward_nil_exempt.get("non_gst").get("intra"), 2)

	def set_itc_details(self, itc_details):

		itc_type_map = {
			'IMPG': 'Import Of Capital Goods',
			'IMPS': 'Import Of Service',
			'ISD': 'Input Service Distributor',
			'OTH': 'All Other ITC'
		}

		net_itc = self.report_dict["itc_elg"]["itc_net"]

		for d in self.report_dict["itc_elg"]["itc_avl"]:

			itc_type = itc_type_map.get(d["ty"])
			gst_category = ["Registered Regular"]

			if d["ty"] == 'ISRC':
				reverse_charge = "Y"
				itc_type = 'All Other ITC'
				gst_category = ['Unregistered', 'Overseas', 'Registered Regular']
			else:
				reverse_charge = "N"

			for account_head in self.account_heads:
				for category in gst_category:
					for key in [['iamt', 'igst_account'], ['camt', 'cgst_account'], ['samt', 'sgst_account'], ['csamt', 'cess_account']]:
						d[key[0]] += flt(itc_details.get((category, itc_type, reverse_charge, account_head.get(key[1])), {}).get("amount"), 2)

			for key in ['iamt', 'camt', 'samt', 'csamt']:
				net_itc[key] += flt(d[key], 2)

		for account_head in self.account_heads:
			itc_inelg = self.report_dict["itc_elg"]["itc_inelg"][1]
			for key in [['iamt', 'igst_account'], ['camt', 'cgst_account'], ['samt', 'sgst_account'], ['csamt', 'cess_account']]:
				itc_inelg[key[0]] = flt(itc_details.get(("Ineligible", "N", account_head.get(key[1])), {}).get("amount"), 2)

	def prepare_data(self, doctype, tax_details, supply_type, supply_category, gst_category_list, reverse_charge="N"):

		account_map = {
			'sgst_account': 'samt',
			'cess_account': 'csamt',
			'cgst_account': 'camt',
			'igst_account': 'iamt'
		}

		txval = 0
		total_taxable_value = self.get_total_taxable_value(doctype, reverse_charge)

		for gst_category in gst_category_list:
			txval += total_taxable_value.get(gst_category,0)
			for account_head in self.account_heads:
				for account_type, account_name in iteritems(account_head):
					if account_map.get(account_type) in self.report_dict.get(supply_type).get(supply_category):
						self.report_dict[supply_type][supply_category][account_map.get(account_type)] += \
							flt(tax_details.get((account_name, gst_category), {}).get("amount"), 2)

		self.report_dict[supply_type][supply_category]["txval"] += flt(txval, 2)

	def set_inter_state_supply(self, inter_state_supply):

		osup_det = self.report_dict["sup_details"]["osup_det"]

		for key, value in iteritems(inter_state_supply):
			if key[0] == "Unregistered":
				self.report_dict["inter_sup"]["unreg_details"].append(value)

			if key[0] == "Registered Composition":
				self.report_dict["inter_sup"]["comp_details"].append(value)

			if key[0] == "UIN Holders":
				self.report_dict["inter_sup"]["uin_details"].append(value)

	def get_total_taxable_value(self, doctype, reverse_charge):

		return frappe._dict(frappe.db.sql("""
			select gst_category, sum(base_net_total) as total
			from `tab{doctype}`
			where docstatus = 1 and month(posting_date) = %s
			and year(posting_date) = %s and reverse_charge = %s
			and company = %s and company_gstin = %s
			group by gst_category
			""" #nosec
			.format(doctype = doctype), (self.month_no, self.year, reverse_charge, self.company, self.gst_details.get("gstin"))))

	def get_itc_details(self):
		itc_amount = frappe.db.sql("""
			select s.gst_category, sum(t.tax_amount_after_discount_amount) as tax_amount, t.account_head, s.eligibility_for_itc, s.reverse_charge
			from `tabPurchase Invoice` s , `tabPurchase Taxes and Charges` t
			where s.docstatus = 1 and t.parent = s.name
			and month(s.posting_date) = %s and year(s.posting_date) = %s and s.company = %s
			and s.company_gstin = %s
			group by t.account_head, s.gst_category, s.eligibility_for_itc
			""",
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")), as_dict=1)

		itc_details = {}

		for d in itc_amount:
			itc_details.setdefault((d.gst_category, d.eligibility_for_itc, d.reverse_charge, d.account_head),{
				"amount": d.tax_amount
			})

		return itc_details

	def get_nil_rated_supply_value(self):

		return frappe.db.sql("""
			select sum(i.base_amount) as total from
			`tabSales Invoice Item` i, `tabSales Invoice` s
			where s.docstatus = 1 and i.parent = s.name and i.is_nil_exempt = 1
			and month(s.posting_date) = %s and year(s.posting_date) = %s
			and s.company = %s and s.company_gstin = %s""",
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")), as_dict=1)[0].total

	def get_inter_state_supplies(self, state_number):
		inter_state_supply_tax = frappe.db.sql(""" select t.account_head, t.tax_amount_after_discount_amount as tax_amount,
			s.name, s.net_total, s.place_of_supply, s.gst_category from `tabSales Invoice` s, `tabSales Taxes and Charges` t
			where t.parent = s.name and s.docstatus = 1 and month(s.posting_date) = %s and year(s.posting_date) = %s
			and s.company = %s and s.company_gstin = %s and s.gst_category in ('Unregistered', 'Registered Composition', 'UIN Holders')
			and ifnull(s.name, '') != ''
		""", (self.month_no, self.year, self.company, self.gst_details.get("gstin")), as_dict=1)

		inter_state_supply_tax_mapping = {}
		inter_state_supply_details = {}

		for d in inter_state_supply_tax:
			inter_state_supply_tax_mapping.setdefault(cstr(d.name), {
				'place_of_supply': d.place_of_supply,
				'taxable_value': d.net_total,
				'gst_category': d.gst_category,
				'camt': 0.0,
				'samt': 0.0,
				'iamt': 0.0,
				'csamt': 0.0
			})

			if d.account_head in [a.cgst_account for a in self.account_heads]:
				inter_state_supply_tax_mapping[cstr(d.name)]['camt'] += d.tax_amount

			if d.account_head in [a.sgst_account for a in self.account_heads]:
				inter_state_supply_tax_mapping[cstr(d.name)]['samt'] += d.tax_amount

			if d.account_head in [a.igst_account for a in self.account_heads]:
				inter_state_supply_tax_mapping[cstr(d.name)]['iamt'] += d.tax_amount

			if d.account_head in [a.cess_account for a in self.account_heads]:
				inter_state_supply_tax_mapping[cstr(d.name)]['csamt'] += d.tax_amount

		for key, value in iteritems(inter_state_supply_tax_mapping):
			if value.get('place_of_supply'):
				osup_det = self.report_dict["sup_details"]["osup_det"]
				osup_det["txval"] = flt(osup_det["txval"] + value['taxable_value'], 2)
				osup_det["iamt"] = flt(osup_det["iamt"] + value['iamt'], 2)
				osup_det["camt"] = flt(osup_det["camt"] + value['camt'], 2)
				osup_det["samt"] = flt(osup_det["samt"] + value['samt'], 2)
				osup_det["csamt"] = flt(osup_det["csamt"] + value['csamt'], 2)

				if state_number != value.get('place_of_supply').split("-")[0]:
					inter_state_supply_details.setdefault((value.get('gst_category'), value.get('place_of_supply')), {
						"txval": 0.0,
						"pos": value.get('place_of_supply').split("-")[0],
						"iamt": 0.0
					})

					inter_state_supply_details[(value.get('gst_category'), value.get('place_of_supply'))]['txval'] += value['taxable_value']
					inter_state_supply_details[(value.get('gst_category'), value.get('place_of_supply'))]['iamt'] += value['iamt']

		return inter_state_supply_details

	def get_inward_nil_exempt(self, state):

		inward_nil_exempt = frappe.db.sql(""" select p.place_of_supply, sum(i.base_amount) as base_amount,
			i.is_nil_exempt, i.is_non_gst from `tabPurchase Invoice` p , `tabPurchase Invoice Item` i
			where p.docstatus = 1 and p.name = i.parent
			and i.is_nil_exempt = 1 or i.is_non_gst = 1 and
			month(p.posting_date) = %s and year(p.posting_date) = %s and p.company = %s and p.company_gstin = %s
			group by p.place_of_supply """, (self.month_no, self.year, self.company, self.gst_details.get("gstin")), as_dict=1)

		inward_nil_exempt_details = {
			"gst": {
				"intra": 0.0,
				"inter": 0.0
			},
			"non_gst": {
				"intra": 0.0,
				"inter": 0.0
			}
		}

		for d in inward_nil_exempt:
			if d.place_of_supply:
				if d.is_nil_exempt == 1 and state == d.place_of_supply.split("-")[1]:
					inward_nil_exempt_details["gst"]["intra"] += d.base_amount
				elif d.is_nil_exempt == 1 and state != d.place_of_supply.split("-")[1]:
					inward_nil_exempt_details["gst"]["inter"] += d.base_amount
				elif d.is_non_gst == 1 and state == d.place_of_supply.split("-")[1]:
					inward_nil_exempt_details["non_gst"]["intra"] += d.base_amount
				elif d.is_non_gst == 1 and state != d.place_of_supply.split("-")[1]:
					inward_nil_exempt_details["non_gst"]["inter"] += d.base_amount

		return inward_nil_exempt_details

	def get_tax_amounts(self, doctype, reverse_charge="N"):

		if doctype == "Sales Invoice":
			tax_template = 'Sales Taxes and Charges'
		elif doctype == "Purchase Invoice":
			tax_template = 'Purchase Taxes and Charges'

		tax_amounts = frappe.db.sql("""
			select s.gst_category, sum(t.tax_amount_after_discount_amount) as tax_amount, t.account_head
			from `tab{doctype}` s , `tab{template}` t
			where s.docstatus = 1 and t.parent = s.name and s.reverse_charge = %s
			and month(s.posting_date) = %s and year(s.posting_date) = %s and s.company = %s
			and s.company_gstin = %s
			group by t.account_head, s.gst_category
			""" #nosec
			.format(doctype=doctype, template=tax_template),
			(reverse_charge, self.month_no, self.year, self.company, self.gst_details.get("gstin")), as_dict=1)

		tax_details = {}

		for d in tax_amounts:
			tax_details.setdefault(
				(d.account_head,d.gst_category),{
					"amount": d.get("tax_amount"),
				}
			)

		return tax_details

	def get_company_gst_details(self):

		gst_details =  frappe.get_all("Address",
			fields=["gstin", "gst_state", "gst_state_number"],
			filters={
				"name":self.company_address
			})

		if gst_details:
			return gst_details[0]
		else:
			frappe.throw(_("Please enter GSTIN and state for the Company Address {0}".format(self.company_address)))

	def get_account_heads(self):

		account_heads =  frappe.get_all("GST Account",
			fields=["cgst_account", "sgst_account", "igst_account", "cess_account"],
			filters={
				"company":self.company
			})

		if account_heads:
			return account_heads
		else:
			frappe.throw(_("Please set account heads in GST Settings for Compnay {0}".format(self.company)))

	def get_missing_field_invoices(self):

		missing_field_invoices = []

		for doctype in ["Sales Invoice", "Purchase Invoice"]:

			if doctype == "Sales Invoice":
				party_type = 'Customer'
				party = 'customer'
			else:
				party_type = 'Supplier'
				party = 'supplier'

			docnames = frappe.db.sql("""
				select t1.name from `tab{doctype}` t1, `tab{party_type}` t2
				where t1.docstatus = 1 and month(t1.posting_date) = %s and year(t1.posting_date) = %s
				and t1.company = %s and t1.place_of_supply IS NULL and t1.{party} = t2.name and
				t2.gst_category != 'Overseas'
			""".format(doctype = doctype, party_type = party_type, party=party), (self.month_no, self.year, self.company), as_dict=1) #nosec

			for d in docnames:
				missing_field_invoices.append(d.name)

		return ",".join(missing_field_invoices)

def get_state_code(state):

	state_code = state_numbers.get(state)

	return state_code

def get_period(month, year=None):

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

	if year:
		return str(month_no).zfill(2) + str(year)
	else:
		return month_no


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
