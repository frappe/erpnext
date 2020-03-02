# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, cint
from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

from six import iteritems

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		self.ageing_range = [cint(r.strip()) for r in self.filters.get('ageing_range', "").split(",") if r]
		self.ageing_range = sorted(list(set(self.ageing_range)))
		self.ageing_column_count = len(self.ageing_range) + 1

		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		return self.get_columns(party_naming_by, args), self.get_data(party_naming_by, args)

	def get_columns(self, party_naming_by, args):
		columns = [
			{
				"fieldname": "party",
				"label": _(args.get("party_type")),
				"fieldtype": "Link",
				"options": args.get("party_type"),
				"width": 200
			}
		]

		if party_naming_by == "Naming Series":
			columns.append(
				{
					"fieldname": "party_name",
					"label": _(args.get("party_type") + " Name"),
					"fieldtype": "Data",
					"width": 140
				}
			)

		invoiced_label = "Total Invoiced Amt"
		paid_label = "Total Paid Amt"
		return_label = "Returned Amount"
		if args.get("party_type") == "Customer":
			return_label = "Credit Note Amt"
		elif args.get("party_type") == "Supplier":
			return_label = "Debit Note Amt"
		elif args.get("party_type") == "Employee":
			invoiced_label = "Total Paid Amt"
			paid_label = "Total Claimed Amt"

		if args.get("party_type") != "Employee":
			columns.append({
				"label": _("Advance Amount"),
				"fieldname": "advance_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 100
			})

		columns += [
			{
				"label": _(invoiced_label),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140
			},
			{
				"label": _(paid_label),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140
			}
		]

		columns += [
			{
				"label": _(return_label),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140
			},
			{
				"label": _("Total Outstanding Amt"),
				"fieldname": "outstanding_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 160
			}
		]

		self.ageing_columns = []
		lower_limit = 0
		for i, upper_limit in enumerate(self.ageing_range):
			self.ageing_columns.append({
				"label": "{0}-{1}".format(lower_limit, upper_limit),
				"fieldname": "range{0}".format(i+1),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			})
			lower_limit = upper_limit + 1

		self.ageing_columns.append({
			"label": "{0}-Above".format(lower_limit),
			"fieldname": "range{0}".format(self.ageing_column_count),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		})

		columns += self.ageing_columns

		if args.get("party_type") == "Customer":
			columns += [{
				"label": _("Territory"),
				"fieldname": "territory",
				"fieldtype": "Link",
				"options": "Territory",
				"width": 80
			},
			{
				"label": _("Customer Group"),
				"fieldname": "customer_group",
				"fieldtype": "Link",
				"options": "Customer Group",
				"width": 80
			},
			{
				"label": _("Sales Person"),
				"fieldtype": "Data",
				"fieldname": "sales_person",
				"width": 120,
			}]

		if args.get("party_type") == "Supplier":
			columns += [{
				"label": _("Supplier Group"),
				"fieldname": "supplier_group",
				"fieldtype": "Link",
				"options": "Supplier Group",
				"width": 80
			}]

		columns.append({
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80
		})

		return columns

	def get_data(self, party_naming_by, args):
		data = []

		partywise_total = self.get_partywise_total(party_naming_by, args)
		if args.get("party_type") != "Employee":
			partywise_advance_amount = get_partywise_advanced_payment_amount(args.get("party_type"),
				self.filters.get("report_date")) or {}
		else:
			partywise_advance_amount = {}

		for party, party_dict in iteritems(partywise_total):
			row = frappe._dict({"party": party})

			if party_naming_by == "Naming Series":
				row["party_name"] = self.get_party_name(args.get("party_type"), party)

			row["advance_amount"] = partywise_advance_amount.get(party, 0)
			row["invoiced_amount"] = party_dict.invoiced_amount
			row["paid_amount"] = party_dict.paid_amount
			row["return_amount"] = party_dict.return_amount
			row["outstanding_amount"] = party_dict.outstanding_amount

			for i in range(self.ageing_column_count):
				row["range{0}".format(i+1)] = party_dict.get("range{0}".format(i+1))

			if args.get("party_type") == "Customer":
				row["territory"] = self.get_territory(party)
				row["customer_group"] = self.get_customer_group(party)
				row["sales_person"] = ", ".join(set(party_dict.sales_person))
			if args.get("party_type") == "Supplier":
				row["supplier_group"] = self.get_supplier_group(party)

			row["currency"] = party_dict.currency
			data.append(row)

		return data

	def get_partywise_total(self, party_naming_by, args):
		party_total = frappe._dict()

		template = frappe._dict({
			"invoiced_amount": 0,
			"paid_amount": 0,
			"return_amount": 0,
			"outstanding_amount": 0,
			"sales_person": []
		})
		for r in range(self.ageing_column_count):
			template['range{0}'.format(r+1)] = 0

		for d in self.get_voucherwise_data(party_naming_by, args):
			party_total.setdefault(d.party, template.copy())
			
			for k in list(party_total[d.party]):
				if k not in ["currency", "sales_person"]:
					party_total[d.party][k] += flt(d.get(k, 0))

			party_total[d.party].currency = d.currency

			if d.sales_person:
				party_total[d.party].sales_person.append(d.sales_person)

		return party_total

	def get_voucherwise_data(self, party_naming_by, args):
		voucherwise_data = ReceivablePayableReport(self.filters).run(args)[1]
		return voucherwise_data

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)
