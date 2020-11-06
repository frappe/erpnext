# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe import _
from frappe.model.document import Document

class Routing(Document):
	def validate(self):
		self.set_routing_id()

	def set_routing_id(self):
		sequence_id = 0
		for row in self.operations:
			if not row.sequence_id:
				row.sequence_id = sequence_id + 1
			elif sequence_id and row.sequence_id and cint(sequence_id) > cint(row.sequence_id):
				frappe.throw(_("At row #{0}: the sequence id {1} cannot be less than previous row sequence id {2}")
					.format(row.idx, row.sequence_id, sequence_id))

			sequence_id = row.sequence_id