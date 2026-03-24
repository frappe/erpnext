# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "bank_transaction")

	bank_transaction_fields = frappe.get_meta("Bank Transaction").get_valid_columns()
	bank_transaction = frappe.qb.DocType("Bank Transaction")

	if "debit" in bank_transaction_fields:
		(
			frappe.qb.update(bank_transaction)
			.set(bank_transaction.status, "Reconciled")
			.where(
				(bank_transaction.status == "Settled")
				& (
					(bank_transaction.debit == bank_transaction.allocated_amount)
					| (bank_transaction.credit == bank_transaction.allocated_amount)
				)
				& (bank_transaction.allocated_amount > 0)
			)
		).run()

	elif "deposit" in bank_transaction_fields:
		(
			frappe.qb.update(bank_transaction)
			.set(bank_transaction.status, "Reconciled")
			.where(
				(bank_transaction.status == "Settled")
				& (
					(bank_transaction.deposit == bank_transaction.allocated_amount)
					| (bank_transaction.withdrawal == bank_transaction.allocated_amount)
				)
				& (bank_transaction.allocated_amount > 0)
			)
		).run()
