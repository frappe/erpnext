# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import os

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt
from six import iteritems

from erpnext.regional.india import state_numbers


class GSTR3BReport(Document):
	def validate(self):
		self.get_data()

	def get_data(self):
		self.report_dict = json.loads(get_json("gstr_3b_report_template"))

		self.gst_details = self.get_company_gst_details()
		self.report_dict["gstin"] = self.gst_details.get("gstin")
		self.report_dict["ret_period"] = get_period(self.month, self.year)
		self.month_no = get_period(self.month)
		self.account_heads = self.get_account_heads()

		self.get_outward_supply_details("Sales Invoice")
		self.set_outward_taxable_supplies()

		self.get_outward_supply_details("Purchase Invoice", reverse_charge=True)
		self.set_supplies_liable_to_reverse_charge()

		itc_details = self.get_itc_details()
		self.set_itc_details(itc_details)
		self.get_itc_reversal_entries()
		inward_nil_exempt = self.get_inward_nil_exempt(self.gst_details.get("gst_state"))
		self.set_inward_nil_exempt(inward_nil_exempt)

		self.missing_field_invoices = self.get_missing_field_invoices()
		self.json_output = frappe.as_json(self.report_dict)

	def set_inward_nil_exempt(self, inward_nil_exempt):
		self.report_dict["inward_sup"]["isup_details"][0]["inter"] = flt(
			inward_nil_exempt.get("gst").get("inter"), 2
		)
		self.report_dict["inward_sup"]["isup_details"][0]["intra"] = flt(
			inward_nil_exempt.get("gst").get("intra"), 2
		)
		self.report_dict["inward_sup"]["isup_details"][1]["inter"] = flt(
			inward_nil_exempt.get("non_gst").get("inter"), 2
		)
		self.report_dict["inward_sup"]["isup_details"][1]["intra"] = flt(
			inward_nil_exempt.get("non_gst").get("intra"), 2
		)

	def set_itc_details(self, itc_details):
		itc_eligible_type_map = {
			"IMPG": "Import Of Capital Goods",
			"IMPS": "Import Of Service",
			"ISRC": "ITC on Reverse Charge",
			"ISD": "Input Service Distributor",
			"OTH": "All Other ITC",
		}

		itc_ineligible_map = {"RUL": "Ineligible As Per Section 17(5)", "OTH": "Ineligible Others"}

		net_itc = self.report_dict["itc_elg"]["itc_net"]

		for d in self.report_dict["itc_elg"]["itc_avl"]:
			itc_type = itc_eligible_type_map.get(d["ty"])
			for key in ["iamt", "camt", "samt", "csamt"]:
				d[key] = flt(itc_details.get(itc_type, {}).get(key))
				net_itc[key] += flt(d[key], 2)

		for d in self.report_dict["itc_elg"]["itc_inelg"]:
			itc_type = itc_ineligible_map.get(d["ty"])
			for key in ["iamt", "camt", "samt", "csamt"]:
				d[key] = flt(itc_details.get(itc_type, {}).get(key))

	def get_itc_reversal_entries(self):
		reversal_entries = frappe.db.sql(
			"""
			SELECT ja.account, j.reversal_type, sum(credit_in_account_currency) as amount
			FROM `tabJournal Entry` j, `tabJournal Entry Account` ja
			where j.docstatus = 1
			and j.is_opening = 'No'
			and ja.parent = j.name
			and j.voucher_type = 'Reversal Of ITC'
			and month(j.posting_date) = %s and year(j.posting_date) = %s
			and j.company = %s and j.company_gstin = %s
			GROUP BY ja.account, j.reversal_type""",
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")),
			as_dict=1,
		)

		net_itc = self.report_dict["itc_elg"]["itc_net"]

		for entry in reversal_entries:
			if entry.reversal_type == "As per rules 42 & 43 of CGST Rules":
				index = 0
			else:
				index = 1

			for key in ["camt", "samt", "iamt", "csamt"]:
				if entry.account in self.account_heads.get(key):
					self.report_dict["itc_elg"]["itc_rev"][index][key] += flt(entry.amount)
					net_itc[key] -= flt(entry.amount)

	def get_itc_details(self):
		itc_amounts = frappe.db.sql(
			"""
			SELECT eligibility_for_itc, sum(itc_integrated_tax) as itc_integrated_tax,
			sum(itc_central_tax) as itc_central_tax,
			sum(itc_state_tax) as itc_state_tax,
			sum(itc_cess_amount) as itc_cess_amount
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1
			and is_opening = 'No'
			and month(posting_date) = %s and year(posting_date) = %s and company = %s
			and company_gstin = %s
			GROUP BY eligibility_for_itc
		""",
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")),
			as_dict=1,
		)

		itc_details = {}
		for d in itc_amounts:
			itc_details.setdefault(
				d.eligibility_for_itc,
				{
					"iamt": d.itc_integrated_tax,
					"camt": d.itc_central_tax,
					"samt": d.itc_state_tax,
					"csamt": d.itc_cess_amount,
				},
			)

		return itc_details

	def get_inward_nil_exempt(self, state):
		inward_nil_exempt = frappe.db.sql(
			"""
			SELECT p.name, p.place_of_supply, p.supplier_address, p.gst_category,
			i.base_amount, i.is_nil_exempt, i.is_non_gst
			FROM `tabPurchase Invoice` p , `tabPurchase Invoice Item` i
			WHERE p.docstatus = 1 and p.name = i.parent
			and p.is_opening = 'No'
			and (i.is_nil_exempt = 1 or i.is_non_gst = 1 or p.gst_category = 'Registered Composition') and
			month(p.posting_date) = %s and year(p.posting_date) = %s
			and p.company = %s and p.company_gstin = %s
		""",
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")),
			as_dict=1,
		)

		inward_nil_exempt_details = {
			"gst": {"intra": 0.0, "inter": 0.0},
			"non_gst": {"intra": 0.0, "inter": 0.0},
		}

		address_state_map = get_address_state_map()

		for d in inward_nil_exempt:
			if not d.place_of_supply:
				d.place_of_supply = "00-" + cstr(state)

			supplier_state = address_state_map.get(d.supplier_address) or state

			if (d.is_nil_exempt == 1 or d.get("gst_category") == "Registered Composition") and cstr(
				supplier_state
			) == cstr(d.place_of_supply.split("-")[1]):
				inward_nil_exempt_details["gst"]["intra"] += d.base_amount
			elif (d.is_nil_exempt == 1 or d.get("gst_category") == "Registered Composition") and cstr(
				supplier_state
			) != cstr(d.place_of_supply.split("-")[1]):
				inward_nil_exempt_details["gst"]["inter"] += d.base_amount
			elif d.is_non_gst == 1 and cstr(supplier_state) == cstr(d.place_of_supply.split("-")[1]):
				inward_nil_exempt_details["non_gst"]["intra"] += d.base_amount
			elif d.is_non_gst == 1 and cstr(supplier_state) != cstr(d.place_of_supply.split("-")[1]):
				inward_nil_exempt_details["non_gst"]["inter"] += d.base_amount

		return inward_nil_exempt_details

	def get_outward_supply_details(self, doctype, reverse_charge=None):
		self.get_outward_tax_invoices(doctype, reverse_charge=reverse_charge)
		self.get_outward_items(doctype)
		self.get_outward_tax_details(doctype)

	def get_outward_tax_invoices(self, doctype, reverse_charge=None):
		self.invoices = []
		self.invoice_detail_map = {}
		condition = ""

		if reverse_charge:
			condition += "AND reverse_charge = 'Y'"

		invoice_details = frappe.db.sql(
			"""
			SELECT
				name, gst_category, export_type, place_of_supply
			FROM
				`tab{doctype}`
			WHERE
				docstatus = 1
				AND month(posting_date) = %s
				AND year(posting_date) = %s
				AND company = %s
				AND company_gstin = %s
				AND is_opening = 'No'
				{reverse_charge}
			ORDER BY name
		""".format(
				doctype=doctype, reverse_charge=condition
			),
			(self.month_no, self.year, self.company, self.gst_details.get("gstin")),
			as_dict=1,
		)

		for d in invoice_details:
			self.invoice_detail_map.setdefault(d.name, d)
			self.invoices.append(d.name)

	def get_outward_items(self, doctype):
		self.invoice_items = frappe._dict()
		self.is_nil_exempt = []
		self.is_non_gst = []

		if self.get("invoices"):
			item_details = frappe.db.sql(
				"""
				SELECT
					item_code, parent, taxable_value, base_net_amount, item_tax_rate,
					is_nil_exempt, is_non_gst
				FROM
					`tab%s Item`
				WHERE parent in (%s)
			"""
				% (doctype, ", ".join(["%s"] * len(self.invoices))),
				tuple(self.invoices),
				as_dict=1,
			)

			for d in item_details:
				self.invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, 0.0)
				self.invoice_items[d.parent][d.item_code] += d.get("taxable_value", 0) or d.get(
					"base_net_amount", 0
				)

				if d.is_nil_exempt and d.item_code not in self.is_nil_exempt:
					self.is_nil_exempt.append(d.item_code)

				if d.is_non_gst and d.item_code not in self.is_non_gst:
					self.is_non_gst.append(d.item_code)

	def get_outward_tax_details(self, doctype):
		if doctype == "Sales Invoice":
			tax_template = "Sales Taxes and Charges"
		elif doctype == "Purchase Invoice":
			tax_template = "Purchase Taxes and Charges"

		self.items_based_on_tax_rate = {}
		self.invoice_cess = frappe._dict()
		self.cgst_sgst_invoices = []

		if self.get("invoices"):
			tax_details = frappe.db.sql(
				"""
				SELECT
					parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
				FROM `tab%s`
				WHERE
					parenttype = %s and docstatus = 1
					and parent in (%s)
				ORDER BY account_head
			"""
				% (tax_template, "%s", ", ".join(["%s"] * len(self.invoices))),
				tuple([doctype] + list(self.invoices)),
			)

			for parent, account, item_wise_tax_detail, tax_amount in tax_details:
				if account in self.account_heads.get("csamt"):
					self.invoice_cess.setdefault(parent, tax_amount)
				else:
					if item_wise_tax_detail:
						try:
							item_wise_tax_detail = json.loads(item_wise_tax_detail)
							cgst_or_sgst = False
							if account in self.account_heads.get("camt") or account in self.account_heads.get("samt"):
								cgst_or_sgst = True

							for item_code, tax_amounts in item_wise_tax_detail.items():
								if not (
									cgst_or_sgst
									or account in self.account_heads.get("iamt")
									or (item_code in self.is_non_gst + self.is_nil_exempt)
								):
									continue

								tax_rate = tax_amounts[0]
								if tax_rate:
									if cgst_or_sgst:
										tax_rate *= 2
										if parent not in self.cgst_sgst_invoices:
											self.cgst_sgst_invoices.append(parent)

									rate_based_dict = self.items_based_on_tax_rate.setdefault(parent, {}).setdefault(
										tax_rate, []
									)
									if item_code not in rate_based_dict:
										rate_based_dict.append(item_code)
						except ValueError:
							continue

		if self.get("invoice_items"):
			# Build itemised tax for export invoices, nil and exempted where tax table is blank
			for invoice, items in iteritems(self.invoice_items):
				if (
					invoice not in self.items_based_on_tax_rate
					and self.invoice_detail_map.get(invoice, {}).get("export_type") == "Without Payment of Tax"
					and self.invoice_detail_map.get(invoice, {}).get("gst_category") == "Overseas"
				):
					self.items_based_on_tax_rate.setdefault(invoice, {}).setdefault(0, items.keys())
				else:
					for item in items.keys():
						if (
							item in self.is_nil_exempt + self.is_non_gst
							and item not in self.items_based_on_tax_rate.get(invoice, {}).get(0, [])
						):
							self.items_based_on_tax_rate.setdefault(invoice, {}).setdefault(0, [])
							self.items_based_on_tax_rate[invoice][0].append(item)

	def set_outward_taxable_supplies(self):
		inter_state_supply_details = {}
		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			gst_category = self.invoice_detail_map.get(inv, {}).get("gst_category")
			place_of_supply = (
				self.invoice_detail_map.get(inv, {}).get("place_of_supply") or "00-Other Territory"
			)
			export_type = self.invoice_detail_map.get(inv, {}).get("export_type")

			for rate, items in items_based_on_rate.items():
				for item_code, taxable_value in self.invoice_items.get(inv).items():
					if item_code in items:
						if item_code in self.is_nil_exempt:
							self.report_dict["sup_details"]["osup_nil_exmp"]["txval"] += taxable_value
						elif item_code in self.is_non_gst:
							self.report_dict["sup_details"]["osup_nongst"]["txval"] += taxable_value
						elif rate == 0 or (gst_category == "Overseas" and export_type == "Without Payment of Tax"):
							self.report_dict["sup_details"]["osup_zero"]["txval"] += taxable_value
						else:
							if inv in self.cgst_sgst_invoices:
								tax_rate = rate / 2
								self.report_dict["sup_details"]["osup_det"]["camt"] += taxable_value * tax_rate / 100
								self.report_dict["sup_details"]["osup_det"]["samt"] += taxable_value * tax_rate / 100
								self.report_dict["sup_details"]["osup_det"]["txval"] += taxable_value
							else:
								self.report_dict["sup_details"]["osup_det"]["iamt"] += taxable_value * rate / 100
								self.report_dict["sup_details"]["osup_det"]["txval"] += taxable_value
								if (
									gst_category in ["Unregistered", "Registered Composition", "UIN Holders"]
									and self.gst_details.get("gst_state") != place_of_supply.split("-")[1]
								):
									inter_state_supply_details.setdefault(
										(gst_category, place_of_supply),
										{"txval": 0.0, "pos": place_of_supply.split("-")[0], "iamt": 0.0},
									)
									inter_state_supply_details[(gst_category, place_of_supply)]["txval"] += taxable_value
									inter_state_supply_details[(gst_category, place_of_supply)]["iamt"] += (
										taxable_value * rate / 100
									)

			if self.invoice_cess.get(inv):
				self.report_dict["sup_details"]["osup_det"]["csamt"] += flt(self.invoice_cess.get(inv), 2)

		self.set_inter_state_supply(inter_state_supply_details)

	def set_supplies_liable_to_reverse_charge(self):
		for inv, items_based_on_rate in self.items_based_on_tax_rate.items():
			for rate, items in items_based_on_rate.items():
				for item_code, taxable_value in self.invoice_items.get(inv).items():
					if item_code in items:
						if inv in self.cgst_sgst_invoices:
							tax_rate = rate / 2
							self.report_dict["sup_details"]["isup_rev"]["camt"] += taxable_value * tax_rate / 100
							self.report_dict["sup_details"]["isup_rev"]["samt"] += taxable_value * tax_rate / 100
							self.report_dict["sup_details"]["isup_rev"]["txval"] += taxable_value
						else:
							self.report_dict["sup_details"]["isup_rev"]["iamt"] += taxable_value * rate / 100
							self.report_dict["sup_details"]["isup_rev"]["txval"] += taxable_value

	def set_inter_state_supply(self, inter_state_supply):
		for key, value in iteritems(inter_state_supply):
			if key[0] == "Unregistered":
				self.report_dict["inter_sup"]["unreg_details"].append(value)

			if key[0] == "Registered Composition":
				self.report_dict["inter_sup"]["comp_details"].append(value)

			if key[0] == "UIN Holders":
				self.report_dict["inter_sup"]["uin_details"].append(value)

	def get_company_gst_details(self):
		gst_details = frappe.get_all(
			"Address",
			fields=["gstin", "gst_state", "gst_state_number"],
			filters={"name": self.company_address},
		)

		if gst_details:
			return gst_details[0]
		else:
			frappe.throw(
				_("Please enter GSTIN and state for the Company Address {0}").format(self.company_address)
			)

	def get_account_heads(self):
		account_map = {
			"sgst_account": "samt",
			"cess_account": "csamt",
			"cgst_account": "camt",
			"igst_account": "iamt",
		}

		account_heads = {}
		gst_settings_accounts = frappe.get_all(
			"GST Account",
			filters={"company": self.company, "is_reverse_charge_account": 0},
			fields=["cgst_account", "sgst_account", "igst_account", "cess_account"],
		)

		if not gst_settings_accounts:
			frappe.throw(_("Please set GST Accounts in GST Settings"))

		for d in gst_settings_accounts:
			for acc, val in d.items():
				account_heads.setdefault(account_map.get(acc), []).append(val)

		return account_heads

	def get_missing_field_invoices(self):
		missing_field_invoices = []

		for doctype in ["Sales Invoice", "Purchase Invoice"]:

			if doctype == "Sales Invoice":
				party_type = "Customer"
				party = "customer"
			else:
				party_type = "Supplier"
				party = "supplier"

			docnames = frappe.db.sql(
				"""
				SELECT t1.name FROM `tab{doctype}` t1, `tab{party_type}` t2
				WHERE t1.docstatus = 1 and t1.is_opening = 'No'
				and month(t1.posting_date) = %s and year(t1.posting_date) = %s
				and t1.company = %s and t1.place_of_supply IS NULL and t1.{party} = t2.name and
				t2.gst_category != 'Overseas'
			""".format(
					doctype=doctype, party_type=party_type, party=party
				),
				(self.month_no, self.year, self.company),
				as_dict=1,
			)  # nosec

			for d in docnames:
				missing_field_invoices.append(d.name)

		return ",".join(missing_field_invoices)


def get_address_state_map():
	return frappe._dict(frappe.get_all("Address", fields=["name", "gst_state"], as_list=1))


def get_json(template):
	file_path = os.path.join(os.path.dirname(__file__), "{template}.json".format(template=template))
	with open(file_path, "r") as f:
		return cstr(f.read())


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
		"December": 12,
	}.get(month)

	if year:
		return str(month_no).zfill(2) + str(year)
	else:
		return month_no


@frappe.whitelist()
def view_report(name):
	json_data = frappe.get_value("GSTR 3B Report", name, "json_output")
	return json.loads(json_data)


@frappe.whitelist()
def make_json(name):
	json_data = frappe.get_value("GSTR 3B Report", name, "json_output")
	file_name = "GST3B.json"
	frappe.local.response.filename = file_name
	frappe.local.response.filecontent = json_data
	frappe.local.response.type = "download"
