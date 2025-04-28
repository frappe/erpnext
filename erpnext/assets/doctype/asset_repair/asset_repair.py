# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
<<<<<<< HEAD
from frappe.query_builder import DocType
from frappe.utils import cint, flt, get_link_to_form, getdate, time_diff_in_hours
=======
from frappe.utils import add_months, cint, flt, get_link_to_form, getdate, time_diff_in_hours
>>>>>>> 7c4cf3e834 (Favicon.svg)

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.assets.doctype.asset.asset import get_asset_account
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
<<<<<<< HEAD
	reschedule_depreciation,
=======
	make_new_active_asset_depr_schedules_and_cancel_current_ones,
>>>>>>> 7c4cf3e834 (Favicon.svg)
)
from erpnext.controllers.accounts_controller import AccountsController


class AssetRepair(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.asset_repair_consumed_item.asset_repair_consumed_item import (
			AssetRepairConsumedItem,
		)
<<<<<<< HEAD
		from erpnext.assets.doctype.asset_repair_purchase_invoice.asset_repair_purchase_invoice import (
			AssetRepairPurchaseInvoice,
		)
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)

		actions_performed: DF.LongText | None
		amended_from: DF.Link | None
		asset: DF.Link
		asset_name: DF.ReadOnly | None
		capitalize_repair_cost: DF.Check
		company: DF.Link | None
		completion_date: DF.Datetime | None
<<<<<<< HEAD
		consumed_items_cost: DF.Currency
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		cost_center: DF.Link | None
		description: DF.LongText | None
		downtime: DF.Data | None
		failure_date: DF.Datetime
		increase_in_asset_life: DF.Int
<<<<<<< HEAD
		invoices: DF.Table[AssetRepairPurchaseInvoice]
		naming_series: DF.Literal["ACC-ASR-.YYYY.-"]
		project: DF.Link | None
		repair_cost: DF.Currency
		repair_status: DF.Literal["Pending", "Completed", "Cancelled"]
=======
		naming_series: DF.Literal["ACC-ASR-.YYYY.-"]
		project: DF.Link | None
		purchase_invoice: DF.Link | None
		repair_cost: DF.Currency
		repair_status: DF.Literal["Pending", "Completed", "Cancelled"]
		stock_consumption: DF.Check
>>>>>>> 7c4cf3e834 (Favicon.svg)
		stock_items: DF.Table[AssetRepairConsumedItem]
		total_repair_cost: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.asset_doc = frappe.get_doc("Asset", self.asset)
<<<<<<< HEAD
		self.validate_asset()
		self.validate_dates()
		self.validate_purchase_invoices()
		self.update_status()
		self.calculate_consumed_items_cost()
		self.calculate_repair_cost()
		self.calculate_total_repair_cost()
		self.check_repair_status()

	def validate_asset(self):
		if self.asset_doc.status in ("Sold", "Fully Depreciated", "Scrapped"):
			frappe.throw(
				_("Asset {0} is in {1} status and cannot be repaired.").format(
					get_link_to_form("Asset", self.asset), self.asset_doc.status
				)
			)

	def validate_dates(self):
		if self.completion_date and (getdate(self.failure_date) > getdate(self.completion_date)):
=======
		self.validate_dates()
		self.update_status()

		if self.get("stock_items"):
			self.set_stock_items_cost()
		self.calculate_total_repair_cost()

	def validate_dates(self):
		if self.completion_date and (self.failure_date > self.completion_date):
>>>>>>> 7c4cf3e834 (Favicon.svg)
			frappe.throw(
				_("Completion Date can not be before Failure Date. Please adjust the dates accordingly.")
			)

