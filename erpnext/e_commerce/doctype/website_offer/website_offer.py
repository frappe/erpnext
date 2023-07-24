# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WebsiteOffer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		offer_details: DF.TextEditor | None
		offer_subtitle: DF.Data | None
		offer_title: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass


@frappe.whitelist(allow_guest=True)
def get_offer_details(offer_id):
	return frappe.db.get_value("Website Offer", {"name": offer_id}, ["offer_details"])
