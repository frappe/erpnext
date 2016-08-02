# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe

def enable_service():
	from erpnext.integration_controller.utils import create_payment_gateway_and_account
	create_payment_gateway_and_account("PayPal")

def validate_credentails():
	pass