<<<<<<< HEAD
	def validate_purchase_invoices(self):
		for d in self.invoices:
			self.validate_purchase_invoice_status(d.purchase_invoice)
			invoice_items = self.get_invoice_items(d.purchase_invoice)
			self.validate_service_purchase_invoice(d.purchase_invoice, invoice_items)
			self.validate_expense_account(d, invoice_items)
			self.validate_purchase_invoice_repair_cost(d, invoice_items)

	def validate_purchase_invoice_status(self, purchase_invoice):
		docstatus = frappe.db.get_value("Purchase Invoice", purchase_invoice, "docstatus")
		if docstatus == 0:
			frappe.throw(
				_("{0} is still in Draft. Please submit it before saving the Asset Repair.").format(
					get_link_to_form("Purchase Invoice", purchase_invoice)
				)
			)

	def get_invoice_items(self, pi):
		invoice_items = frappe.get_all(
			"Purchase Invoice Item",
			filters={"parent": pi},
			fields=["item_code", "expense_account", "base_net_amount"],
		)

		return invoice_items

	def validate_service_purchase_invoice(self, purchase_invoice, invoice_items):
		service_item_exists = False
		for item in invoice_items:
			if frappe.db.get_value("Item", item.item_code, "is_stock_item") == 0:
				service_item_exists = True
				break

		if not service_item_exists:
			frappe.throw(
				_("Service item not present in Purchase Invoice {0}").format(
					get_link_to_form("Purchase Invoice", purchase_invoice)
				)
			)

	def validate_expense_account(self, row, invoice_items):
		pi_expense_accounts = set([item.expense_account for item in invoice_items])
		if row.expense_account not in pi_expense_accounts:
			frappe.throw(
				_("Expense account {0} not present in Purchase Invoice {1}").format(
					row.expense_account, get_link_to_form("Purchase Invoice", row.purchase_invoice)
				)
			)

	def validate_purchase_invoice_repair_cost(self, row, invoice_items):
		pi_net_total = sum([flt(item.base_net_amount) for item in invoice_items])
		if flt(row.repair_cost) > pi_net_total:
			frappe.throw(
				_("Repair cost cannot be greater than purchase invoice base net total {0}").format(
					pi_net_total
				)
			)

	def update_status(self):
		if self.repair_status == "Pending" and self.asset_doc.status != "Out of Order":
			frappe.db.set_value("Asset", self.asset, "status", "Out of Order")
			self.add_asset_activity(
=======
	def update_status(self):
		if self.repair_status == "Pending" and self.asset_doc.status != "Out of Order":
			frappe.db.set_value("Asset", self.asset, "status", "Out of Order")
			add_asset_activity(
				self.asset,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				_("Asset out of order due to Asset Repair {0}").format(
					get_link_to_form("Asset Repair", self.name)
				),
			)
		else:
			self.asset_doc.set_status()

<<<<<<< HEAD
	def calculate_consumed_items_cost(self):
		consumed_items_cost = 0.0
		for item in self.get("stock_items"):
			item.total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)
			consumed_items_cost += item.total_value
		self.consumed_items_cost = consumed_items_cost

	def calculate_repair_cost(self):
		self.repair_cost = sum(flt(pi.repair_cost) for pi in self.invoices)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost) + flt(self.consumed_items_cost)

	def on_submit(self):
		self.decrease_stock_quantity()

		if self.get("capitalize_repair_cost"):
			self.update_asset_value()
			self.set_increase_in_asset_life()

			depreciation_note = self.get_depreciation_note()
			reschedule_depreciation(self.asset_doc, depreciation_note)
			self.add_asset_activity()

			self.make_gl_entries()

	def cancel_sabb(self):
		for row in self.stock_items:
			if sabb := row.serial_and_batch_bundle:
				row.db_set("serial_and_batch_bundle", None)
				doc = frappe.get_doc("Serial and Batch Bundle", sabb)
				doc.cancel()

	def on_cancel(self):
		self.asset_doc = frappe.get_doc("Asset", self.asset)
		if self.get("capitalize_repair_cost"):
			self.update_asset_value()
			self.make_gl_entries(cancel=True)
			self.set_increase_in_asset_life()

			depreciation_note = self.get_depreciation_note()
			reschedule_depreciation(self.asset_doc, depreciation_note)
			self.add_asset_activity()

		self.cancel_sabb()
