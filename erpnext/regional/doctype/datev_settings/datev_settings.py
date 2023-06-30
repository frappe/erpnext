# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe import _, throw
from frappe.model.document import Document


class DATEVSettings(Document):
	def validate(self):
		if (
			self.temporary_against_account_number
			and len(self.temporary_against_account_number) != self.account_number_length
		):
			throw(
				_("Temporary Against Account Number must be {0} digits long").format(
					self.account_number_length
				)
			)

		if (
			self.opening_against_account_number
			and len(self.opening_against_account_number) != self.account_number_length
		):
			throw(
				_("Opening Against Account Number must be {0} digits long").format(self.account_number_length)
			)
