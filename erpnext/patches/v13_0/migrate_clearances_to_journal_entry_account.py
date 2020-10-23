# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	affected_transactions = 0
	affected_payments = 0
	new_payments = 0
	frappe.reload_doc("accounts", "doctype", "Journal Entry Account")
	for btname in frappe.db.get_all("Bank Transaction",
					filters = { 'allocated_amount': ('>', 0) }):
		bank_trans = frappe.get_doc("Bank Transaction", btname)
		account = frappe.db.get_value("Bank Account",
			bank_trans.bank_account, "account")
		need_side = "credit" if bank_trans.debit > 0 else "debit"
		to_replace = []
		for payment in bank_trans.payment_entries:
			if payment.payment_document != "Journal Entry":
				continue
			entry = frappe.get_doc("Journal Entry", payment.payment_entry)
			je_total = sum(jea.get(need_side) for jea in entry.accounts if jea.account == account)
			if je_total == payment.allocated_amount:
				# OK, we will plan to replace the Journal
				# Entry payment with payments for all of the
				# Journal Entry Account records for that
				# bank account on the correct side:
				to_replace.append((payment, entry))
			else:
				print(f"Warning: For bank transaction {bank_trans.name}:\n",
					f"keeping Journal Entry payment from {payment.payment_entry} because\n",
					f"it does not match the sum of the Journal Entry Account records for Account {account}."
				)
		if len(to_replace) > 0:
			affected_transactions += 1
		for (oldpay, oldentry) in to_replace:
			affected_payments += 1
			bank_trans.remove(oldpay)
			for jea in oldentry.accounts:
				if jea.account == account and jea.get(need_side) > 0:
					new_payments += 1
					bank_trans.append("payment_entries", dict(
						payment_document = "Journal Entry Account",
						payment_entry = jea.name,
						allocated_amount = jea.get(need_side),
						clearance_date = bank_trans.date
					))
					frappe.db.set_value("Journal Entry Account", jea.name, "clearance_date", bank_trans.date);
					frappe.db.set_value("Journal Entry Account", jea.name, "reconciled_with", bank_trans.name);
		bank_trans.save()
	print(f"Updated {affected_transactions} bank transactions by replacing {affected_payments} Journal Entry payments with {new_payments} Journal Entry Account payments.")

