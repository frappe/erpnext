# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe import _

from erpnext.accounts.party import get_partywise_advanced_payment_amount


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_data(filters):
	data = []
	unreconciled_entries = (
		get_partywise_advanced_payment_amount(party_type=[filters.party_type], company=filters.company)
		or {}
	)

	for party, unreconciled_amount in unreconciled_entries.items():
		data.append({"party": party, "to_reconcile": unreconciled_amount})

	return data


def get_columns(filters):
	return [
		{
			"fieldname": "party",
			"label": _(filters.party_type),
			"fieldtype": "Link",
			"options": filters.party_type,
			"width": 250,
		},
		{
			"fieldname": "to_reconcile",
			"label": _("To Reconcile"),
			"fieldtype": "Currency",
			"width": 200,
		},
	]