=======
	def set_stock_items_cost(self):
		for item in self.get("stock_items"):
			item.total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost)

		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		self.total_repair_cost += total_value_of_stock_consumed

	def before_submit(self):
		self.check_repair_status()

		self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

		if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
			self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

			self.increase_asset_value()

			if self.capitalize_repair_cost:
				self.asset_doc.total_asset_cost += self.repair_cost
				self.asset_doc.additional_asset_cost += self.repair_cost

			if self.get("stock_consumption"):
				self.check_for_stock_items_and_warehouse()
				self.decrease_stock_quantity()
			if self.get("capitalize_repair_cost"):
				self.make_gl_entries()
				if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
					self.modify_depreciation_schedule()

				notes = _(
					"This schedule was created when Asset {0} was repaired through Asset Repair {1}."
				).format(
					get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
					get_link_to_form(self.doctype, self.name),
				)
				self.asset_doc.flags.ignore_validate_update_after_submit = True
				make_new_active_asset_depr_schedules_and_cancel_current_ones(
					self.asset_doc, notes, ignore_booked_entry=True
				)
				self.asset_doc.save()

				add_asset_activity(
					self.asset,
					_("Asset updated after completion of Asset Repair {0}").format(
						get_link_to_form("Asset Repair", self.name)
					),
				)

	def before_cancel(self):
		self.asset_doc = frappe.get_doc("Asset", self.asset)

		self.asset_doc.flags.increase_in_asset_value_due_to_repair = False

		if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
			self.asset_doc.flags.increase_in_asset_value_due_to_repair = True

			self.decrease_asset_value()

			if self.capitalize_repair_cost:
				self.asset_doc.total_asset_cost -= self.repair_cost
				self.asset_doc.additional_asset_cost -= self.repair_cost

			if self.get("capitalize_repair_cost"):
				self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
				self.make_gl_entries(cancel=True)
				if self.asset_doc.calculate_depreciation and self.increase_in_asset_life:
					self.revert_depreciation_schedule_on_cancellation()

				notes = _(
					"This schedule was created when Asset {0}'s Asset Repair {1} was cancelled."
				).format(
					get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
					get_link_to_form(self.doctype, self.name),
				)
				self.asset_doc.flags.ignore_validate_update_after_submit = True
				make_new_active_asset_depr_schedules_and_cancel_current_ones(
					self.asset_doc, notes, ignore_booked_entry=True
				)
				self.asset_doc.save()

				add_asset_activity(
					self.asset,
					_("Asset updated after cancellation of Asset Repair {0}").format(
						get_link_to_form("Asset Repair", self.name)
					),
				)
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def after_delete(self):
		frappe.get_doc("Asset", self.asset).set_status()

	def check_repair_status(self):
<<<<<<< HEAD
		if self.repair_status == "Pending" and self.docstatus == 1:
			frappe.throw(_("Please update Repair Status."))

	def update_asset_value(self):
		total_repair_cost = self.total_repair_cost if self.docstatus == 1 else -1 * self.total_repair_cost

		self.asset_doc.total_asset_cost += flt(total_repair_cost)
		self.asset_doc.additional_asset_cost += flt(total_repair_cost)

		if self.asset_doc.calculate_depreciation:
			for row in self.asset_doc.finance_books:
				row.value_after_depreciation += flt(total_repair_cost)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.save()

	def get_total_value_of_stock_consumed(self):
		return sum([flt(item.total_value) for item in self.get("stock_items")])

	def decrease_stock_quantity(self):
		if not self.get("stock_items"):
			return

		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": self.company,
				"asset_repair": self.name,
			}
		)
