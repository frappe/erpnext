# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document


class PurchasePartner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.target_detail.target_detail import TargetDetail

		commission_rate: DF.Float
		partner_name: DF.Data
		partner_type: DF.Link | None
		targets: DF.Table[TargetDetail]
		territory: DF.Link
	# end: auto-generated types

	def onload(self):
		load_address_and_contact(self)
