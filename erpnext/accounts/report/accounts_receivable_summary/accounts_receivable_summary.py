# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		return self.get_columns(party_naming_by), self.get_data(party_naming_by, args)

	def get_columns(self, party_naming_by):
		columns = [_("Customer") + ":Link/Customer:200"]

		if party_naming_by == "Naming Series":
			columns += ["Customer Name::110"]

		columns += [_("Total Invoiced Amount") + ":Currency:100",
			_("Total Paid Amount") + ":Currency:100", _("Total Outstanding Amount") + ":Currency:100",
			"0-" + self.filters.range1 + ":Currency:100",
			self.filters.range1 + "-" + self.filters.range2 + ":Currency:100", 
			self.filters.range2 + "-" + self.filters.range3 + ":Currency:100", 
			self.filters.range3 + _("-Above") + ":Currency:100",
			_("Territory") + ":Link/Territory:80"
		]

		return columns

	def get_data(self, party_naming_by, args):
		data = []
		prev_columns, prev_data = ReceivablePayableReport(self.filters).run(args)
		total_amount_dict = frappe._dict()

		key_list = ["posting_date", "customer"]

		if party_naming_by == "Naming Series":
			key_list += ["customer_name"]

		key_list += ["voucher_type", "voucher_no", "due_date", "invoiced_amt", "paid_amt", 
		"outstanding_amt", "age", "range1", "range2", "range3", "range4", "territory", "remarks"]

		data_dict = self.make_data_dict(key_list, prev_data)

		for d in data_dict:
			if d["customer"] in total_amount_dict:
				customer_key = total_amount_dict[d.customer]
				customer_key["total_invoiced_amt"] += d.get("invoiced_amt")
				customer_key["total_paid_amt"] += d.get("paid_amt")
				customer_key["total_outstanding_amt"]+= d.get("outstanding_amt")
				customer_key["total_range1"] += d.get("range1")
				customer_key["total_range2"] += d.get("range2")
				customer_key["total_range3"] += d.get("range3")
				customer_key["total_range4"] += d.get("range4")
			else:
				total_amount_dict.setdefault(d.get("customer"), {}).update({
					"total_invoiced_amt": d.get("invoiced_amt"),
					"total_paid_amt": d.get("paid_amt"),
					"total_outstanding_amt": d.get("outstanding_amt"),
					"total_range1": d.get("range1"),
					"total_range2": d.get("range2"),
					"total_range3": d.get("range3"),
					"total_range4": d.get("range4")
					})

		for i in total_amount_dict:
			row = [i]

			if party_naming_by == "Naming Series":
				row += [self.get_party_name("Customer", i)]

			row += [total_amount_dict[i]["total_invoiced_amt"], total_amount_dict[i]["total_paid_amt"], 
				total_amount_dict[i]["total_outstanding_amt"], total_amount_dict[i]["total_range1"],
				total_amount_dict[i]["total_range2"], total_amount_dict[i]["total_range3"], 
				total_amount_dict[i]["total_range4"], self.get_territory(i)]

			data.append(row)

		return data

	def make_data_dict(self, key_list, data):
		make_data_dict = []
		for d in data:
			make_data_dict.append(frappe._dict(zip(key_list, d)))

		return make_data_dict

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"dr_or_cr": "debit",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)
