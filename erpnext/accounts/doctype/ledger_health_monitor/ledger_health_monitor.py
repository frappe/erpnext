# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LedgerHealthMonitor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.ledger_health_monitor_company.ledger_health_monitor_company import (
			LedgerHealthMonitorCompany,
		)

		companies: DF.Table[LedgerHealthMonitorCompany]
		debit_credit_mismatch: DF.Check
		enable_health_monitor: DF.Check
		general_and_payment_ledger_mismatch: DF.Check
		monitor_for_last_x_days: DF.Int
	# end: auto-generated types

	pass
