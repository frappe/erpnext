# Copyright (c) 2020, Hash Include Solutions FZC and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class BankAccountType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_type: DF.Data | None
	# end: auto-generated types

	pass
