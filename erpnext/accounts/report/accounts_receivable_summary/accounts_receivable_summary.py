# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		return self.get_columns(party_naming_by, args), self.get_data(party_naming_by, args)

	def get_columns(self, party_naming_by, args):
		columns = [_(args.get("party_type")) + ":Link/" + args.get("party_type") + ":200"]

		if party_naming_by == "Naming Series":
			columns += [ args.get("party_type") + " Name::140"]

		columns += [
			_("Total Invoiced Amt") + ":Currency/currency:140",
			_("Total Paid Amt") + ":Currency/currency:140",
			_("Total Outstanding Amt") + ":Currency/currency:160",
			"0-" + str(self.filters.range1) + ":Currency/currency:100",
			str(self.filters.range1) + "-" + str(self.filters.range2) + ":Currency/currency:100",
			str(self.filters.range2) + "-" + str(self.filters.range3) + ":Currency/currency:100",
			str(self.filters.range3) + _("-Above") + ":Currency/currency:100"]

		if args.get("party_type") == "Customer":
			columns += [
				_("Territory") + ":Link/Territory:80", 
				_("Customer Group") + ":Link/Customer Group:120"
			]
		if args.get("party_type") == "Supplier":
			columns += [_("Supplier Type") + ":Link/Supplier Type:80"]
			
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

		for party, party_dict in partywise_total.items():
			row = [party]

			if party_naming_by == "Naming Series":
				row += [self.get_party_name(args.get("party_type"), party)]

			row += [
				party_dict.invoiced_amt, party_dict.paid_amt, party_dict.outstanding_amt,
				party_dict.range1, party_dict.range2, party_dict.range3, party_dict.range4,
			]

			if args.get("party_type") == "Customer":
				row += [self.get_territory(party), self.get_customer_group(party)]
			if args.get("party_type") == "Supplier":
				row += [self.get_supplier_type(party)]
				
			row.append(party_dict.currency)
			data.append(row)

		return data

	def get_partywise_total(self, party_naming_by, args):
		party_total = frappe._dict()
		for d in self.get_voucherwise_data(party_naming_by, args):
			party_total.setdefault(d.party,
				frappe._dict({
					"invoiced_amt": 0,
					"paid_amt": 0,
					"outstanding_amt": 0,
					"range1": 0,
					"range2": 0,
					"range3": 0,
					"range4": 0
				})
			)
			for k in party_total[d.party].keys():
				party_total[d.party][k] += d.get(k, 0)
				
			party_total[d.party].currency = d.currency

		return party_total

	def get_voucherwise_data(self, party_naming_by, args):
		voucherwise_data = ReceivablePayableReport(self.filters).run(args)[1]

		cols = ["posting_date", "party"]

		if party_naming_by == "Naming Series":
			cols += ["party_name"]

		cols += ["voucher_type", "voucher_no", "due_date"]

		if args.get("party_type") == "Supplier":
			cols += ["bill_no", "bill_date"]

		cols += ["invoiced_amt", "paid_amt",
		"outstanding_amt", "age", "range1", "range2", "range3", "range4", "currency"]

		if args.get("party_type") == "Supplier":
			cols += ["supplier_type", "remarks"]
		if args.get("party_type") == "Customer":
			cols += ["territory", "customer_group", "remarks"]

		return self.make_data_dict(cols, voucherwise_data)

	def make_data_dict(self, cols, data):
		data_dict = []
		for d in data:
			data_dict.append(frappe._dict(zip(cols, d)))

		return data_dict

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)
