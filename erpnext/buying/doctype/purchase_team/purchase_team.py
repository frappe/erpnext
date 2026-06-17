# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class PurchaseTeam(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allocated_amount: DF.Currency
		allocated_percentage: DF.Float
		commission_rate: DF.Data | None
		contact_no: DF.Data | None
		incentives: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_person: DF.Link
	# end: auto-generated types

	pass