=======
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def check_for_stock_items_and_warehouse(self):
		if not self.get("stock_items"):
			frappe.throw(_("Please enter Stock Items consumed during the Repair."), title=_("Missing Items"))

	def increase_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()

		if self.asset_doc.calculate_depreciation:
			for row in self.asset_doc.finance_books:
				row.value_after_depreciation += total_value_of_stock_consumed

				if self.capitalize_repair_cost:
					row.value_after_depreciation += self.repair_cost

	def decrease_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()

		if self.asset_doc.calculate_depreciation:
			for row in self.asset_doc.finance_books:
				row.value_after_depreciation -= total_value_of_stock_consumed

				if self.capitalize_repair_cost:
					row.value_after_depreciation -= self.repair_cost

	def get_total_value_of_stock_consumed(self):
		total_value_of_stock_consumed = 0
		if self.get("stock_consumption"):
			for item in self.get("stock_items"):
				total_value_of_stock_consumed += item.total_value

		return total_value_of_stock_consumed

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc(
			{"doctype": "Stock Entry", "stock_entry_type": "Material Issue", "company": self.company}
		)
		stock_entry.asset_repair = self.name
>>>>>>> 7c4cf3e834 (Favicon.svg)

		for stock_item in self.get("stock_items"):
			self.validate_serial_no(stock_item)

			stock_entry.append(
				"items",
				{
					"s_warehouse": stock_item.warehouse,
					"item_code": stock_item.item_code,
					"qty": stock_item.consumed_quantity,
					"basic_rate": stock_item.valuation_rate,
					"serial_and_batch_bundle": stock_item.serial_and_batch_bundle,
					"cost_center": self.cost_center,
					"project": self.project,
				},
			)

		stock_entry.insert()
		stock_entry.submit()

	def validate_serial_no(self, stock_item):
		if not stock_item.serial_and_batch_bundle and frappe.get_cached_value(
			"Item", stock_item.item_code, "has_serial_no"
		):
			msg = f"Serial No Bundle is mandatory for Item {stock_item.item_code}"
<<<<<<< HEAD
			frappe.throw(_(msg), title=_("Missing Serial No Bundle"))
=======
			frappe.throw(msg, title=_("Missing Serial No Bundle"))
>>>>>>> 7c4cf3e834 (Favicon.svg)

		if stock_item.serial_and_batch_bundle:
			values_to_update = {
				"type_of_transaction": "Outward",
				"voucher_type": "Stock Entry",
			}

			frappe.db.set_value(
				"Serial and Batch Bundle", stock_item.serial_and_batch_bundle, values_to_update
			)

	def make_gl_entries(self, cancel=False):
<<<<<<< HEAD
		if cancel:
			self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")

=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		if flt(self.total_repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entries = []

		fixed_asset_account = get_asset_account("fixed_asset_account", asset=self.asset, company=self.company)
		self.get_gl_entries_for_repair_cost(gl_entries, fixed_asset_account)
		self.get_gl_entries_for_consumed_items(gl_entries, fixed_asset_account)

		return gl_entries

	def get_gl_entries_for_repair_cost(self, gl_entries, fixed_asset_account):
		if flt(self.repair_cost) <= 0:
			return

<<<<<<< HEAD
		debit_against_account = set()

		for pi in self.invoices:
			debit_against_account.add(pi.expense_account)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": pi.expense_account,
						"credit": pi.repair_cost,
						"credit_in_account_currency": pi.repair_cost,
						"against": fixed_asset_account,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"cost_center": self.cost_center,
						"posting_date": self.completion_date,
						"company": self.company,
					},
					item=self,
				)
			)
		debit_against_account = ", ".join(debit_against_account)
=======
		pi_expense_account = (
			frappe.get_doc("Purchase Invoice", self.purchase_invoice).items[0].expense_account
		)

