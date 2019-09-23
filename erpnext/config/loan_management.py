from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	return [
		{
			"label": _("Loan"),
			"items": [
				{
					"type": "doctype",
					"name": "Loan Type",
					"description": _("Loan Type for interest and penalty rates"),
				},
				{
					"type": "doctype",
					"name": "Loan Application",
					"description": _("Loans provided to customers and employees."),
				},
				{
					"type": "doctype",
					"name": "Loan",
					"description": _("Loans provided to customers and employees."),
				},

			]
		},
		{
			"label": _("Loan Security"),
			"items": [
				{
					"type": "doctype",
					"name": "Loan Security Type",
				},
				{
					"type": "doctype",
					"name": "Loan Security Price",
				},
				{
					"type": "doctype",
					"name": "Loan Security",
				},
				{
					"type": "doctype",
					"name": "Loan Security Pledge",
				},
				{
					"type": "doctype",
					"name": "Loan Security Unpledge",
				},
				{
					"type": "doctype",
					"name": "Loan Security Shortfall",
				},
			]
		},
		{
			"label": _("Disbursement and Repayment"),
			"items": [
				{
					"type": "doctype",
					"name": "Loan Disbursement",
				},
				{
					"type": "doctype",
					"name": "Loan Repayment",
				},
				{
					"type": "doctype",
					"name": "Loan Interest Accrual"
				}
			]
		}
	]