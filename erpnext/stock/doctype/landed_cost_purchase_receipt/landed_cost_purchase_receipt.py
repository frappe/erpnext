# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class LandedCostPurchaseReceipt(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		grand_total: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_date: DF.Date | None
		receipt_document: DF.DynamicLink
<<<<<<< HEAD
		receipt_document_type: DF.Literal[
			"", "Purchase Invoice", "Purchase Receipt", "Stock Entry", "Subcontracting Receipt"
		]
=======
		receipt_document_type: DF.Literal["", "Purchase Invoice", "Purchase Receipt"]
>>>>>>> 7c4cf3e834 (Favicon.svg)
		supplier: DF.Link | None
	# end: auto-generated types

	pass
