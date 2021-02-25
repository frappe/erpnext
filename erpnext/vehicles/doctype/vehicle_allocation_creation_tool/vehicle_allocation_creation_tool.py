# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.selling.doctype.vehicle_booking_order.vehicle_booking_order import validate_vehicle_item
from frappe.model.document import Document
from frappe.utils import clean_whitespace, add_years, get_first_day, get_last_day, add_months

class VehicleAllocationCreationTool(Document):
	def create(self):
		self._validate_mandatory()

		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item)

		for d in self.allocation_detail:
			doc = frappe.new_doc("Vehicle Allocation")
			doc.item_code = self.item_code
			doc.supplier = self.supplier
			doc.allocation_period = self.allocation_period
			doc.delivery_period = d.delivery_period_link
			doc.code = d.code
			doc.sr_no = d.sr_no
			doc.is_additional = self.is_additional
			doc.booking_price = d.booking_price
			doc.vehicle_color = d.vehicle_color

			doc.insert()
			doc.submit()

		frappe.msgprint(_("{0} Vehicle Allocations successfully created").format(len(self.allocation_detail)))
		self.allocation_detail = []

	def determine_delivery_periods(self):
		if not self.allocation_period:
			frappe.throw(_("Please set Allocation Period first"))
		if not self.allocation_detail:
			frappe.throw(_("Please set Allocation List first"))

		allocation_period = frappe.get_cached_doc("Vehicle Allocation Period", self.allocation_period)

		for d in self.allocation_detail:
			d.delivery_period_str = clean_whitespace(d.delivery_period_str)

		delivery_period_map = {}
		to_determine = list(set([d.delivery_period_str for d in self.allocation_detail
			if d.delivery_period_str and not d.delivery_period_link]))

		for period_str in to_determine:
			period_link = guess_delivery_period(period_str, allocation_period.from_date)
			if period_link:
				delivery_period_map[period_str] = period_link

		if delivery_period_map:
			for d in self.allocation_detail:
				if d.delivery_period_str in delivery_period_map and not d.delivery_period_link:
					d.delivery_period_link = delivery_period_map[d.delivery_period_str]

			frappe.msgprint(_("Determined Delivery Period:<ul>{0}</ul>").format("".join(
				["<li>{0}: {1}</li>".format(period_str, period_link) for period_str, period_link in delivery_period_map.items()])))


def guess_delivery_period(period_str, start_date):
	if frappe.db.exists("Vehicle Allocation", period_str):
		return period_str

	allowed = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
		"November", "December"]

	# Rename short form to full form
	rename_map = {
		"jan": "January",
		"feb": "February",
		"mar": "March",
		"apr": "April",
		"jun": "June",
		"jul": "July",
		"aug": "August",
		"sep": "September",
		"sept": "September",
		"oct": "October",
		"nov": "November",
		"dec": "December",
	}

	original_period_str = period_str
	if period_str.lower() in rename_map:
		period_str = rename_map[period_str.lower()]

	# Make sure a valid month is provided
	if period_str not in allowed:
		frappe.msgprint(_("Invalid Delivery Period {0}").format(frappe.bold(period_str)), indicator='red')
		return None

	delivery_month = allowed.index(period_str) + 1

	# Find the next delivery period range
	start_date = get_first_day(start_date)
	current_date = start_date
	end_date = add_years(start_date, 1)

	from_date = None
	while current_date < end_date:
		if current_date.month == delivery_month:
			from_date = current_date
			break

		current_date = add_months(current_date, 1)

	# check for period in database
	if from_date:
		from_date = get_first_day(from_date)
		to_date = get_last_day(from_date)

		period_link_list = frappe.db.get_all("Vehicle Allocation Period", filters={'from_date': from_date, 'to_date': to_date})
		if not period_link_list:
			frappe.msgprint(_("Cannot find Delivery Period {0} in Vehicle Allocation Period list. Please create one first")
				.format(frappe.bold(original_period_str)), indicator='red')
			return None

		return period_link_list[0].name
