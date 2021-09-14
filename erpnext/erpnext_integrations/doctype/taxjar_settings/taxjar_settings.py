# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from erpnext.erpnext_integrations.taxjar_integration import get_client


class TaxJarSettings(Document):

	@frappe.whitelist()
	def update_nexus_list(self):
		client = get_client()
		nexus = client.nexus_regions()

		new_nexus_list = [frappe._dict(address) for address in nexus]

		self.set('nexus',[])
		self.set('nexus',new_nexus_list)
		self.save()