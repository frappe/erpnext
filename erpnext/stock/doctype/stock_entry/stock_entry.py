# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe import _
from frappe.utils import cstr, cint, flt, comma_or, getdate, nowdate
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle, get_valuation_rate
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor,\
	get_reserved_qty_for_so, get_hide_item_code, get_default_warehouse
from erpnext.stock.doctype.batch.batch import get_batch_qty, auto_select_and_split_batches
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, add_additional_cost
from erpnext.stock.utils import get_bin
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit, get_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import OpeningEntryAccountError

import json

from six import string_types, itervalues, iteritems

class IncorrectValuationRateError(frappe.ValidationError): pass
class DuplicateEntryForWorkOrderError(frappe.ValidationError): pass
class OperationsNotCompleteError(frappe.ValidationError): pass
class MaxSampleAlreadyRetainedError(frappe.ValidationError): pass

from erpnext.controllers.stock_controller import StockController

form_grid_templates = {
	"items": "templates/form_grid/stock_entry_grid.html"
}

force_fields = ["stock_uom", "has_batch_no", "has_serial_no", "is_vehicle", "alt_uom", "alt_uom_size"]


class StockEntry(StockController):
	def get_feed(self):
		return self.stock_entry_type

	def onload(self):
		for item in self.get("items"):
			item.update(get_bin_details(item.item_code, item.s_warehouse))

	def validate(self):
		self.pro_doc = frappe._dict()
		if self.work_order:
			self.pro_doc = frappe.get_doc('Work Order', self.work_order)

		self.validate_posting_time()
		self.validate_stock_entry_type()
		self.validate_purpose()
		self.validate_vehicle_item()
		self.validate_item()
		self.validate_customer_provided_item()
		self.validate_customer_provided_entry()
		self.validate_qty()
		self.set_transfer_qty()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse()
		self.validate_work_order()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_with_material_request()
		self.validate_batch()
		self.validate_inspection()
		self.validate_fg_completed_qty()
		self.validate_difference_account()
		self.set_job_card_data()
		self.set_purpose_for_stock_entry()

		if not self.from_bom:
			self.fg_completed_qty = 0.0

		if self._action == 'submit':
			self.make_batches('t_warehouse')
		else:
			pass
			# set_batch_nos(self, 's_warehouse')

		self.set_incoming_rate()
		self.validate_serialized_batch()
		self.set_actual_qty()
		self.calculate_rate_and_amount()
		self.set_transferred_status()

	def on_submit(self):
		self.update_stock_ledger()

		update_serial_nos_after_submit(self, "items")
		self.update_work_order()
		self.validate_purchase_order()
		if self.purchase_order and self.purpose == "Send to Subcontractor":
			self.update_purchase_order_supplied_items()
		self.make_gl_entries()
		self.update_cost_in_project()
		self.validate_reserved_serial_no_consumption()
		self.update_previous_doc_status()
		self.update_quality_inspection()
		if self.work_order and self.purpose == "Manufacture":
			self.update_so_in_serial_number()

	def on_cancel(self):
		if self.purchase_order and self.purpose == "Send to Subcontractor":
			self.update_purchase_order_supplied_items()

		if self.work_order and self.purpose == "Material Consumption for Manufacture":
			self.validate_work_order_status()

		self.update_work_order()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.update_cost_in_project()
		self.update_previous_doc_status()
		self.update_quality_inspection()

	def update_previous_doc_status(self):
		material_requests = set()
		material_request_row_names = set()
		stock_entries = set()
		stock_entry_row_names = set()

		for d in self.get("items"):
			if d.material_request:
				material_requests.add(d.material_request)
			if d.material_request_item:
				material_request_row_names.add(d.material_request_item)
			if d.against_stock_entry:
				stock_entries.add(d.against_stock_entry)
			if d.ste_detail:
				stock_entry_row_names.add(d.ste_detail)

		# Update Material Requests
		for name in material_requests:
			doc = frappe.get_doc("Material Request", name)

			if doc.docstatus != 1:
				frappe.throw(_("{0} is not submitted").format(frappe.get_desk_link("Material Request", name)),
					frappe.InvalidStatusError)

			if doc.status == "Stopped":
				frappe.throw(_("{0} is cancelled or stopped").format(frappe.get_desk_link("Material Request", name)),
					frappe.InvalidStatusError)

			doc.set_completion_status(update=True)
			doc.validate_ordered_qty(from_doctype=self.doctype, row_names=material_request_row_names)
			doc.update_requested_qty(material_request_row_names)
			doc.set_status(update=True)
			doc.notify_update()

		# Update Send to Warehouse Stock Entries
		if self.purpose == "Receive at Warehouse":
			for name in stock_entries:
				doc = frappe.get_doc("Stock Entry", name)
				doc.set_transferred_status(update=True)
				doc.validate_transferred_qty(from_doctype=self.doctype, row_names=stock_entry_row_names)
				doc.set_status(update=True)
				doc.notify_update()

	def set_transferred_status(self, update=False, update_modified=True):
		transferred_qty_map = self.get_transferred_qty_map()

		# update values in rows
		for d in self.items:
			d.transferred_qty = flt(transferred_qty_map.get(d.name))

			if update:
				d.db_set({
					'transferred_qty': d.transferred_qty,
				}, update_modified=update_modified)

		# update percentage in parent
		self.per_transferred = self.calculate_status_percentage('transferred_qty', 'qty', self.items)

		if update:
			self.db_set({
				'per_transferred': self.per_transferred,
			}, update_modified=update_modified)

	def get_transferred_qty_map(self):
		transferred_qty_map = {}

		if self.docstatus == 1:
			row_names = [d.name for d in self.items]
			if row_names:
				transferred_qty_map = dict(frappe.db.sql("""
					select i.ste_detail, sum(i.qty)
					from `tabStock Entry Detail` i
					inner join `tabStock Entry` p on p.name = i.parent
					where p.docstatus = 1 and i.ste_detail in %s
					group by i.ste_detail
				""", [row_names]))

		return transferred_qty_map

	def validate_transferred_qty(self, from_doctype=None, row_names=None):
		self.validate_completed_qty('transferred_qty', 'qty', self.items,
			allowance_type=None, from_doctype=from_doctype, row_names=row_names)

	def auto_select_batches(self):
		auto_select_and_split_batches(self, 's_warehouse')

	def set_job_card_data(self):
		if self.job_card and not self.work_order:
			data = frappe.db.get_value('Job Card',
				self.job_card, ['for_quantity', 'work_order', 'bom_no'], as_dict=1)
			self.fg_completed_qty = data.for_quantity
			self.work_order = data.work_order
			self.from_bom = 1
			self.bom_no = data.bom_no

	def validate_work_order_status(self):
		pro_doc = frappe.get_doc("Work Order", self.work_order)
		if pro_doc.status == 'Completed':
			frappe.throw(_("Cannot cancel transaction for Completed Work Order."))

	def validate_stock_entry_type(self):
		ste_type_doc = frappe.get_cached_doc("Stock Entry Type", self.stock_entry_type)
		self.purpose = ste_type_doc.purpose

		if ste_type_doc.posting_date:
			self.posting_date = ste_type_doc.posting_date

		if ste_type_doc.is_opening:
			self.is_opening = ste_type_doc.is_opening

		if ste_type_doc.customer_provided:
			self.customer_provided = cint(ste_type_doc.customer_provided == "Yes")

		self.source_warehouse_type = ste_type_doc.source_warehouse_type
		self.target_warehouse_type = ste_type_doc.target_warehouse_type
		for d in self.items:
			if self.source_warehouse_type and d.s_warehouse:
				if frappe.get_cached_value("Warehouse", d.s_warehouse, "warehouse_type") != self.source_warehouse_type:
					frappe.throw(_("Row #{0}: Source Warehouse must be of type {1} for Stock Entry Type {2}")
						.format(d.idx, frappe.bold(self.source_warehouse_type), frappe.bold(self.stock_entry_type)))
			if self.target_warehouse_type and d.t_warehouse:
				if frappe.get_cached_value("Warehouse", d.t_warehouse, "warehouse_type") != self.target_warehouse_type:
					frappe.throw(_("Row #{0}: Target Warehouse must be of type {1} for Stock Entry Type {2}")
						.format(d.idx, frappe.bold(self.target_warehouse_type), frappe.bold(self.stock_entry_type)))

	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer",
			"Material Transfer for Manufacture", "Manufacture", "Repack", "Send to Subcontractor",
			"Material Consumption for Manufacture", "Send to Warehouse", "Receive at Warehouse"]

		if self.purpose not in valid_purposes:
			frappe.throw(_("Purpose must be one of {0}").format(comma_or(valid_purposes)))

		if self.job_card and self.purpose != 'Material Transfer for Manufacture':
			frappe.throw(_("For job card {0}, you can only make the 'Material Transfer for Manufacture' type stock entry")
				.format(self.job_card))

	def set_transfer_qty(self):
		for item in self.get("items"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx))
			if not flt(item.conversion_factor):
				frappe.throw(_("Row {0}: UOM Conversion Factor is mandatory").format(item.idx))
			item.transfer_qty = flt(flt(item.qty) * flt(item.conversion_factor),
				self.precision("transfer_qty", item))

			if not item.alt_uom:
				item.alt_uom_size = 1.0
			item.alt_uom_qty = flt(flt(item.qty) * flt(item.conversion_factor) * flt(item.alt_uom_size), item.precision("alt_uom_qty"))

	def update_cost_in_project(self):
		if self.work_order:
			if not frappe.db.get_value("Work Order", self.work_order, "update_consumed_material_cost_in_project"):
				return

		if self.project:
			project = frappe.get_doc("Project", self.project)
			project.set_material_consumed_cost(update=True)
			project.set_gross_margin(update=True)
			project.set_status(update=True)
			project.notify_update()

	def validate_item(self):
		from erpnext.stock.doctype.item.item import validate_end_of_life

		stock_items = self.get_stock_items()
		serialized_items = self.get_serialized_items()

		for d in self.get("items"):
			item = frappe.get_cached_value("Item", d.item_code, ['has_variants', 'end_of_life', 'disabled'], as_dict=1)
			validate_end_of_life(d.item_code, end_of_life=item.end_of_life, disabled=item.disabled)

			if cint(item.has_variants):
				frappe.throw(_("Item {0} is a template, please select one of its variants").format(item.name))

			if d.item_code not in stock_items:
				frappe.throw(_("{0} is not a stock Item").format(d.item_code))

			if flt(d.qty) and flt(d.qty) < 0:
				frappe.throw(_("Row {0}: The item {1}, quantity must be positive number")
					.format(d.idx, frappe.bold(d.item_code)))

			self.set_missing_item_values(d)

			if not d.transfer_qty and d.qty:
				d.transfer_qty = flt(flt(d.qty) * flt(d.conversion_factor),
				self.precision("transfer_qty", d))

			if (self.purpose in ("Material Transfer", "Material Transfer for Manufacture")
				and not d.serial_no
				and d.item_code in serialized_items):
				frappe.throw(_("Row #{0}: Please specify Serial No for Item {1}").format(d.idx, d.item_code),
					frappe.MandatoryError)

	def set_missing_item_values(self, item):
		item_details = self.get_item_details(frappe._dict(
			{"item_code": item.item_code, "company": self.company, 'batch_no': item.batch_no,
				"project": item.project or self.project, "uom": item.uom, 's_warehouse': item.s_warehouse}),
			for_update=True)

		for f in item_details:
			if f in force_fields or not item.get(f):
				item.set(f, item_details.get(f))

	def validate_qty(self):
		manufacture_purpose = ["Manufacture", "Material Consumption for Manufacture"]

		if self.purpose in manufacture_purpose and self.work_order:
			if not frappe.get_value('Work Order', self.work_order, 'skip_transfer'):
				item_code = []
				for item in self.items:
					if cstr(item.t_warehouse) == '':
						req_items = frappe.get_all('Work Order Item',
										filters={'parent': self.work_order, 'item_code': item.item_code}, fields=["item_code"])

						transferred_materials = frappe.db.sql("""
									select
										sum(qty) as qty
									from `tabStock Entry` se,`tabStock Entry Detail` sed
									where
										se.name = sed.parent and se.docstatus=1 and
										(se.purpose='Material Transfer for Manufacture' or se.purpose='Manufacture')
										and sed.item_code=%s and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
								""", (item.item_code, self.work_order), as_dict=1)

						stock_qty = flt(item.qty)
						trans_qty = flt(transferred_materials[0].qty)
						if req_items:
							if stock_qty > trans_qty:
								item_code.append(item.item_code)

	def validate_fg_completed_qty(self):
		if self.purpose == "Manufacture" and self.work_order:
			production_item = frappe.get_value('Work Order', self.work_order, 'production_item')
			for item in self.items:
				if item.item_code == production_item and item.qty != self.fg_completed_qty:
					frappe.throw(_("Finished product quantity <b>{0}</b> and For Quantity <b>{1}</b> cannot be different")
						.format(item.qty, self.fg_completed_qty))

	def validate_difference_account(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		for d in self.get("items"):
			if not d.expense_account:
				frappe.throw(_("Please enter <b>Difference Account</b> or set default <b>Stock Adjustment Account</b> for company {0}")
					.format(frappe.bold(self.company)))

			elif self.is_opening == "Yes" and frappe.db.get_value("Account", d.expense_account, "report_type") == "Profit and Loss":
				frappe.throw(_("Difference Account must be a Asset/Liability type account, since this Stock Entry is an Opening Entry"), OpeningEntryAccountError)

	def validate_warehouse(self):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = ["Material Issue", "Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture",
			"Material Consumption for Manufacture", "Send to Warehouse", "Receive at Warehouse"]

		target_mandatory = ["Material Receipt", "Material Transfer", "Send to Subcontractor",
			"Material Transfer for Manufacture", "Send to Warehouse", "Receive at Warehouse"]

		validate_for_manufacture = any([d.bom_no for d in self.get("items")])

		if self.purpose in source_mandatory and self.purpose not in target_mandatory:
			self.to_warehouse = None
			for d in self.get('items'):
				d.t_warehouse = None
		elif self.purpose in target_mandatory and self.purpose not in source_mandatory:
			self.from_warehouse = None
			for d in self.get('items'):
				d.s_warehouse = None

		for d in self.get('items'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.from_warehouse
				d.t_warehouse = self.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				frappe.throw(_("Atleast one warehouse is mandatory"))

			if self.purpose in source_mandatory and not d.s_warehouse:
				if self.from_warehouse:
					d.s_warehouse = self.from_warehouse
				else:
					frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose in target_mandatory and not d.t_warehouse:
				if self.to_warehouse:
					d.t_warehouse = self.to_warehouse
				else:
					frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose == "Manufacture":
				if validate_for_manufacture:
					if d.bom_no:
						d.s_warehouse = None
						if not d.t_warehouse:
							frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))
					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse) and not self.purpose == "Material Transfer for Manufacture":
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

	def validate_customer_provided_entry(self):
		if self.purpose not in ('Material Receipt', 'Material Issue'):
			self.customer_provided = 0

		if not self.customer_provided:
			self.customer = self.customer_name = self.customer_address = None
		if not self.customer_address and not self.supplier_address:
			self.address_display = None

		if self.customer_provided:
			for d in self.items:
				d.allow_zero_valuation_rate = 1


	def validate_work_order(self):
		if self.purpose in ("Manufacture", "Material Transfer for Manufacture", "Material Consumption for Manufacture"):
			# check if work order is entered

			if (self.purpose=="Manufacture" or self.purpose=="Material Consumption for Manufacture") \
					and self.work_order:
				if not self.fg_completed_qty:
					frappe.throw(_("For Quantity (Manufactured Qty) is mandatory"))
				self.check_if_operations_completed()
				self.check_duplicate_entry_for_work_order()
		elif self.purpose != "Material Transfer":
			self.work_order = None

	def check_if_operations_completed(self):
		"""Check if Time Sheets are completed against before manufacturing to capture operating costs."""
		prod_order = frappe.get_doc("Work Order", self.work_order)
		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		for d in prod_order.get("operations"):
			total_completed_qty = flt(self.fg_completed_qty) + flt(prod_order.produced_qty)
			completed_qty = d.completed_qty + (allowance_percentage/100 * d.completed_qty)
			if total_completed_qty > flt(completed_qty):
				job_card = frappe.db.get_value('Job Card', {'operation_id': d.name}, 'name')
				if not job_card:
					frappe.throw(_("Work Order {0}: Job Card not found for the operation {1}")
						.format(self.work_order, d.operation))

				work_order_link = frappe.utils.get_link_to_form('Work Order', self.work_order)
				job_card_link = frappe.utils.get_link_to_form('Job Card', job_card)
				frappe.throw(_("Row #{0}: Operation {1} is not completed for {2} qty of finished goods in Work Order {3}. Please update operation status via Job Card {4}.")
					.format(d.idx, frappe.bold(d.operation), frappe.bold(total_completed_qty), work_order_link, job_card_link), OperationsNotCompleteError)

	def check_duplicate_entry_for_work_order(self):
		other_ste = [t[0] for t in frappe.db.get_values("Stock Entry",  {
			"work_order": self.work_order,
			"purpose": self.purpose,
			"docstatus": ["!=", 2],
			"name": ["!=", self.name]
		}, "name")]

		if other_ste:
			production_item, qty = frappe.db.get_value("Work Order",
				self.work_order, ["production_item", "qty"])
			args = other_ste + [production_item]
			fg_qty_already_entered = frappe.db.sql("""select sum(transfer_qty)
				from `tabStock Entry Detail`
				where parent in (%s)
					and item_code = %s
					and ifnull(s_warehouse,'')='' """ % (", ".join(["%s" * len(other_ste)]), "%s"), args)[0][0]
			if fg_qty_already_entered and fg_qty_already_entered >= qty:
				frappe.throw(_("Stock Entries already created for Work Order ")
					+ self.work_order + ":" + ", ".join(other_ste), DuplicateEntryForWorkOrderError)

	def set_incoming_rate(self):
		for d in self.items:
			if d.s_warehouse:
				args = self.get_args_for_incoming_rate(d)
				d.basic_rate = get_incoming_rate(args)
			elif d.allow_zero_valuation_rate and not d.s_warehouse:
				d.basic_rate = 0.0
			elif d.t_warehouse and not d.basic_rate and not self.is_finished_good_item(d):
				d.basic_rate = get_valuation_rate(d.item_code, d.t_warehouse,
					self.doctype, d.name, d.batch_no, d.allow_zero_valuation_rate,
					currency=erpnext.get_company_currency(self.company), company=self.company,
					raise_error_if_no_rate=False)

	def set_actual_qty(self):
		for d in self.get('items'):
			previous_sle = get_previous_sle({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time
			})

			# get actual stock at source warehouse
			d.actual_qty = previous_sle.get("qty_after_transaction") or 0

	def set_serial_nos(self, work_order):
		previous_se = frappe.db.get_value("Stock Entry", {"work_order": work_order,
				"purpose": "Material Transfer for Manufacture"}, "name")

		for d in self.get('items'):
			transferred_serial_no = frappe.db.get_value("Stock Entry Detail",{"parent": previous_se,
				"item_code": d.item_code}, "serial_no")

			if transferred_serial_no:
				d.serial_no = transferred_serial_no

	def get_stock_and_rate(self):
		self.set_work_order_details()
		self.set_transfer_qty()
		self.set_actual_qty()
		self.calculate_rate_and_amount()

	def calculate_rate_and_amount(self, force=False,
			update_finished_item_rate=True, raise_error_if_no_rate=True):
		self.set_basic_rate(force, update_finished_item_rate, raise_error_if_no_rate)
		self.distribute_additional_costs()
		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()

	def set_basic_rate(self, force=False, update_finished_item_rate=True, raise_error_if_no_rate=True):
		"""get stock and incoming rate on posting date"""
		for d in self.get('items'):
			if self.customer_provided and not d.s_warehouse:
				d.basic_rate = 0
				d.basic_amount = 0

			args = self.get_args_for_incoming_rate(d)

			# get basic rate
			if not d.bom_no:
				if d.s_warehouse or force:
					basic_rate = flt(get_incoming_rate(args, raise_error_if_no_rate))
					if basic_rate > 0:
						d.basic_rate = basic_rate

				d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

			# get scrap items basic rate
			if self.is_scrap_item(d):
				if not flt(d.basic_rate) and not d.allow_zero_valuation_rate:
					basic_rate = flt(get_incoming_rate(args, raise_error_if_no_rate))
					if basic_rate > 0:
						d.basic_rate = basic_rate
					d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

		if self.purpose in ("Manufacture", "Repack") and update_finished_item_rate:
			self.set_basic_rate_for_finished_goods()

	def get_args_for_incoming_rate(self, item):
		return frappe._dict({
			"item_code": item.item_code,
			"warehouse": item.s_warehouse or item.t_warehouse,
			"batch_no": item.batch_no,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"qty": item.s_warehouse and -1*flt(item.transfer_qty) or flt(item.transfer_qty),
			"serial_no": item.serial_no,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"company": self.company,
			"allow_zero_valuation": item.allow_zero_valuation_rate,
		})

	def set_basic_rate_for_finished_goods(self):
		for d in self.get("items"):
			d.cost_percentage = 0

		if self.purpose not in ["Manufacture", "Repack"]:
			return

		# Calculate costs and qtys
		raw_material_cost = 0
		scrap_material_cost = 0
		total_fg_qty = 0
		total_fg_stock_qty = 0
		total_fg_items = 0
		for d in self.get("items"):
			if self.is_scrap_item(d):
				scrap_material_cost += flt(d.basic_amount)
			elif d.s_warehouse and not d.t_warehouse:
				raw_material_cost += flt(d.basic_amount)
			elif self.is_finished_good_item(d):
				total_fg_qty += flt(d.qty)
				total_fg_stock_qty += flt(d.transfer_qty)
				total_fg_items += 1

		if not total_fg_stock_qty or not total_fg_items:
			return

		# Use raw material cost from BOM if allow_multiple_material_consumption
		allow_multiple_material_consumption = frappe.get_cached_value("Manufacturing Settings", None, "material_consumption")
		if self.purpose == "Manufacture" and self.work_order and total_fg_stock_qty and allow_multiple_material_consumption:
			bom_items = self.get_bom_raw_materials(total_fg_stock_qty)
			raw_material_cost = sum([flt(row.qty) * flt(row.rate) for row in bom_items.values()])

		# set fg rate
		if self.purpose == "Manufacture":
			basic_rate = (raw_material_cost - scrap_material_cost) / total_fg_stock_qty if total_fg_stock_qty else 0
		else:
			basic_rate = (raw_material_cost - scrap_material_cost) / total_fg_qty if total_fg_qty else 0

		for d in self.get("items"):
			if self.is_finished_good_item(d) and not d.set_basic_rate_manually:
				if self.purpose == "Manufacture":
					d.basic_rate = basic_rate
					d.basic_amount = flt(d.basic_rate * flt(d.transfer_qty), d.precision("basic_amount"))
					d.cost_percentage = flt(d.transfer_qty) / total_fg_stock_qty * 100 if total_fg_stock_qty else 0
				else:
					d.basic_rate = basic_rate
					d.basic_amount = flt(d.basic_rate * flt(d.qty), d.precision("basic_amount"))
					d.cost_percentage = flt(d.qty) / total_fg_qty * 100 if total_fg_qty else 0

	def is_scrap_item(self, d):
		pro_doc = getattr(self, "pro_doc", frappe._dict())
		return (self.purpose in ('Manufacture', 'Repack')
			and d.bom_no
			and d.t_warehouse
			and pro_doc.scrap_warehouse == d.t_warehouse)

	def is_finished_good_item(self, d):
		return (self.purpose in ('Manufacture', 'Repack')
			and (d.bom_no or d.t_warehouse)
			and not d.s_warehouse
			and not self.is_scrap_item(d))

	def distribute_additional_costs(self):
		if self.purpose == "Material Issue":
			self.additional_costs = []

		self.total_additional_costs = sum([flt(t.amount) for t in self.get("additional_costs")])
		total_basic_amount = sum([flt(t.basic_amount) for t in self.get("items") if t.t_warehouse and not self.is_scrap_item(t)])
		total_qty = sum([flt(t.qty) for t in self.get("items") if t.t_warehouse and not self.is_scrap_item(t)])

		for d in self.get("items"):
			if d.t_warehouse and not self.is_scrap_item(d) and (total_basic_amount or total_qty):
				if total_basic_amount:
					d.additional_cost = (flt(d.basic_amount) / total_basic_amount) * self.total_additional_costs
				else:
					d.additional_cost = (flt(d.qty) / total_qty) * self.total_additional_costs
			else:
				d.additional_cost = 0

	def update_valuation_rate(self):
		for d in self.get("items"):
			if d.transfer_qty:
				d.amount = flt(flt(d.basic_amount) + flt(d.additional_cost), d.precision("amount"))
				d.valuation_rate = d.amount / flt(d.transfer_qty)

	def set_total_incoming_outgoing_value(self):
		self.total_incoming_value = self.total_outgoing_value = 0.0
		for d in self.get("items"):
			if d.t_warehouse:
				self.total_incoming_value += flt(d.amount)
			if d.s_warehouse:
				self.total_outgoing_value += flt(d.amount)

		self.value_difference = self.total_incoming_value - self.total_outgoing_value

	def set_total_amount(self):
		self.total_amount = None
		if self.purpose not in ['Manufacture', 'Repack']:
			self.total_amount = sum([flt(item.amount) for item in self.get("items")])

	def set_stock_entry_type(self):
		if self.purpose:
			types = frappe.db.get_all("Stock Entry Type", filters={'purpose': self.purpose}, order_by='creation asc')
			types = [d.name for d in types]

			if self.purpose in types:
				self.stock_entry_type = self.purpose
			else:
				self.stock_entry_type = types[0]

	def set_purpose_for_stock_entry(self):
		if self.stock_entry_type and not self.purpose:
			self.purpose = frappe.get_cached_value('Stock Entry Type',
				self.stock_entry_type, 'purpose')

	def validate_purchase_order(self):
		"""Throw exception if more raw material is transferred against Purchase Order than in
		the raw materials supplied table"""
		backflush_raw_materials_based_on = frappe.db.get_single_value("Buying Settings",
			"backflush_raw_materials_of_subcontract_based_on")

		qty_allowance = flt(frappe.db.get_single_value("Buying Settings",
			"over_transfer_allowance"))

		if not (self.purpose == "Send to Subcontractor" and self.purchase_order): return

		if (backflush_raw_materials_based_on == 'BOM'):
			purchase_order = frappe.get_doc("Purchase Order", self.purchase_order)
			for se_item in self.items:
				item_code = se_item.original_item or se_item.item_code
				precision = cint(frappe.db.get_default("float_precision")) or 3
				required_qty = sum([flt(d.required_qty) for d in purchase_order.supplied_items \
					if d.rm_item_code == item_code])

				total_allowed = required_qty + (required_qty * (qty_allowance/100))

				if not required_qty:
					bom_no = frappe.db.get_value("Purchase Order Item",
						{"parent": self.purchase_order, "item_code": se_item.subcontracted_item},
						"bom")

					if se_item.allow_alternative_item:
						original_item_code = frappe.get_value("Item Alternative", {"alternative_item_code": item_code}, "item_code")

						required_qty = sum([flt(d.required_qty) for d in purchase_order.supplied_items \
							if d.rm_item_code == original_item_code])

						total_allowed = required_qty + (required_qty * (qty_allowance/100))

				if not required_qty:
					frappe.throw(_("Item {0} not found in 'Raw Materials Supplied' table in Purchase Order {1}")
						.format(se_item.item_code, self.purchase_order))
				total_supplied = frappe.db.sql("""select sum(transfer_qty)
					from `tabStock Entry Detail`, `tabStock Entry`
					where `tabStock Entry`.purchase_order = %s
						and `tabStock Entry`.docstatus = 1
						and `tabStock Entry Detail`.item_code = %s
						and `tabStock Entry Detail`.parent = `tabStock Entry`.name""",
							(self.purchase_order, se_item.item_code))[0][0]

				if flt(total_supplied, precision) > flt(total_allowed, precision):
					frappe.throw(_("Row {0}# Item {1} cannot be transferred more than {2} against Purchase Order {3}")
						.format(se_item.idx, se_item.item_code, total_allowed, self.purchase_order))
		elif backflush_raw_materials_based_on == "Material Transferred for Subcontract":
			for row in self.items:
				if not row.subcontracted_item:
					frappe.throw(_("Row {0}: Subcontracted Item is mandatory for the raw material {1}")
						.format(row.idx, frappe.bold(row.item_code)))

	def validate_bom(self):
		for d in self.get('items'):
			if d.bom_no and (d.t_warehouse != getattr(self, "pro_doc", frappe._dict()).scrap_warehouse):
				item_code = d.original_item or d.item_code
				validate_bom_no(item_code, d.bom_no)

	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		if not self.work_order: return

		items_with_target_warehouse = []
		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		production_item, wo_qty = frappe.db.get_value("Work Order",
			self.work_order, ["production_item", "qty"])

		for d in self.get('items'):
			if (self.purpose != "Send to Subcontractor" and d.bom_no
				and flt(d.transfer_qty) > flt(self.fg_completed_qty) and d.item_code == production_item):
				frappe.throw(_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}"). \
					format(d.idx, d.transfer_qty, self.fg_completed_qty))

			if self.work_order and self.purpose == "Manufacture" and d.t_warehouse:
				items_with_target_warehouse.append(d.item_code)

		if self.work_order and self.purpose == "Manufacture":
			allowed_qty = wo_qty + (allowance_percentage/100 * wo_qty)
			if self.fg_completed_qty > allowed_qty:
				frappe.throw(_("For quantity {0} should not be grater than work order quantity {1}")
					.format(flt(self.fg_completed_qty), wo_qty))

			if production_item not in items_with_target_warehouse:
				frappe.throw(_("Finished Item {0} must be entered for Manufacture type entry")
					.format(production_item))

	def update_stock_ledger(self, allow_negative_stock=False):
		sl_entries = []

		# make sl entries for source warehouse first, then do for target warehouse
		for d in self.get('items'):
			if cstr(d.s_warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.s_warehouse),
					"actual_qty": -flt(d.transfer_qty),
					"incoming_rate": 0
				}))

		for d in self.get('items'):
			if cstr(d.t_warehouse):
				sle = self.get_sl_entries(d, {
					"warehouse": cstr(d.t_warehouse),
					"actual_qty": flt(d.transfer_qty),
					"incoming_rate": flt(d.valuation_rate)
				})

				# SLE Dependency
				if self.docstatus == 1:
					# Material Transfer dependency
					if cstr(d.s_warehouse):
						sle.additional_cost = flt(d.additional_cost)
						sle.dependencies = [{
							"dependent_voucher_type": self.doctype,
							"dependent_voucher_no": self.name,
							"dependent_voucher_detail_no": d.name,
							"dependency_type": "Amount",
						}]

					# Receive at Warehouse dependency
					elif d.against_stock_entry and d.ste_detail:
						sle.dependencies = [{
							"dependent_voucher_type": d.against_stock_entry,
							"dependent_voucher_no": d.ste_detail,
							"dependent_voucher_detail_no": d.name,
							"dependency_type": "Rate",
							"dependency_qty_filter": "Positive"
						}]

					# Manufacture / Repack dependency
					elif self.is_finished_good_item(d) and not d.set_basic_rate_manually and d.cost_percentage:
						sle.additional_cost = flt(d.additional_cost)
						sle.dependencies = []
						for dep_row in self.get("items"):
							if flt(dep_row.transfer_qty) and (self.is_scrap_item(dep_row) or (dep_row.s_warehouse and not dep_row.t_warehouse)):
								sle.dependencies.append({
									"dependent_voucher_type": self.doctype,
									"dependent_voucher_no": self.name,
									"dependent_voucher_detail_no": dep_row.name,
									"dependency_type": "Amount",
									"dependency_percentage": d.cost_percentage
								})

				sl_entries.append(sle)

		# On cancellation, make stock ledger entry for
		# target warehouse first, to update serial no values properly

			# if cstr(d.s_warehouse) and self.docstatus == 2:
			# 	sl_entries.append(self.get_sl_entries(d, {
			# 		"warehouse": cstr(d.s_warehouse),
			# 		"actual_qty": -flt(d.transfer_qty),
			# 		"incoming_rate": 0
			# 	}))

		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No',
			allow_negative_stock=allow_negative_stock)

	def get_gl_entries(self, warehouse_account):
		gl_entries = super(StockEntry, self).get_gl_entries(warehouse_account)

		total_basic_amount = sum([flt(t.basic_amount) for t in self.get("items") if t.t_warehouse])
		divide_based_on = total_basic_amount

		if self.get("additional_costs") and not total_basic_amount:
			# if total_basic_amount is 0, distribute additional charges based on qty
			divide_based_on = sum(item.qty for item in list(self.get("items")))

		item_account_wise_additional_cost = {}

		for t in self.get("additional_costs"):
			for d in self.get("items"):
				if d.t_warehouse:
					item_account_wise_additional_cost.setdefault((d.item_code, d.name), {})
					item_account_wise_additional_cost[(d.item_code, d.name)].setdefault(t.expense_account, 0.0)

					multiply_based_on = d.basic_amount if total_basic_amount else d.qty

					item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account] += \
						(t.amount * multiply_based_on) / divide_based_on

		if item_account_wise_additional_cost:
			for d in self.get("items"):
				for account, amount in iteritems(item_account_wise_additional_cost.get((d.item_code, d.name), {})):
					if not amount: continue

					gl_entries.append(self.get_gl_dict({
						"account": account,
						"against": d.expense_account,
						"cost_center": d.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"credit": amount
					}, item=d))

					gl_entries.append(self.get_gl_dict({
						"account": d.expense_account,
						"against": account,
						"cost_center": d.cost_center,
						"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
						"credit": -1 * amount # put it as negative credit instead of debit purposefully
					}, item=d))

		if self.get('cost_center'):
			for gle in gl_entries:
				gle.cost_center = self.get('cost_center')

		return gl_entries

	def update_work_order(self):
		def _validate_work_order(pro_doc):
			if flt(pro_doc.docstatus) != 1:
				frappe.throw(_("Work Order {0} must be submitted").format(self.work_order))

			if pro_doc.status == 'Stopped':
				frappe.throw(_("Transaction not allowed against stopped Work Order {0}").format(self.work_order))

		if self.job_card:
			job_doc = frappe.get_doc('Job Card', self.job_card)
			job_doc.set_transferred_qty(update_status=True)

		if self.work_order:
			pro_doc = frappe.get_doc("Work Order", self.work_order)
			_validate_work_order(pro_doc)
			pro_doc.run_method("update_status")
			if self.fg_completed_qty:
				pro_doc.run_method("update_work_order_qty")
				if self.purpose == "Manufacture":
					pro_doc.run_method("update_planned_qty")

			pro_doc.notify_update()

	def get_item_details(self, args=None, for_update=False):
		if not args.get('item_code'):
			frappe.throw(_("Item Code not provided"))

		item = frappe.get_cached_doc("Item", args.get('item_code'))

		out = frappe._dict({
			'uom': item.stock_uom,
			'stock_uom': item.stock_uom,
			'description': cstr(item.description).strip(),
			'image': item.image,
			'item_name': item.item_name,
			'hide_item_code': get_hide_item_code(item, args),
			'cost_center': get_default_cost_center(item, args),
			'qty': args.get("qty"),
			'transfer_qty': args.get('qty'),
			'conversion_factor': 1,
			'batch_no': '',
			'actual_qty': 0,
			'basic_rate': 0,
			'serial_no': '',
			'has_serial_no': item.has_serial_no,
			'is_vehicle': item.is_vehicle,
			'has_batch_no': item.has_batch_no,
			'sample_quantity': item.sample_quantity
		})

		if self.purpose == 'Send to Subcontractor':
			out["allow_alternative_item"] = item.allow_alternative_item

		# update uom
		if args.get("uom"):
			uom_details = get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty'))
			if not uom_details.get('not_convertible'):
				out['uom'] = args.get("uom")
				out.update(uom_details)

		company_copy_fields = {
			'stock_adjustment_account': 'expense_account',
			'cost_center': 'cost_center'
		}
		for company_field, field in company_copy_fields.items():
			if not out.get(field):
				out[field] = frappe.get_cached_value('Company',  self.company,  company_field)

		out['expense_account'] = get_expense_account(self.company, stock_entry_type=self.stock_entry_type,
			is_opening=self.is_opening, expense_account=out.get('expense_account'))

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get('warehouse') else {}
		out.update(stock_and_rate)

		# Contents UOM
		out.alt_uom = item.alt_uom
		out.alt_uom_size = item.alt_uom_size if item.alt_uom else 1.0
		out.alt_uom_qty = flt(out.transfer_qty) * flt(out.alt_uom_size)

		if self.purpose == "Send to Subcontractor" and self.get("purchase_order") and args.get('item_code'):
			subcontract_items = frappe.get_all("Purchase Order Item Supplied",
				{"parent": self.purchase_order, "rm_item_code": args.get('item_code')}, "main_item_code")

			if subcontract_items and len(subcontract_items) == 1:
				out["subcontracted_item"] = subcontract_items[0].main_item_code

		return out

	@frappe.whitelist()
	def set_item_cost_centers(self, row=None):
		for d in self.get("items"):
			if d.get("item_code") and (not row or d.name == row):
				d.cost_center = get_default_cost_center(d.item_code, {
					"doctype": "Stock Entry",
					"company": self.company,
					"project": d.get('project') or self.get('project'),
					"cost_center": d.get('cost_center'),
					"customer": self.get("customer"),
				})

	def set_items_for_stock_in(self):
		self.items = []

		if self.outgoing_stock_entry and self.purpose == 'Receive at Warehouse':
			doc = frappe.get_doc('Stock Entry', self.outgoing_stock_entry)

			if doc.per_transferred == 100:
				frappe.throw(_("Goods are already received against the outward entry {0}")
					.format(doc.name))

			for d in doc.items:
				self.append('items', {
					's_warehouse': d.t_warehouse,
					'item_code': d.item_code,
					'qty': d.qty,
					'uom': d.uom,
					'against_stock_entry': d.parent,
					'ste_detail': d.name,
					'stock_uom': d.stock_uom,
					'conversion_factor': d.conversion_factor,
					'serial_no': d.serial_no,
					'batch_no': d.batch_no
				})

	def get_items(self):
		self.set('items', [])
		self.validate_work_order()

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		self.set_work_order_details()

		if self.bom_no:

			if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
					"Send to Subcontractor", "Material Transfer for Manufacture", "Material Consumption for Manufacture"]:

				if self.work_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials()
					if self.to_warehouse and self.pro_doc:
						for item in itervalues(item_dict):
							item["to_warehouse"] = self.pro_doc.wip_warehouse
					self.add_to_stock_entry_detail(item_dict)

				elif (self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
					and not self.pro_doc.skip_transfer and frappe.db.get_single_value("Manufacturing Settings",
					"backflush_raw_materials_based_on")== "Material Transferred for Manufacture"):
					self.get_transfered_raw_materials()

				elif self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture") and \
					frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "BOM" and \
					frappe.db.get_single_value("Manufacturing Settings", "material_consumption")== 1:
					self.get_unconsumed_raw_materials()
				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(flt(self.fg_completed_qty) + flt(self.scrap_qty))

					#Get PO Supplied Items Details
					if self.purchase_order and self.purpose == "Send to Subcontractor":
						#Get PO Supplied Items Details
						item_wh = frappe._dict(frappe.db.sql("""
							select rm_item_code, reserve_warehouse
							from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
							where po.name = poitemsup.parent
								and po.name = %s""",self.purchase_order))

					for item in itervalues(item_dict):
						if self.pro_doc and (cint(self.pro_doc.from_wip_warehouse) or not self.pro_doc.skip_transfer):
							item["from_warehouse"] = self.pro_doc.wip_warehouse
						elif self.pro_doc:
							required_item_dict = self.pro_doc.get_required_items_dict()
							required_item_row = required_item_dict.get(item.item_code)
							if required_item_row:
								item["from_warehouse"] = required_item_row.get('source_warehouse')
						#Get Reserve Warehouse from PO
						if self.purchase_order and self.purpose=="Send to Subcontractor":
							item["from_warehouse"] = item_wh.get(item.item_code)
						item["to_warehouse"] = self.to_warehouse if self.purpose=="Send to Subcontractor" else ""

					self.add_to_stock_entry_detail(item_dict)

			# fetch the serial_no of the first stock entry for the second stock entry
			if self.work_order and self.purpose == "Manufacture":
				self.set_serial_nos(self.work_order)

			if self.purpose in ("Manufacture", "Repack"):
				work_order = frappe.get_doc('Work Order', self.work_order) if self.work_order else frappe._dict()
				add_additional_cost(self, work_order)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.load_items_from_bom()

		self.set_scrap_items()
		self.set_actual_qty()
		self.calculate_rate_and_amount(raise_error_if_no_rate=False)

	def set_scrap_items(self):
		if self.purpose != "Send to Subcontractor" and self.purpose in ["Manufacture", "Repack"]:
			scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
			for item in itervalues(scrap_item_dict):
				item.idx = ''
				if self.pro_doc and self.pro_doc.scrap_warehouse:
					item["to_warehouse"] = self.pro_doc.scrap_warehouse

			self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

	def set_work_order_details(self):
		if not getattr(self, "pro_doc", None):
			self.pro_doc = frappe._dict()

		if self.work_order:
			# common validations
			if not self.pro_doc:
				self.pro_doc = frappe.get_doc('Work Order', self.work_order)

			if self.pro_doc:
				self.bom_no = self.pro_doc.bom_no
			else:
				# invalid work order
				self.work_order = None

	def load_items_from_bom(self):
		if self.work_order:
			item_code = self.pro_doc.production_item
			to_warehouse = self.pro_doc.fg_warehouse
		else:
			item_code = frappe.db.get_value("BOM", self.bom_no, "item")
			to_warehouse = self.to_warehouse

		item = frappe.get_cached_doc("Item", item_code)

		if not self.work_order and not to_warehouse:
			# in case of BOM
			to_warehouse = get_default_warehouse(item, {'company': self.company}, True)

		self.add_to_stock_entry_detail({
			item.name: {
				"to_warehouse": to_warehouse,
				"from_warehouse": "",
				"qty": self.fg_completed_qty,
				"item_name": item.item_name,
				"description": item.description,
				"stock_uom": item.stock_uom,
			}
		}, bom_no = self.bom_no)

	def get_bom_raw_materials(self, qty, scrap_qty=0):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty + scrap_qty,
			fetch_exploded = self.use_multi_level_bom, fetch_qty_in_stock_uom=False)

		used_alternative_items = get_used_alternative_items(work_order = self.work_order)
		for item in itervalues(item_dict):
			# if source warehouse presents in BOM set from_warehouse as bom source_warehouse
			if item["allow_alternative_item"]:
				item["allow_alternative_item"] = frappe.db.get_value('Work Order',
					self.work_order, "allow_alternative_item")

			item.from_warehouse = self.from_warehouse or item.source_warehouse or item.default_warehouse
			if item.item_code in used_alternative_items:
				alternative_item_data = used_alternative_items.get(item.item_code)
				item.item_code = alternative_item_data.item_code
				item.item_name = alternative_item_data.item_name
				item.stock_uom = alternative_item_data.stock_uom
				item.uom = alternative_item_data.uom
				item.conversion_factor = alternative_item_data.conversion_factor
				item.description = alternative_item_data.description

		return item_dict

	def get_bom_scrap_material(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = 0, fetch_scrap_items = 1)

		for item in itervalues(item_dict):
			item.from_warehouse = ""
		return item_dict

	def get_unconsumed_raw_materials(self):
		wo = frappe.get_doc("Work Order", self.work_order)
		wo_items = frappe.get_all('Work Order Item',
			filters={'parent': self.work_order},
			fields=["item_code", "uom", "stock_uom", "required_qty", "consumed_qty"]
			)

		for item in wo_items:
			qty = item.required_qty

			# Take into account consumption if there are any.
			if self.purpose == 'Manufacture':
				req_qty_each = flt(item.required_qty / wo.qty)
				if (flt(item.consumed_qty) != 0):
					remaining_qty = flt(item.consumed_qty) - (flt(wo.produced_qty) * req_qty_each)
					exhaust_qty = req_qty_each * wo.produced_qty
					if remaining_qty > exhaust_qty :
						if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
							qty =0
						else:
							qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
				else:
					qty = req_qty_each * flt(self.fg_completed_qty)

			if qty > 0:
				self.add_to_stock_entry_detail({
					item.item_code: {
						"from_warehouse": wo.wip_warehouse,
						"to_warehouse": "",
						"qty": qty,
						"uom": item.uom,
						"item_name": item.item_name,
						"description": item.description,
						"stock_uom": item.stock_uom,
					}
				})

	def get_transfered_raw_materials(self):
		transferred_materials = frappe.db.sql("""
			select
				item_name, original_item, item_code, sum(qty) as qty, sed.t_warehouse as warehouse,
				description, uom, stock_uom, expense_account, cost_center
			from `tabStock Entry` se,`tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1 and se.purpose='Material Transfer for Manufacture'
				and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
			group by sed.item_code, sed.t_warehouse
		""", self.work_order, as_dict=1)

		materials_already_backflushed = frappe.db.sql("""
			select
				item_code, sed.s_warehouse as warehouse, sum(qty) as qty
			from
				`tabStock Entry` se, `tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1
				and (se.purpose='Manufacture' or se.purpose='Material Consumption for Manufacture')
				and se.work_order= %s and ifnull(sed.s_warehouse, '') != ''
			group by sed.item_code, sed.s_warehouse
		""", self.work_order, as_dict=1)

		backflushed_materials= {}
		for d in materials_already_backflushed:
			backflushed_materials.setdefault(d.item_code,[]).append({d.warehouse: d.qty})

		po_qty = frappe.db.sql("""select qty, produced_qty, material_transferred_for_manufacturing from
			`tabWork Order` where name=%s""", self.work_order, as_dict=1)[0]

		manufacturing_qty = flt(po_qty.qty)
		produced_qty = flt(po_qty.produced_qty)
		trans_qty = flt(po_qty.material_transferred_for_manufacturing)

		for item in transferred_materials:
			qty= item.qty
			item_code = item.original_item or item.item_code
			req_items = frappe.get_all('Work Order Item',
				filters={'parent': self.work_order, 'item_code': item_code},
				fields=["required_qty", "consumed_qty"]
				)
			if not req_items:
				frappe.msgprint(_("Did not found transfered item {0} in Work Order {1}, the item not added in Stock Entry")
					.format(item_code, self.work_order))
				continue

			req_qty = flt(req_items[0].required_qty)
			req_qty_each = flt(req_qty / manufacturing_qty)
			consumed_qty = flt(req_items[0].consumed_qty)

			if trans_qty and manufacturing_qty > (produced_qty + flt(self.fg_completed_qty)):
				if qty >= req_qty:
					qty = (req_qty/trans_qty) * flt(self.fg_completed_qty)
				else:
					qty = qty - consumed_qty

				if self.purpose == 'Manufacture':
					# If Material Consumption is booked, must pull only remaining components to finish product
					if consumed_qty != 0:
						remaining_qty = consumed_qty - (produced_qty * req_qty_each)
						exhaust_qty = req_qty_each * produced_qty
						if remaining_qty > exhaust_qty :
							if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
								qty =0
							else:
								qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
					else:
						qty = req_qty_each * flt(self.fg_completed_qty)


			elif backflushed_materials.get(item.item_code):
				for d in backflushed_materials.get(item.item_code):
					if d.get(item.warehouse):
						if (qty > req_qty):
							qty = req_qty
							qty-= d.get(item.warehouse)

			if qty > 0:
				self.add_to_stock_entry_detail({
					item.item_code: {
						"from_warehouse": item.warehouse,
						"to_warehouse": "",
						"qty": qty,
						"item_name": item.item_name,
						"description": item.description,
						"uom": item.uom,
						"stock_uom": item.stock_uom,
						"expense_account": item.expense_account,
						"cost_center": item.cost_center,
						"original_item": item.original_item
					}
				})

	def get_pending_raw_materials(self):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_dict = self.get_pro_order_required_items()
		max_qty = flt(self.pro_doc.qty)
		for item, item_details in iteritems(item_dict):
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if desire_to_transfer <= pending_to_issue:
				item_dict[item]["qty"] = desire_to_transfer
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0

		# delete items with 0 qty
		for item in item_dict.keys():
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict

	def get_pro_order_required_items(self):
		item_dict = frappe._dict()
		pro_order = frappe.get_doc("Work Order", self.work_order)
		if not frappe.db.get_value("Warehouse", pro_order.wip_warehouse, "is_group"):
			wip_warehouse = pro_order.wip_warehouse
		else:
			wip_warehouse = None

		for d in pro_order.get("required_items"):
			if (flt(d.required_qty) > flt(d.transferred_qty) and
				(d.include_item_in_manufacturing or self.purpose != "Material Transfer for Manufacture")):
				item_row = d.as_dict()
				if d.source_warehouse and not frappe.db.get_value("Warehouse", d.source_warehouse, "is_group"):
					item_row["from_warehouse"] = d.source_warehouse

				item_row["to_warehouse"] = wip_warehouse
				if item_row["allow_alternative_item"]:
					item_row["allow_alternative_item"] = pro_order.allow_alternative_item

				item_dict.setdefault(d.item_code, item_row)

		return item_dict

	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		for d in item_dict:
			stock_uom = item_dict[d].get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

			se_child = self.append('items')
			se_child.s_warehouse = item_dict[d].get("from_warehouse")
			se_child.t_warehouse = item_dict[d].get("to_warehouse")
			se_child.item_code = item_dict[d].get('item_code') or cstr(d)
			se_child.uom = item_dict[d]["uom"] if item_dict[d].get("uom") else stock_uom
			se_child.stock_uom = stock_uom
			se_child.qty = flt(item_dict[d]["qty"], se_child.precision("qty"))

			se_child.expense_account = get_expense_account(self.company, stock_entry_type=self.stock_entry_type,
				is_opening=self.is_opening, expense_account=item_dict[d].get("expense_account"))
			se_child.cost_center = item_dict[d].get("cost_center")
			se_child.allow_alternative_item = item_dict[d].get("allow_alternative_item", 0)
			se_child.subcontracted_item = item_dict[d].get("main_item_code")

			for field in ["purchase_order_item", "original_item", "description", "item_name"]:
				if item_dict[d].get(field):
					se_child.set(field, item_dict[d].get(field))

			if se_child.s_warehouse==None:
				se_child.s_warehouse = self.from_warehouse
			if se_child.t_warehouse==None:
				se_child.t_warehouse = self.to_warehouse

			# in stock uom
			se_child.conversion_factor = flt(item_dict[d].get("conversion_factor")) or 1
			se_child.transfer_qty = flt(item_dict[d]["qty"]*se_child.conversion_factor, se_child.precision("transfer_qty"))

			self.set_missing_item_values(se_child)

			# to be assigned for finished item
			se_child.bom_no = bom_no

	def validate_with_material_request(self):
		for item in self.get("items"):
			if item.material_request:
				mreq_item = frappe.db.get_value("Material Request Item",
					{"name": item.material_request_item, "parent": item.material_request},
					["item_code", "warehouse", "idx"], as_dict=True)
				if mreq_item.item_code != item.item_code or \
				mreq_item.warehouse != (item.s_warehouse if self.purpose== "Material Issue" else item.t_warehouse):
					frappe.throw(_("Item or Warehouse for row {0} does not match Material Request").format(item.idx),
						frappe.MappingMismatchError)

	def validate_batch(self):
		if self.purpose in ["Material Transfer for Manufacture", "Manufacture", "Repack", "Send to Subcontractor"]:
			for item in self.get("items"):
				if item.batch_no:
					disabled = frappe.db.get_value("Batch", item.batch_no, "disabled")
					if disabled == 0:
						expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
						if expiry_date:
							if getdate(self.posting_date) > getdate(expiry_date):
								frappe.throw(_("Batch {0} of Item {1} has expired.")
									.format(item.batch_no, item.item_code))
					else:
						frappe.throw(_("Batch {0} of Item {1} is disabled.")
							.format(item.batch_no, item.item_code))

	def update_purchase_order_supplied_items(self):
		#Get PO Supplied Items Details
		item_wh = frappe._dict(frappe.db.sql("""
			select rm_item_code, reserve_warehouse
			from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
			where po.name = poitemsup.parent
			and po.name = %s""", self.purchase_order))

		#Update Supplied Qty in PO Supplied Items

		frappe.db.sql("""UPDATE `tabPurchase Order Item Supplied` pos
			SET
				pos.supplied_qty = IFNULL((SELECT ifnull(sum(transfer_qty), 0)
					FROM
						`tabStock Entry Detail` sed, `tabStock Entry` se
					WHERE
						(pos.name = sed.purchase_order_item OR sed.subcontracted_item = pos.main_item_code)
						AND sed.docstatus = 1 AND se.name = sed.parent and se.purchase_order = %(po)s
				), 0)
			WHERE pos.docstatus = 1 and pos.parent = %(po)s""", {"po": self.purchase_order})

		#Update reserved sub contracted quantity in bin based on Supplied Item Details and
		for d in self.get("items"):
			item_code = d.get('original_item') or d.get('item_code')
			reserve_warehouse = item_wh.get(item_code)
			stock_bin = get_bin(item_code, reserve_warehouse)
			stock_bin.update_reserved_qty_for_sub_contracting()

	def update_so_in_serial_number(self):
		so_name, item_code = frappe.db.get_value("Work Order", self.work_order, ["sales_order", "production_item"])
		if so_name and item_code:
			qty_to_reserve = get_reserved_qty_for_so(so_name, item_code)
			if qty_to_reserve:
				reserved_qty = frappe.db.sql("""select count(name) from `tabSerial No` where item_code=%s and
					sales_order=%s""", (item_code, so_name))
				if reserved_qty and reserved_qty[0][0]:
					qty_to_reserve -= reserved_qty[0][0]
				if qty_to_reserve > 0:
					for item in self.items:
						if item.item_code == item_code:
							serial_nos = (item.serial_no).split("\n")
							for serial_no in serial_nos:
								if qty_to_reserve > 0:
									frappe.db.set_value("Serial No", serial_no, "sales_order", so_name)
									qty_to_reserve -=1

	def validate_reserved_serial_no_consumption(self):
		for item in self.items:
			if item.s_warehouse and not item.t_warehouse and item.serial_no:
				for sr in get_serial_nos(item.serial_no):
					sales_order = frappe.db.get_value("Serial No", sr, "sales_order")
					if sales_order:
						frappe.throw(_("Item {0} (Serial No: {1}) cannot be consumed as is reserverd\
						 to fullfill Sales Order {2}.").format(item.item_code, sr, sales_order))

	def update_quality_inspection(self):
		if self.inspection_required:
			reference_type = reference_name = ''
			if self.docstatus == 1:
				reference_name = self.name
				reference_type = 'Stock Entry'

			for d in self.items:
				if d.quality_inspection:
					frappe.db.set_value("Quality Inspection", d.quality_inspection, {
						'reference_type': reference_type,
						'reference_name': reference_name
					})