>>>>>>> 7c4cf3e834 (Favicon.svg)
		gl_entries.append(
			self.get_gl_dict(
				{
					"account": fixed_asset_account,
					"debit": self.repair_cost,
					"debit_in_account_currency": self.repair_cost,
<<<<<<< HEAD
					"against": debit_against_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"posting_date": self.completion_date,
					"against_voucher_type": "Purchase Invoice",
=======
					"against": pi_expense_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"posting_date": getdate(),
					"against_voucher_type": "Purchase Invoice",
					"against_voucher": self.purchase_invoice,
					"company": self.company,
				},
				item=self,
			)
		)

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": pi_expense_account,
					"credit": self.repair_cost,
					"credit_in_account_currency": self.repair_cost,
					"against": fixed_asset_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"posting_date": getdate(),
>>>>>>> 7c4cf3e834 (Favicon.svg)
					"company": self.company,
				},
				item=self,
			)
		)

	def get_gl_entries_for_consumed_items(self, gl_entries, fixed_asset_account):
<<<<<<< HEAD
		if not self.get("stock_items"):
=======
		if not (self.get("stock_consumption") and self.get("stock_items")):
>>>>>>> 7c4cf3e834 (Favicon.svg)
			return

		# creating GL Entries for each row in Stock Items based on the Stock Entry created for it
		stock_entry = frappe.get_doc("Stock Entry", {"asset_repair": self.name})

		default_expense_account = None
		if not erpnext.is_perpetual_inventory_enabled(self.company):
			default_expense_account = frappe.get_cached_value(
				"Company", self.company, "default_expense_account"
			)
			if not default_expense_account:
				frappe.throw(_("Please set default Expense Account in Company {0}").format(self.company))

		for item in stock_entry.items:
			if flt(item.amount) > 0:
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": item.expense_account or default_expense_account,
							"credit": item.amount,
							"credit_in_account_currency": item.amount,
							"against": fixed_asset_account,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"cost_center": self.cost_center,
<<<<<<< HEAD
							"posting_date": self.completion_date,
=======
							"posting_date": getdate(),
>>>>>>> 7c4cf3e834 (Favicon.svg)
							"company": self.company,
						},
						item=self,
					)
				)

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": fixed_asset_account,
							"debit": item.amount,
							"debit_in_account_currency": item.amount,
							"against": item.expense_account or default_expense_account,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"cost_center": self.cost_center,
<<<<<<< HEAD
							"posting_date": self.completion_date,
=======
							"posting_date": getdate(),
>>>>>>> 7c4cf3e834 (Favicon.svg)
							"against_voucher_type": "Stock Entry",
							"against_voucher": stock_entry.name,
							"company": self.company,
						},
						item=self,
					)
				)

<<<<<<< HEAD
	def set_increase_in_asset_life(self):
		if self.asset_doc.calculate_depreciation and cint(self.increase_in_asset_life) > 0:
			for row in self.asset_doc.finance_books:
				row.increase_in_asset_life = cint(row.increase_in_asset_life) + (
					cint(self.increase_in_asset_life) * (1 if self.docstatus == 1 else -1)
				)
				row.db_update()

	def get_depreciation_note(self):
		return _("This schedule was created when Asset {0} was repaired through Asset Repair {1}.").format(
			get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
			get_link_to_form(self.doctype, self.name),
		)

	def add_asset_activity(self, subject=None):
		if not subject:
			subject = _("Asset updated due to Asset Repair {0} {1}.").format(
				get_link_to_form(self.doctype, self.name),
				"submission" if self.docstatus == 1 else "cancellation",
			)

		add_asset_activity(self.asset, subject)
