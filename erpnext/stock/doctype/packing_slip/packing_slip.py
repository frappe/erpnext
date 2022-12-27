# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt
from erpnext.controllers.stock_controller import StockController
from erpnext.utilities.transaction_base import validate_uom_is_integer


class PackingSlip(StockController):
	def validate(self):
		super(PackingSlip, self).validate()
		validate_uom_is_integer(self, "stock_uom", "qty")
		validate_uom_is_integer(self, "uom", "qty")