@frappe.whitelist()
def move_sample_to_retention_warehouse(company, items):
	if isinstance(items, string_types):
		items = json.loads(items)
	retention_warehouse = frappe.db.get_single_value('Stock Settings', 'sample_retention_warehouse')
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.company = company
	stock_entry.purpose = "Material Transfer"
	stock_entry.set_stock_entry_type()
	for item in items:
		if item.get('sample_quantity') and item.get('batch_no'):
			sample_quantity = validate_sample_quantity(item.get('item_code'), item.get('sample_quantity'),
				item.get('transfer_qty') or item.get('qty'), item.get('batch_no'))
			if sample_quantity:
				sample_serial_nos = ''
				if item.get('serial_no'):
					serial_nos = (item.get('serial_no')).split()
					if serial_nos and len(serial_nos) > item.get('sample_quantity'):
						serial_no_list = serial_nos[:-(len(serial_nos)-item.get('sample_quantity'))]
						sample_serial_nos = '\n'.join(serial_no_list)

				stock_entry.append("items", {
					"item_code": item.get('item_code'),
					"s_warehouse": item.get('t_warehouse'),
					"t_warehouse": retention_warehouse,
					"qty": item.get('sample_quantity'),
					"basic_rate": item.get('valuation_rate'),
					'uom': item.get('uom'),
					'stock_uom': item.get('stock_uom'),
					"conversion_factor": 1.0,
					"serial_no": sample_serial_nos,
					'batch_no': item.get('batch_no')
				})
	if stock_entry.get('items'):
		return stock_entry.as_dict()