=======
	def modify_depreciation_schedule(self):
		for row in self.asset_doc.finance_books:
			row.total_number_of_depreciations += self.increase_in_asset_life / row.frequency_of_depreciation

			self.asset_doc.flags.increase_in_asset_life = False
			extra_months = self.increase_in_asset_life % row.frequency_of_depreciation
			if extra_months != 0:
				self.calculate_last_schedule_date(self.asset_doc, row, extra_months)

	# to help modify depreciation schedule when increase_in_asset_life is not a multiple of frequency_of_depreciation
	def calculate_last_schedule_date(self, asset, row, extra_months):
		asset.flags.increase_in_asset_life = True
		number_of_pending_depreciations = cint(row.total_number_of_depreciations) - cint(
			asset.opening_number_of_booked_depreciations
		)

		depr_schedule = get_depr_schedule(asset.name, "Active", row.finance_book)

		# the Schedule Date in the final row of the old Depreciation Schedule
		last_schedule_date = depr_schedule[len(depr_schedule) - 1].schedule_date

		# the Schedule Date in the final row of the new Depreciation Schedule
		asset.to_date = add_months(last_schedule_date, extra_months)

		# the latest possible date at which the depreciation can occur, without increasing the Total Number of Depreciations
		# if depreciations happen yearly and the Depreciation Posting Date is 01-01-2020, this could be 01-01-2021, 01-01-2022...
		schedule_date = add_months(
			row.depreciation_start_date,
			number_of_pending_depreciations * cint(row.frequency_of_depreciation),
		)

		if asset.to_date > schedule_date:
			row.total_number_of_depreciations += 1

	def revert_depreciation_schedule_on_cancellation(self):
		for row in self.asset_doc.finance_books:
			row.total_number_of_depreciations -= self.increase_in_asset_life / row.frequency_of_depreciation

			self.asset_doc.flags.increase_in_asset_life = False
			extra_months = self.increase_in_asset_life % row.frequency_of_depreciation
			if extra_months != 0:
				self.calculate_last_schedule_date_before_modification(self.asset_doc, row, extra_months)

	def calculate_last_schedule_date_before_modification(self, asset, row, extra_months):
		asset.flags.increase_in_asset_life = True
		number_of_pending_depreciations = cint(row.total_number_of_depreciations) - cint(
			asset.opening_number_of_booked_depreciations
		)

		depr_schedule = get_depr_schedule(asset.name, "Active", row.finance_book)

		# the Schedule Date in the final row of the modified Depreciation Schedule
		last_schedule_date = depr_schedule[len(depr_schedule) - 1].schedule_date

		# the Schedule Date in the final row of the original Depreciation Schedule
		asset.to_date = add_months(last_schedule_date, -extra_months)

		# the latest possible date at which the depreciation can occur, without decreasing the Total Number of Depreciations
		# if depreciations happen yearly and the Depreciation Posting Date is 01-01-2020, this could be 01-01-2021, 01-01-2022...
		schedule_date = add_months(
			row.depreciation_start_date,
			(number_of_pending_depreciations - 1) * cint(row.frequency_of_depreciation),
		)

		if asset.to_date < schedule_date:
			row.total_number_of_depreciations -= 1
>>>>>>> 7c4cf3e834 (Favicon.svg)


@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)
<<<<<<< HEAD


@frappe.whitelist()
def get_purchase_invoice(doctype, txt, searchfield, start, page_len, filters):
	PurchaseInvoice = DocType("Purchase Invoice")
	PurchaseInvoiceItem = DocType("Purchase Invoice Item")
	Item = DocType("Item")

	return (
		frappe.qb.from_(PurchaseInvoice)
		.join(PurchaseInvoiceItem)
		.on(PurchaseInvoiceItem.parent == PurchaseInvoice.name)
		.join(Item)
		.on(Item.name == PurchaseInvoiceItem.item_code)
		.select(PurchaseInvoice.name)
		.where(
			(Item.is_stock_item == 0)
			& (Item.is_fixed_asset == 0)
			& (PurchaseInvoice.company == filters.get("company"))
			& (PurchaseInvoice.docstatus == 1)
		)
	).run(as_list=1)


@frappe.whitelist()
def get_expense_accounts(doctype, txt, searchfield, start, page_len, filters):
	PurchaseInvoiceItem = DocType("Purchase Invoice Item")
	return (
		frappe.qb.from_(PurchaseInvoiceItem)
		.select(PurchaseInvoiceItem.expense_account)
		.distinct()
		.where(PurchaseInvoiceItem.parent == filters.get("purchase_invoice"))
	).run(as_list=1)
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
