# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class WorkOrderAdditionalItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		rate: DF.Currency
		secondary_item_type: DF.Data | None
		uom: DF.Link | None
	# end: auto-generated types

	@staticmethod
	def get_list(self, *args, **kwargs):
		pass

	@staticmethod
	def get_count(self, *args, **kwargs):
		pass

	@staticmethod
	def get_stats(self, *args, **kwargs):
		pass

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self, *args, **kwargs):
		pass

	def db_update(self, *args, **kwargs):
		pass

	def delete(self, *args, **kwargs):
		pass