@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.purpose = 'Receive at Warehouse'
		target.set_stock_entry_type()

	def update_item(source_doc, target_doc, source_parent, target_parent):
		target_doc.t_warehouse = ''
		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty - source_doc.transferred_qty

	doclist = get_mapped_doc("Stock Entry", source_name, 	{
		"Stock Entry": {
			"doctype": "Stock Entry",
			"field_map": {
				"name": "outgoing_stock_entry"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Stock Entry Detail": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"name": "ste_detail",
				"parent": "against_stock_entry",
				"serial_no": "serial_no",
				"batch_no": "batch_no"
			},
			"postprocess": update_item,
			"condition": lambda doc, source, target: flt(doc.qty) - flt(doc.transferred_qty) > 0.01
		},
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def get_work_order_details(work_order, company):
	work_order = frappe.get_doc("Work Order", work_order)
	pending_qty_to_produce = flt(work_order.qty) - flt(work_order.produced_qty)

	return {
		"from_bom": 1,
		"bom_no": work_order.bom_no,
		"use_multi_level_bom": work_order.use_multi_level_bom,
		"wip_warehouse": work_order.wip_warehouse,
		"fg_warehouse": work_order.fg_warehouse,
		"fg_completed_qty": pending_qty_to_produce
	}


def get_operating_cost_per_unit(work_order=None, bom_no=None):
	operating_cost_per_unit = 0
	if work_order:
		for d in work_order.get("operations"):
			if flt(d.completed_qty):
				operating_cost_per_unit += flt(d.actual_operating_cost) / flt(d.completed_qty)
			elif work_order.qty:
				operating_cost_per_unit += flt(d.planned_operating_cost) / flt(work_order.qty)
	elif bom_no:
		bom = frappe.db.get_value("BOM", bom_no, ["operating_cost", "quantity"], as_dict=1)
		if bom.quantity:
			operating_cost_per_unit = flt(bom.operating_cost) / flt(bom.quantity)

	return operating_cost_per_unit


def get_additional_operating_costs(work_order=None, bom_no=None, use_multi_level_bom=0):
	from erpnext.manufacturing.doctype.bom.bom import get_additional_operating_cost_per_unit

	additional_costs = []

	if work_order:
		additional_costs = work_order.get("additional_costs")
	elif bom_no:
		additional_costs = get_additional_operating_cost_per_unit(bom_no, use_multi_level_bom)

	return additional_costs


def get_used_alternative_items(purchase_order=None, work_order=None):
	cond = ""

	if purchase_order:
		cond = "and ste.purpose = 'Send to Subcontractor' and ste.purchase_order = '{0}'".format(purchase_order)
	elif work_order:
		cond = "and ste.purpose = 'Material Transfer for Manufacture' and ste.work_order = '{0}'".format(work_order)

	if not cond: return {}

	used_alternative_items = {}
	data = frappe.db.sql(""" select sted.original_item, sted.uom, sted.conversion_factor,
			sted.item_code, sted.item_name, sted.conversion_factor,sted.stock_uom, sted.description
		from
			`tabStock Entry` ste, `tabStock Entry Detail` sted
		where
			sted.parent = ste.name and ste.docstatus = 1 and sted.original_item !=  sted.item_code
			{0} """.format(cond), as_dict=1)

	for d in data:
		used_alternative_items[d.original_item] = d

	return used_alternative_items


def get_valuation_rate_for_finished_good_entry(work_order):
	work_order_qty = flt(frappe.get_cached_value("Work Order",
		work_order, 'material_transferred_for_manufacturing'))

	field = "(SUM(total_outgoing_value) / %s) as valuation_rate" % (work_order_qty)

	stock_data = frappe.get_all("Stock Entry",
		fields = field,
		filters = {
			"docstatus": 1,
			"purpose": "Material Transfer for Manufacture",
			"work_order": work_order
		}
	)

	if stock_data:
		return stock_data[0].valuation_rate


@frappe.whitelist()
def get_uom_details(item_code, uom, qty):
	"""Returns dict `{"conversion_factor": [value], "transfer_qty": qty * [value]}`

	:param args: dict with `item_code`, `uom` and `qty`"""
	conversion = get_conversion_factor(item_code, uom)
	conversion_factor = flt(conversion.get("conversion_factor"))
	not_convertible = cint(conversion.get('not_convertible'))

	if not conversion_factor:
		frappe.msgprint(_("UOM coversion factor required for UOM: {0} in Item: {1}")
			.format(uom, item_code))
		ret = {'uom' : ''}
	else:
		ret = {
			'conversion_factor'		: flt(conversion_factor),
			'transfer_qty'			: flt(qty) * flt(conversion_factor),
			'not_convertible'		: not_convertible
		}
	return ret


@frappe.whitelist()
def get_expired_batch_items():
	return frappe.db.sql("""select b.item, sum(sle.actual_qty) as qty, sle.batch_no, sle.warehouse, sle.stock_uom\
	from `tabBatch` b, `tabStock Ledger Entry` sle
	where b.expiry_date <= %s
	and b.expiry_date is not NULL
	and b.batch_id = sle.batch_no
	group by sle.warehouse, sle.item_code, sle.batch_no""",(nowdate()), as_dict=1)


@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	ret = {}
	if args.warehouse and args.item_code:
		args.update({
			"posting_date": args.posting_date,
			"posting_time": args.posting_time,
		})
		ret = {
			"actual_qty" : get_previous_sle(args).get("qty_after_transaction") or 0,
			"basic_rate" : get_incoming_rate(args) if not args.get('customer_provided') else 0
		}
	return ret


@frappe.whitelist()
def validate_sample_quantity(item_code, sample_quantity, qty, batch_no = None):
	if cint(qty) < cint(sample_quantity):
		frappe.throw(_("Sample quantity {0} cannot be more than received quantity {1}").format(sample_quantity, qty))
	retention_warehouse = frappe.db.get_single_value('Stock Settings', 'sample_retention_warehouse')
	retainted_qty = 0
	if batch_no:
		retainted_qty = get_batch_qty(batch_no, retention_warehouse, item_code)
	max_retain_qty = frappe.get_value('Item', item_code, 'sample_quantity')
	if retainted_qty >= max_retain_qty:
		frappe.msgprint(_("Maximum Samples - {0} have already been retained for Batch {1} and Item {2} in Batch {3}.").
			format(retainted_qty, batch_no, item_code, batch_no), alert=True)
		sample_quantity = 0
	qty_diff = max_retain_qty-retainted_qty
	if cint(sample_quantity) > cint(qty_diff):
		frappe.msgprint(_("Maximum Samples - {0} can be retained for Batch {1} and Item {2}.").
			format(max_retain_qty, batch_no, item_code), alert=True)
		sample_quantity = qty_diff
	return sample_quantity


@frappe.whitelist()
def get_expense_account(company, stock_entry_type=None, is_opening='No', expense_account=None):
	if company and is_opening == 'Yes':
		return frappe.get_cached_value('Company', company, 'temporary_opening_account')

	if stock_entry_type:
		account = frappe.get_cached_value('Stock Entry Type', stock_entry_type, 'expense_account')
		if account:
			return account

	if frappe.get_cached_value('Company', company, 'stock_adjustment_account'):
		return frappe.get_cached_value('Company', company, 'stock_adjustment_account')

	return expense_account


@frappe.whitelist()
def get_item_expense_accounts(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	expense_account_item = {}
	for d in args.get('items'):
		account = get_expense_account(company=args.company, stock_entry_type=args.stock_entry_type,
			is_opening=args.is_opening, expense_account=d.get('expense_account'))
		expense_account_item[d.get("name")] = account

	return expense_account_item
