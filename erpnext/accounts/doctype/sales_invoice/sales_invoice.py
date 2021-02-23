# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, getdate, add_days, cstr, nowdate, get_link_to_form, formatdate
from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date, get_party_details
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.selling_controller import SellingController
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.doctype.delivery_note.delivery_note import update_billed_amount_based_on_so
from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_gl_entries_on_asset_disposal
from erpnext.stock.doctype.batch.batch import set_batch_nos
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_delivery_note_serial_no
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.doctype.loyalty_program.loyalty_program import \
	get_loyalty_program_details_with_points, get_loyalty_details, validate_loyalty_points
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display

from erpnext.healthcare.utils import manage_invoice_submit_cancel

from six import iteritems

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class SalesInvoice(SellingController):
	def __init__(self, *args, **kwargs):
		super(SalesInvoice, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Sales Invoice Item',
			'target_field': 'billed_amt',
			'target_ref_field': 'amount',
			'target_dt': 'Sales Order Item',
			'join_field': 'so_detail',
			'target_parent_dt': 'Sales Order',
			'target_parent_field': 'per_billed',
			'source_field': 'amount',
			'join_field': 'so_detail',
			'percent_join_field': 'sales_order',
			'status_field': 'billing_status',
			'keyword': 'Billed',
			'overflow_type': 'billing'
		}]

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.outstanding_amount < 0:
			self.indicator_title = _("Credit Note Issued")
			self.indicator_color = "darkgrey"
		elif self.outstanding_amount > 0 and getdate(self.due_date) >= getdate(nowdate()):
			self.indicator_color = "orange"
			self.indicator_title = _("Unpaid")
		elif self.outstanding_amount > 0 and getdate(self.due_date) < getdate(nowdate()):
			self.indicator_color = "red"
			self.indicator_title = _("Overdue")
		elif cint(self.is_return) == 1:
			self.indicator_title = _("Return")
			self.indicator_color = "darkgrey"
		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def validate(self):
		super(SalesInvoice, self).validate()
		self.validate_auto_set_posting_time()

		if not self.is_pos:
			self.so_dn_required()

		self.validate_proj_cust()
		self.validate_pos_return()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.check_sales_order_on_hold_or_close("sales_order")
		self.validate_debit_to_acc()
		self.clear_unallocated_advances("Sales Invoice Advance", "advances")
		self.add_remarks()
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_fixed_asset()
		self.set_income_account_for_fixed_assets()
		self.validate_item_cost_centers()
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_invoice_reference)

		if cint(self.is_pos):
			self.validate_pos()

		if cint(self.update_stock):
			self.validate_dropship_item()
			self.validate_item_code()
			self.validate_warehouse()
			self.update_current_stock()
			self.validate_delivery_note()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		if not self.is_opening:
			self.is_opening = 'No'

		if self._action != 'submit' and self.update_stock and not self.is_return:
			set_batch_nos(self, 'warehouse', True)

		if self.redeem_loyalty_points:
			lp = frappe.get_doc('Loyalty Program', self.loyalty_program)
			self.loyalty_redemption_account = lp.expense_account if not self.loyalty_redemption_account else self.loyalty_redemption_account
			self.loyalty_redemption_cost_center = lp.cost_center if not self.loyalty_redemption_cost_center else self.loyalty_redemption_cost_center

		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_sheets_are_submitted()
		self.validate_multiple_billing("Delivery Note", "dn_detail", "amount", "items")
		if not self.is_return:
			self.validate_serial_numbers()
		self.update_packing_list()
		self.set_billing_hours_and_amount()
		self.update_timesheet_billing_for_project()
		self.set_status()
		if self.is_pos and not self.is_return:
			self.verify_payment_amount_is_positive()

		#validate amount in mode of payments for returned invoices for pos must be negative
		if self.is_pos and self.is_return:
			self.verify_payment_amount_is_negative()

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points and not self.is_consolidated:
			validate_loyalty_points(self, self.loyalty_points)

	def validate_fixed_asset(self):
		for d in self.get("items"):
			if d.is_fixed_asset and d.meta.get_field("asset") and d.asset:
				asset = frappe.get_doc("Asset", d.asset)
				if self.doctype == "Sales Invoice" and self.docstatus == 1:
					if self.update_stock:
						frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))

					elif asset.status in ("Scrapped", "Cancelled", "Sold"):
						frappe.throw(_("Row #{0}: Asset {1} cannot be submitted, it is already {2}").format(d.idx, d.asset, asset.status))

	def validate_item_cost_centers(self):
		for item in self.items:
			cost_center_company = frappe.get_cached_value("Cost Center", item.cost_center, "company")
			if cost_center_company != self.company:
				frappe.throw(_("Row #{0}: Cost Center {1} does not belong to company {2}").format(frappe.bold(item.idx), frappe.bold(item.cost_center), frappe.bold(self.company)))

	def before_save(self):
		set_account_for_mode_of_payment(self)

	def on_submit(self):
		self.validate_pos_paid_amount()

		if not self.auto_repeat:
			frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
				self.company, self.base_grand_total, self)

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_in_dn()
		self.clear_unallocated_mode_of_payments()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		# this sequence because outstanding may get -ve
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.check_credit_limit()

		self.update_serial_no()

		if not cint(self.is_pos) == 1 and not self.is_return:
			self.update_against_document_in_jv()

		self.update_time_sheet(self.name)

		if frappe.db.get_single_value('Selling Settings', 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if not self.is_return and not self.is_consolidated and self.loyalty_program:
			self.make_loyalty_point_entry()
		elif self.is_return and self.return_against and not self.is_consolidated and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()
		if self.redeem_loyalty_points and not self.is_consolidated and self.loyalty_points:
			self.apply_loyalty_points()

		# Healthcare Service Invoice.
		domain_settings = frappe.get_doc('Domain Settings')
		active_domains = [d.domain for d in domain_settings.active_domains]

		if "Healthcare" in active_domains:
			manage_invoice_submit_cancel(self, "on_submit")

	def validate_pos_return(self):

		if self.is_pos and self.is_return:
			total_amount_in_payments = 0
			for payment in self.payments:
				total_amount_in_payments += payment.amount
			invoice_total = self.rounded_total or self.grand_total
			if total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}").format(-invoice_total))

	def validate_pos_paid_amount(self):
		if len(self.payments) == 0 and self.is_pos:
			frappe.throw(_("At least one mode of payment is required for POS invoice."))

	def check_if_consolidated_invoice(self):
		# since POS Invoice extends Sales Invoice, we explicitly check if doctype is Sales Invoice
		if self.doctype == "Sales Invoice" and self.is_consolidated:
			invoice_or_credit_note = "consolidated_credit_note" if self.is_return else "consolidated_invoice"
			pos_closing_entry = frappe.get_all(
				"POS Invoice Merge Log",
				filters={ invoice_or_credit_note: self.name },
				pluck="pos_closing_entry"
			)
			if pos_closing_entry:
				msg = _("To cancel a {} you need to cancel the POS Closing Entry {}. ").format(
					frappe.bold("Consolidated Sales Invoice"),
					get_link_to_form("POS Closing Entry", pos_closing_entry[0])
				)
				frappe.throw(msg, title=_("Not Allowed"))

	def before_cancel(self):
		self.check_if_consolidated_invoice()

		super(SalesInvoice, self).before_cancel()
		self.update_time_sheet(None)

	def on_cancel(self):
		super(SalesInvoice, self).on_cancel()

		self.check_sales_order_on_hold_or_close("sales_order")

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_in_dn()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.update_serial_no(in_cancel=True)

		self.validate_c_form_on_cancel()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		self.make_gl_entries_on_cancel()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		frappe.db.set(self, 'status', 'Cancelled')

		if frappe.db.get_single_value('Selling Settings', 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		if not self.is_return and not self.is_consolidated and self.loyalty_program:
			self.delete_loyalty_point_entry()
		elif self.is_return and self.return_against and not self.is_consolidated and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		# Healthcare Service Invoice.
		domain_settings = frappe.get_doc('Domain Settings')
		active_domains = [d.domain for d in domain_settings.active_domains]

		if "Healthcare" in active_domains:
			manage_invoice_submit_cancel(self, "on_cancel")

		self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry', 'Repost Item Valuation')

	def update_status_updater_args(self):
		if cint(self.update_stock):
			self.status_updater.append({
				'source_dt':'Sales Invoice Item',
				'target_dt':'Sales Order Item',
				'target_parent_dt':'Sales Order',
				'target_parent_field':'per_delivered',
				'target_field':'delivered_qty',
				'target_ref_field':'qty',
				'source_field':'qty',
				'join_field':'so_detail',
				'percent_join_field':'sales_order',
				'status_field':'delivery_status',
				'keyword':'Delivered',
				'second_source_dt': 'Delivery Note Item',
				'second_source_field': 'qty',
				'second_join_field': 'so_detail',
				'overflow_type': 'delivery',
				'extra_cond': """ and exists(select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and update_stock = 1)"""
			})
			if cint(self.is_return):
				self.status_updater.append({
					'source_dt': 'Sales Invoice Item',
					'target_dt': 'Sales Order Item',
					'join_field': 'so_detail',
					'target_field': 'returned_qty',
					'target_parent_dt': 'Sales Order',
					'source_field': '-1 * qty',
					'second_source_dt': 'Delivery Note Item',
					'second_source_field': '-1 * qty',
					'second_join_field': 'so_detail',
					'extra_cond': """ and exists (select name from `tabSales Invoice` where name=`tabSales Invoice Item`.parent and update_stock=1 and is_return=1)"""
				})

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = frappe.db.get_value("Customer Credit Limit",
			filters={'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
			fieldname=["bypass_credit_limit_check"])

		if bypass_credit_limit_check_at_sales_order:
			validate_against_credit_limit = True

		for d in self.get("items"):
			if not (d.sales_order or d.delivery_note):
				validate_against_credit_limit = True
				break
		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company, bypass_credit_limit_check_at_sales_order)

	def set_missing_values(self, for_validate=False):
		pos = self.set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			self.party_account_currency = frappe.db.get_value("Account", self.debit_to, "account_currency", cache=True)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(self.posting_date, "Customer", self.customer, self.company)

		super(SalesInvoice, self).set_missing_values(for_validate)

		print_format = pos.get("print_format") if pos else None
		if not print_format and not cint(frappe.db.get_value('Print Format', 'POS Invoice', 'disabled')):
			print_format = 'POS Invoice'

		if pos:
			return {
				"print_format": print_format,
				"allow_edit_rate": pos.get("allow_user_to_edit_rate"),
				"allow_edit_discount": pos.get("allow_user_to_edit_discount"),
				"campaign": pos.get("campaign"),
				"allow_print_before_pay": pos.get("allow_print_before_pay")
			}

	def update_time_sheet(self, sales_invoice):
		for d in self.timesheets:
			if d.time_sheet:
				timesheet = frappe.get_doc("Timesheet", d.time_sheet)
				self.update_time_sheet_detail(timesheet, d, sales_invoice)
				timesheet.calculate_total_amounts()
				timesheet.calculate_percentage_billed()
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.save()

	def update_time_sheet_detail(self, timesheet, args, sales_invoice):
		for data in timesheet.time_logs:
			if (self.project and args.timesheet_detail == data.name) or \
				(not self.project and not data.sales_invoice) or \
				(not sales_invoice and data.sales_invoice == self.name):
				data.sales_invoice = sales_invoice

	def on_update(self):
		self.set_paid_amount()

	def set_paid_amount(self):
		paid_amount = 0.0
		base_paid_amount = 0.0
		for data in self.payments:
			data.base_amount = flt(data.amount*self.conversion_rate, self.precision("base_paid_amount"))
			paid_amount += data.amount
			base_paid_amount += data.base_amount

		self.paid_amount = paid_amount
		self.base_paid_amount = base_paid_amount

	def validate_time_sheets_are_submitted(self):
		for data in self.timesheets:
			if data.time_sheet:
				status = frappe.db.get_value("Timesheet", data.time_sheet, "status")
				if status not in ['Submitted', 'Payslip']:
					frappe.throw(_("Timesheet {0} is already completed or cancelled").format(data.time_sheet))

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from POS Profiles"""
		if cint(self.is_pos) != 1:
			return

		from erpnext.stock.get_item_details import get_pos_profile_item_details, get_pos_profile
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			if not pos_profile:
				frappe.throw(_("No POS Profile found. Please create a New POS Profile first"))
			self.pos_profile = pos_profile.get('name')

		pos = {}
		if self.pos_profile:
			pos = frappe.get_doc('POS Profile', self.pos_profile)

		if not self.get('payments') and not for_validate:
			update_multi_mode_option(self, pos)

		if not self.account_for_change_amount:
			self.account_for_change_amount = frappe.get_cached_value('Company',  self.company,  'default_cash_account')

		if pos:
			if not for_validate:
				self.tax_category = pos.get("tax_category")

			if not for_validate and not self.customer:
				self.customer = pos.customer

			if not for_validate:
				self.ignore_pricing_rule = pos.ignore_pricing_rule

			if pos.get('account_for_change_amount'):
				self.account_for_change_amount = pos.get('account_for_change_amount')

			for fieldname in ('currency', 'letter_head', 'tc_name',
				'company', 'select_print_heading', 'write_off_account', 'taxes_and_charges',
				'write_off_cost_center', 'apply_discount_on', 'cost_center'):
					if (not for_validate) or (for_validate and not self.get(fieldname)):
						self.set(fieldname, pos.get(fieldname))

			if pos.get("company_address"):
				self.company_address = pos.get("company_address")

			if self.customer:
				customer_price_list, customer_group = frappe.get_value("Customer", self.customer, ['default_price_list', 'customer_group'])
				customer_group_price_list = frappe.get_value("Customer Group", customer_group, 'default_price_list')
				selling_price_list = customer_price_list or customer_group_price_list or pos.get('selling_price_list')
			else:
				selling_price_list = pos.get('selling_price_list')

			if selling_price_list:
				self.set('selling_price_list', selling_price_list)

			if not for_validate:
				self.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("items"):
				if item.get('item_code'):
					profile_details = get_pos_profile_item_details(pos, frappe._dict(item.as_dict()), pos)
					for fname, val in iteritems(profile_details):
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("taxes")):
				self.set_taxes()

		return pos

	def get_company_abbr(self):
		return frappe.db.sql("select abbr from tabCompany where name=%s", self.company)[0][0]

	def validate_debit_to_acc(self):
		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			if not self.debit_to:
				self.raise_missing_debit_credit_account_error("Customer", self.customer)

		account = frappe.get_cached_value("Account", self.debit_to,
			["account_type", "report_type", "account_currency"], as_dict=True)

		if not account:
			frappe.throw(_("Debit To is required"), title=_("Account Missing"))

		if account.report_type != "Balance Sheet":
			msg = _("Please ensure {} account is a Balance Sheet account. ").format(frappe.bold("Debit To"))
			msg += _("You can change the parent account to a Balance Sheet account or select a different account.")
			frappe.throw(msg, title=_("Invalid Account"))

		if self.customer and account.account_type != "Receivable":
			msg = _("Please ensure {} account is a Receivable account. ").format(frappe.bold("Debit To"))
			msg += _("Change the account type to Receivable or select a different account.")
			frappe.throw(msg, title=_("Invalid Account"))

		self.party_account_currency = account.account_currency

	def clear_unallocated_mode_of_payments(self):
		self.set("payments", self.get("payments", {"amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tabSales Invoice Payment` where parent = %s
			and amount = 0""", self.name)

	def validate_with_previous_doc(self):
		super(SalesInvoice, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Order Item": {
				"ref_dn_field": "so_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Delivery Note": {
				"ref_dn_field": "delivery_note",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Delivery Note Item": {
				"ref_dn_field": "dn_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
		})

		if cint(frappe.db.get_single_value('Selling Settings', 'maintain_same_sales_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([
				["Sales Order", "sales_order", "so_detail"],
				["Delivery Note", "delivery_note", "dn_detail"]
			])

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get('items'):
			if d.income_account and d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.against_income_account = ','.join(against_acc)

	def add_remarks(self):
		if not self.remarks:
			if self.po_no and self.po_date:
				self.remarks = _("Against Customer Order {0} dated {1}").format(self.po_no,
					formatdate(self.po_date))
			else:
				self.remarks = _("No Remarks")

	def validate_auto_set_posting_time(self):
		# Don't auto set the posting date and time if invoice is amended
		if self.is_new() and self.amended_from:
			self.set_posting_time = 1

		self.validate_posting_time()

	def so_dn_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		if self.is_return:
			return

		prev_doc_field_map = {'Sales Order': ['so_required', 'is_pos'],'Delivery Note': ['dn_required', 'update_stock']}
		for key, value in iteritems(prev_doc_field_map):
			if frappe.db.get_single_value('Selling Settings', value[0]) == 'Yes':

				if frappe.get_value('Customer', self.customer, value[0]):
					continue

				for d in self.get('items'):
					if (d.item_code and not d.get(key.lower().replace(' ', '_')) and not self.get(value[1])):
						msgprint(_("{0} is mandatory for Item {1}").format(key, d.item_code), raise_exception=1)


	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or customer is null or customer = '')""",
				(self.project, self.customer))
			if not res:
				throw(_("Customer {0} does not belong to project {1}").format(self.customer,self.project))

	def validate_pos(self):
		if self.is_return:
			invoice_total = self.rounded_total or self.grand_total
			if flt(self.paid_amount) + flt(self.write_off_amount) - flt(invoice_total) > \
				1.0/(10.0**(self.precision("grand_total") + 1.0)):
					frappe.throw(_("Paid amount + Write Off Amount can not be greater than Grand Total"))

	def validate_item_code(self):
		for d in self.get('items'):
			if not d.item_code and self.is_opening == "No":
				msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def validate_warehouse(self):
		super(SalesInvoice, self).validate_warehouse()

		for d in self.get_item_list():
			if not d.warehouse and d.item_code and frappe.get_cached_value("Item", d.item_code, "is_stock_item"):
				frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

	def validate_delivery_note(self):
		for d in self.get("items"):
			if d.delivery_note:
				msgprint(_("Stock cannot be updated against Delivery Note {0}").format(d.delivery_note), raise_exception=1)

	def validate_write_off_account(self):
		if flt(self.write_off_amount) and not self.write_off_account:
			self.write_off_account = frappe.get_cached_value('Company',  self.company,  'write_off_account')

		if flt(self.write_off_amount) and not self.write_off_account:
			msgprint(_("Please enter Write Off Account"), raise_exception=1)

	def validate_account_for_change_amount(self):
		if flt(self.change_amount) and not self.account_for_change_amount:
			msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.amended_from and self.c_form_applicable == 'No' and self.c_form_no:
			frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.amended_from,	self.c_form_no))

			frappe.db.set(self, 'c_form_no', '')

	def validate_c_form_on_cancel(self):
		""" Display message if C-Form no exists on cancellation of Sales Invoice"""
		if self.c_form_applicable == 'Yes' and self.c_form_no:
			msgprint(_("Please remove this Invoice {0} from C-Form {1}")
				.format(self.name, self.c_form_no), raise_exception = 1)

	def validate_dropship_item(self):
		for item in self.items:
			if item.sales_order:
				if frappe.db.get_value("Sales Order Item", item.so_detail, "delivered_by_supplier"):
					frappe.throw(_("Could not update stock, invoice contains drop shipping item."))

	def update_current_stock(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
				d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

		for d in self.get('packed_items'):
			bin = frappe.db.sql("select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
			d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0

	def update_packing_list(self):
		if cint(self.update_stock) == 1:
			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
			make_packing_list(self)
		else:
			self.set('packed_items', [])

	def set_billing_hours_and_amount(self):
		if not self.project:
			for timesheet in self.timesheets:
				ts_doc = frappe.get_doc('Timesheet', timesheet.time_sheet)
				if not timesheet.billing_hours and ts_doc.total_billable_hours:
					timesheet.billing_hours = ts_doc.total_billable_hours

				if not timesheet.billing_amount and ts_doc.total_billable_amount:
					timesheet.billing_amount = ts_doc.total_billable_amount

	def update_timesheet_billing_for_project(self):
		if not self.timesheets and self.project:
			self.add_timesheet_data()
		else:
			self.calculate_billing_amount_for_timesheet()

	def add_timesheet_data(self):
		self.set('timesheets', [])
		if self.project:
			for data in get_projectwise_timesheet_data(self.project):
				self.append('timesheets', {
						'time_sheet': data.parent,
						'billing_hours': data.billing_hours,
						'billing_amount': data.billing_amt,
						'timesheet_detail': data.name
					})

			self.calculate_billing_amount_for_timesheet()

	def calculate_billing_amount_for_timesheet(self):
		total_billing_amount = 0.0
		for data in self.timesheets:
			if data.billing_amount:
				total_billing_amount += data.billing_amount

		self.total_billing_amount = total_billing_amount

	def get_warehouse(self):
		user_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
			where ifnull(user,'') = %s and company = %s""", (frappe.session['user'], self.company))
		warehouse = user_pos_profile[0][1] if user_pos_profile else None

		if not warehouse:
			global_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
				where (user is null or user = '') and company = %s""", self.company)

			if global_pos_profile:
				warehouse = global_pos_profile[0][1]
			elif not user_pos_profile:
				msgprint(_("POS Profile required to make POS Entry"), raise_exception=True)

		return warehouse

	def set_income_account_for_fixed_assets(self):
		disposal_account = depreciation_cost_center = None
		for d in self.get("items"):
			if d.is_fixed_asset:
				if not disposal_account:
					disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(self.company)

				d.income_account = disposal_account
				if not d.cost_center:
					d.cost_center = depreciation_cost_center

	def check_prev_docstatus(self):
		for d in self.get('items'):
			if d.sales_order and frappe.db.get_value("Sales Order", d.sales_order, "docstatus") != 1:
				frappe.throw(_("Sales Order {0} is not submitted").format(d.sales_order))

			if d.delivery_note and frappe.db.get_value("Delivery Note", d.delivery_note, "docstatus") != 1:
				throw(_("Delivery Note {0} is not submitted").format(d.delivery_note))

	def make_gl_entries(self, gl_entries=None, from_repost=False):
		from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
		if not gl_entries:
			gl_entries = self.get_gl_entries()

		if gl_entries:
			# if POS and amount is written off, updating outstanding amt after posting all gl entries
			update_outstanding = "No" if (cint(self.is_pos) or self.write_off_account or
				cint(self.redeem_loyalty_points)) else "Yes"

			if self.docstatus == 1:
				make_gl_entries(gl_entries, update_outstanding=update_outstanding, merge_entries=False, from_repost=from_repost)
			elif self.docstatus == 2:
				make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

			if update_outstanding == "No":
				from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
				update_outstanding_amt(self.debit_to, "Customer", self.customer,
					self.doctype, self.return_against if cint(self.is_return) and self.return_against else self.name)

		elif self.docstatus == 2 and cint(self.update_stock) \
			and cint(auto_accounting_for_stock):
				make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import merge_similar_entries

		gl_entries = []

		self.make_customer_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)
		self.make_internal_transfer_gl_entries(gl_entries)

		self.make_item_gl_entries(gl_entries)

		# merge gl entries before adding pos entries
		gl_entries = merge_similar_entries(gl_entries)

		self.make_loyalty_point_redemption_gle(gl_entries)
		self.make_pos_gl_entries(gl_entries)
		self.make_gle_for_change_amount(gl_entries)

		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)

		return gl_entries

	def make_customer_gl_entry(self, gl_entries):
		# Checked both rounding_adjustment and rounded_total
		# because rounded_total had value even before introcution of posting GLE based on rounded total
		grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
		if grand_total and not self.is_internal_transfer():
			# Didnot use base_grand_total to book rounding loss gle
			grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
				self.precision("grand_total"))

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": self.due_date,
					"against": self.against_income_account,
					"debit": grand_total_in_company_currency,
					"debit_in_account_currency": grand_total_in_company_currency \
						if self.party_account_currency==self.company_currency else grand_total,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)

	def make_tax_gl_entries(self, gl_entries):
		for tax in self.get("taxes"):
			if flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.customer,
						"credit": flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("tax_amount_after_discount_amount")),
						"credit_in_account_currency": (flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("base_tax_amount_after_discount_amount")) if account_currency==self.company_currency else
							flt(tax.tax_amount_after_discount_amount, tax.precision("tax_amount_after_discount_amount"))),
						"cost_center": tax.cost_center
					}, account_currency, item=tax)
				)

	def make_internal_transfer_gl_entries(self, gl_entries):
		if self.is_internal_transfer() and flt(self.base_total_taxes_and_charges):
			account_currency = get_account_currency(self.unrealized_profit_loss_account)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.unrealized_profit_loss_account,
					"against": self.customer,
					"debit": flt(self.total_taxes_and_charges),
					"debit_in_account_currency": flt(self.base_total_taxes_and_charges),
					"cost_center": self.cost_center
				}, account_currency, item=self))

	def make_item_gl_entries(self, gl_entries):
		# income account gl entries
		for item in self.get("items"):
			if flt(item.base_net_amount, item.precision("base_net_amount")):
				if item.is_fixed_asset:
					asset = frappe.get_doc("Asset", item.asset)

					if (len(asset.finance_books) > 1 and not item.finance_book
						and asset.finance_books[0].finance_book):
						frappe.throw(_("Select finance book for the item {0} at row {1}")
							.format(item.item_code, item.idx))

					fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset,
						item.base_net_amount, item.finance_book)

					for gle in fixed_asset_gl_entries:
						gle["against"] = self.customer
						gl_entries.append(self.get_gl_dict(gle, item=item))

					asset.db_set("disposal_date", self.posting_date)
					asset.set_status("Sold" if self.docstatus==1 else None)
				else:
					# Do not book income for transfer within same company
					if not self.is_internal_transfer():
						income_account = (item.income_account
							if (not item.enable_deferred_revenue or self.is_return) else item.deferred_revenue_account)

						account_currency = get_account_currency(income_account)
						gl_entries.append(
							self.get_gl_dict({
								"account": income_account,
								"against": self.customer,
								"credit": flt(item.base_net_amount, item.precision("base_net_amount")),
								"credit_in_account_currency": (flt(item.base_net_amount, item.precision("base_net_amount"))
									if account_currency==self.company_currency
									else flt(item.net_amount, item.precision("net_amount"))),
								"cost_center": item.cost_center,
								"project": item.project or self.project
							}, account_currency, item=item)
						)

		# expense account gl entries
		if cint(self.update_stock) and \
			erpnext.is_perpetual_inventory_enabled(self.company):
			gl_entries += super(SalesInvoice, self).get_gl_entries()

	def make_loyalty_point_redemption_gle(self, gl_entries):
		if cint(self.redeem_loyalty_points):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"against": "Expense account - " + cstr(self.loyalty_redemption_account) + " for the Loyalty Program",
					"credit": self.loyalty_amount,
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center
				}, item=self)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.loyalty_redemption_account,
					"cost_center": self.cost_center or self.loyalty_redemption_cost_center,
					"against": self.customer,
					"debit": self.loyalty_amount,
					"remark": "Loyalty Points redeemed by the customer"
				}, item=self)
			)

	def make_pos_gl_entries(self, gl_entries):
		if cint(self.is_pos):
			for payment_mode in self.payments:
				if payment_mode.amount:
					# POS, make payment entries
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_to,
							"party_type": "Customer",
							"party": self.customer,
							"against": payment_mode.account,
							"credit": payment_mode.base_amount,
							"credit_in_account_currency": payment_mode.base_amount \
								if self.party_account_currency==self.company_currency \
								else payment_mode.amount,
							"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
							"against_voucher_type": self.doctype,
							"cost_center": self.cost_center
						}, self.party_account_currency, item=self)
					)

					payment_mode_account_currency = get_account_currency(payment_mode.account)
					gl_entries.append(
						self.get_gl_dict({
							"account": payment_mode.account,
							"against": self.customer,
							"debit": payment_mode.base_amount,
							"debit_in_account_currency": payment_mode.base_amount \
								if payment_mode_account_currency==self.company_currency \
								else payment_mode.amount,
							"cost_center": self.cost_center
						}, payment_mode_account_currency, item=self)
					)

	def make_gle_for_change_amount(self, gl_entries):
		if cint(self.is_pos) and self.change_amount:
			if self.account_for_change_amount:
				gl_entries.append(
					self.get_gl_dict({
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"against": self.account_for_change_amount,
						"debit": flt(self.base_change_amount),
						"debit_in_account_currency": flt(self.base_change_amount) \
							if self.party_account_currency==self.company_currency else flt(self.change_amount),
						"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
						"against_voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"project": self.project
					}, self.party_account_currency, item=self)
				)

				gl_entries.append(
					self.get_gl_dict({
						"account": self.account_for_change_amount,
						"against": self.customer,
						"credit": self.base_change_amount,
						"cost_center": self.cost_center
					}, item=self)
				)
			else:
				frappe.throw(_("Select change amount account"), title="Mandatory Field")

	def make_write_off_gl_entry(self, gl_entries):
		# write off entries, applicable if only pos
		if self.write_off_account and flt(self.write_off_amount, self.precision("write_off_amount")):
			write_off_account_currency = get_account_currency(self.write_off_account)
			default_cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"against": self.write_off_account,
					"credit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"credit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if self.party_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
					"project": self.project
				}, self.party_account_currency, item=self)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": self.customer,
					"debit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"debit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if write_off_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"cost_center": self.cost_center or self.write_off_cost_center or default_cost_center
				}, write_off_account_currency, item=self)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		if flt(self.rounding_adjustment, self.precision("rounding_adjustment")) and self.base_rounding_adjustment:
			round_off_account, round_off_cost_center = \
				get_round_off_account_and_cost_center(self.company)

			gl_entries.append(
				self.get_gl_dict({
					"account": round_off_account,
					"against": self.customer,
					"credit_in_account_currency": flt(self.rounding_adjustment,
						self.precision("rounding_adjustment")),
					"credit": flt(self.base_rounding_adjustment,
						self.precision("base_rounding_adjustment")),
					"cost_center": self.cost_center or round_off_cost_center,
				}, item=self))

	def update_billing_status_in_dn(self, update_modified=True):
		updated_delivery_notes = []
		for d in self.get("items"):
			if d.dn_detail:
				billed_amt = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
					where dn_detail=%s and docstatus=1""", d.dn_detail)
				billed_amt = billed_amt and billed_amt[0][0] or 0
				frappe.db.set_value("Delivery Note Item", d.dn_detail, "billed_amt", billed_amt, update_modified=update_modified)
				updated_delivery_notes.append(d.delivery_note)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			frappe.get_doc("Delivery Note", dn).update_billing_percentage(update_modified=update_modified)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		for fieldname in ("c_form_applicable", "c_form_no", "write_off_amount"):
			self.set(fieldname, reference_doc.get(fieldname))

		self.due_date = None

	def update_serial_no(self, in_cancel=False):
		""" update Sales Invoice refrence in Serial No """
		invoice = None if (in_cancel or self.is_return) else self.name
		if in_cancel and self.is_return:
			invoice = self.return_against

		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				if serial_no and frappe.db.get_value('Serial No', serial_no, 'item_code') == item.item_code:
					frappe.db.set_value('Serial No', serial_no, 'sales_invoice', invoice)

	def validate_serial_numbers(self):
		"""
			validate serial number agains Delivery Note and Sales Invoice
		"""
		self.set_serial_no_against_delivery_note()
		self.validate_serial_against_delivery_note()
		self.validate_serial_against_sales_invoice()

	def set_serial_no_against_delivery_note(self):
		for item in self.items:
			if item.serial_no and item.delivery_note and \
				item.qty != len(get_serial_nos(item.serial_no)):
				item.serial_no = get_delivery_note_serial_no(item.item_code, item.qty, item.delivery_note)

	def validate_serial_against_delivery_note(self):
		"""
			validate if the serial numbers in Sales Invoice Items are same as in
			Delivery Note Item
		"""

		for item in self.items:
			if not item.delivery_note or not item.dn_detail:
				continue

			serial_nos = frappe.db.get_value("Delivery Note Item", item.dn_detail, "serial_no") or ""
			dn_serial_nos = set(get_serial_nos(serial_nos))

			serial_nos = item.serial_no or ""
			si_serial_nos = set(get_serial_nos(serial_nos))

			if si_serial_nos - dn_serial_nos:
				frappe.throw(_("Serial Numbers in row {0} does not match with Delivery Note").format(item.idx))

			if item.serial_no and cint(item.qty) != len(si_serial_nos):
				frappe.throw(_("Row {0}: {1} Serial numbers required for Item {2}. You have provided {3}.").format(
					item.idx, item.qty, item.item_code, len(si_serial_nos)))

	def validate_serial_against_sales_invoice(self):
		""" check if serial number is already used in other sales invoice """
		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				serial_no_details = frappe.db.get_value("Serial No", serial_no,
					["sales_invoice", "item_code"], as_dict=1)

				if not serial_no_details:
					continue

				if serial_no_details.sales_invoice and serial_no_details.item_code == item.item_code \
					and self.name != serial_no_details.sales_invoice:
					sales_invoice_company = frappe.db.get_value("Sales Invoice", serial_no_details.sales_invoice, "company")
					if sales_invoice_company == self.company:
						frappe.throw(_("Serial Number: {0} is already referenced in Sales Invoice: {1}")
							.format(serial_no, serial_no_details.sales_invoice))

	def update_project(self):
		if self.project:
			project = frappe.get_doc("Project", self.project)
			project.update_billed_amount()
			project.db_update()


	def verify_payment_amount_is_positive(self):
		for entry in self.payments:
			if entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))

	def verify_payment_amount_is_negative(self):
		for entry in self.payments:
			if entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))

	# collection of the loyalty points, create the ledger entry for that.
	def make_loyalty_point_entry(self):
		returned_amount = self.get_returned_amount()
		current_amount = flt(self.grand_total) - cint(self.loyalty_amount)
		eligible_amount = current_amount - returned_amount
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
			current_transaction_amount=current_amount, loyalty_program=self.loyalty_program,
			expiry_date=self.posting_date, include_expired_entry=True)
		if lp_details and getdate(lp_details.from_date) <= getdate(self.posting_date) and \
			(not lp_details.to_date or getdate(lp_details.to_date) >= getdate(self.posting_date)):

			collection_factor = lp_details.collection_factor if lp_details.collection_factor else 1.0
			points_earned = cint(eligible_amount/collection_factor)

			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": lp_details.loyalty_program,
				"loyalty_program_tier": lp_details.tier_name,
				"customer": self.customer,
				"invoice_type": self.doctype,
				"invoice": self.name,
				"loyalty_points": points_earned,
				"purchase_amount": eligible_amount,
				"expiry_date": add_days(self.posting_date, lp_details.expiry_duration),
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			self.set_loyalty_program_tier()

	# valdite the redemption and then delete the loyalty points earned on cancel of the invoice
	def delete_loyalty_point_entry(self):
		lp_entry = frappe.db.sql("select name from `tabLoyalty Point Entry` where invoice=%s",
			(self.name), as_dict=1)

		if not lp_entry: return
		against_lp_entry = frappe.db.sql('''select name, invoice from `tabLoyalty Point Entry`
			where redeem_against=%s''', (lp_entry[0].name), as_dict=1)
		if against_lp_entry:
			invoice_list = ", ".join([d.invoice for d in against_lp_entry])
			frappe.throw(
				_('''{} can't be cancelled since the Loyalty Points earned has been redeemed. First cancel the {} No {}''')
				.format(self.doctype, self.doctype, invoice_list)
			)
		else:
			frappe.db.sql('''delete from `tabLoyalty Point Entry` where invoice=%s''', (self.name))
			# Set loyalty program
			self.set_loyalty_program_tier()

	def set_loyalty_program_tier(self):
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
				loyalty_program=self.loyalty_program, include_expired_entry=True)
		frappe.db.set_value("Customer", self.customer, "loyalty_program_tier", lp_details.tier_name)

	def get_returned_amount(self):
		returned_amount = frappe.db.sql("""
			select sum(grand_total)
			from `tabSales Invoice`
			where docstatus=1 and is_return=1 and ifnull(return_against, '')=%s
		""", self.name)
		return abs(flt(returned_amount[0][0])) if returned_amount else 0

	# redeem the loyalty points.
	def apply_loyalty_points(self):
		from erpnext.accounts.doctype.loyalty_point_entry.loyalty_point_entry \
			import get_loyalty_point_entries, get_redemption_details
		loyalty_point_entries = get_loyalty_point_entries(self.customer, self.loyalty_program, self.company, self.posting_date)
		redemption_details = get_redemption_details(self.customer, self.loyalty_program, self.company)

		points_to_redeem = self.loyalty_points
		for lp_entry in loyalty_point_entries:
			if lp_entry.invoice_type != self.doctype or lp_entry.invoice == self.name:
				# redeemption should be done against same doctype
				# also it shouldn't be against itself
				continue
			available_points = lp_entry.loyalty_points - flt(redemption_details.get(lp_entry.name))
			if available_points > points_to_redeem:
				redeemed_points = points_to_redeem
			else:
				redeemed_points = available_points
			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": self.loyalty_program,
				"loyalty_program_tier": lp_entry.loyalty_program_tier,
				"customer": self.customer,
				"invoice_type": self.doctype,
				"invoice": self.name,
				"redeem_against": lp_entry.name,
				"loyalty_points": -1*redeemed_points,
				"purchase_amount": self.grand_total,
				"expiry_date": lp_entry.expiry_date,
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			points_to_redeem -= redeemed_points
			if points_to_redeem < 1: # since points_to_redeem is integer
				break

	# Healthcare
	def set_healthcare_services(self, checked_values):
		self.set("items", [])
		from erpnext.stock.get_item_details import get_item_details
		for checked_item in checked_values:
			item_line = self.append("items", {})
			price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]
			args = {
				'doctype': "Sales Invoice",
				'item_code': checked_item['item'],
				'company': self.company,
				'customer': frappe.db.get_value("Patient", self.patient, "customer"),
				'selling_price_list': price_list,
				'price_list_currency': price_list_currency,
				'plc_conversion_rate': 1.0,
				'conversion_rate': 1.0
			}
			item_details = get_item_details(args)
			item_line.item_code = checked_item['item']
			item_line.qty = 1
			if checked_item['qty']:
				item_line.qty = checked_item['qty']
			if checked_item['rate']:
				item_line.rate = checked_item['rate']
			else:
				item_line.rate = item_details.price_list_rate
			item_line.amount = float(item_line.rate) * float(item_line.qty)
			if checked_item['income_account']:
				item_line.income_account = checked_item['income_account']
			if checked_item['dt']:
				item_line.reference_dt = checked_item['dt']
			if checked_item['dn']:
				item_line.reference_dn = checked_item['dn']
			if checked_item['description']:
				item_line.description = checked_item['description']

		self.set_missing_values(for_validate = True)

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		precision = self.precision("outstanding_amount")
		outstanding_amount = flt(self.outstanding_amount, precision)
		due_date = getdate(self.due_date)
		nowdate = getdate()

		discounting_status = None
		if self.is_discounted:
			discountng_status = get_discounting_status(self.name)

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if self.is_internal_transfer():
					self.status = 'Internal Transfer'
				elif outstanding_amount > 0 and due_date < nowdate and self.is_discounted and discountng_status=='Disbursed':
					self.status = "Overdue and Discounted"
				elif outstanding_amount > 0 and due_date < nowdate:
					self.status = "Overdue"
				elif outstanding_amount > 0 and due_date >= nowdate and self.is_discounted and discountng_status=='Disbursed':
					self.status = "Unpaid and Discounted"
				elif outstanding_amount > 0 and due_date >= nowdate:
					self.status = "Unpaid"
				#Check if outstanding amount is 0 due to credit note issued against invoice
				elif outstanding_amount <= 0 and self.is_return == 0 and frappe.db.get_value('Sales Invoice', {'is_return': 1, 'return_against': self.name, 'docstatus': 1}):
					self.status = "Credit Note Issued"
				elif self.is_return == 1:
					self.status = "Return"
				elif outstanding_amount<=0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set('status', self.status, update_modified = update_modified)

def get_discounting_status(sales_invoice):
	status = None

	invoice_discounting_list = frappe.db.sql("""
		select status
		from `tabInvoice Discounting` id, `tabDiscounted Invoice` d
		where
			id.name = d.parent
			and d.sales_invoice=%s
			and id.docstatus=1
			and status in ('Disbursed', 'Settled')
	""", sales_invoice)

	for d in invoice_discounting_list:
		status = d[0]
		if status == "Disbursed":
			break

	return status

def validate_inter_company_party(doctype, party, company, inter_company_reference):
	if not party:
		return

	if doctype in ["Sales Invoice", "Sales Order"]:
		partytype, ref_partytype, internal = "Customer", "Supplier", "is_internal_customer"

		if doctype == "Sales Invoice":
			ref_doc = "Purchase Invoice"
		else:
			ref_doc = "Purchase Order"
	else:
		partytype, ref_partytype, internal = "Supplier", "Customer", "is_internal_supplier"

		if doctype == "Purchase Invoice":
			ref_doc = "Sales Invoice"
		else:
			ref_doc = "Sales Order"

	if inter_company_reference:
		doc = frappe.get_doc(ref_doc, inter_company_reference)
		ref_party = doc.supplier if doctype in ["Sales Invoice", "Sales Order"] else doc.customer
		if not frappe.db.get_value(partytype, {"represents_company": doc.company}, "name") == party:
			frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(partytype))
		if not frappe.get_cached_value(ref_partytype, ref_party, "represents_company") == company:
			frappe.throw(_("Invalid Company for Inter Company Transaction."))

	elif frappe.db.get_value(partytype, {"name": party, internal: 1}, "name") == party:
		companies = frappe.get_all("Allowed To Transact With", fields=["company"], filters={"parenttype": partytype, "parent": party})
		companies = [d.company for d in companies]
		if not company in companies:
			frappe.throw(_("{0} not allowed to transact with {1}. Please change the Company.").format(partytype, company))

def update_linked_doc(doctype, name, inter_company_reference):

	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_field = "inter_company_invoice_reference"
	else:
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, inter_company_reference,\
			ref_field, name)

def unlink_inter_company_doc(doctype, name, inter_company_reference):

	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Sales Invoice"
		ref_field = "inter_company_invoice_reference"
	else:
		ref_doc = "Purchase Order" if doctype == "Sales Order" else "Sales Order"
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, name, ref_field, "")
		frappe.db.set_value(ref_doc, inter_company_reference, ref_field, "")

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Invoices'),
	})
	return list_context

@frappe.whitelist()
def get_bank_cash_account(mode_of_payment, company):
	account = frappe.db.get_value("Mode of Payment Account",
		{"parent": mode_of_payment, "company": company}, "default_account")
	if not account:
		frappe.throw(_("Please set default Cash or Bank account in Mode of Payment {0}")
			.format(get_link_to_form("Mode of Payment", mode_of_payment)), title=_("Missing Account"))
	return {
		"account": account
	}

@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Maintenance Schedule",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Invoice Item": {
			"doctype": "Maintenance Schedule Item",
		},
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
		target_doc.stock_qty = target_doc.qty * flt(source_doc.conversion_factor)

		target_doc.base_amount = target_doc.qty * flt(source_doc.base_rate)
		target_doc.amount = target_doc.qty * flt(source_doc.rate)

	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Invoice Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"name": "si_detail",
				"parent": "against_sales_invoice",
				"serial_no": "serial_no",
				"sales_order": "against_sales_order",
				"so_detail": "so_detail",
				"cost_center": "cost_center"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.delivered_by_supplier!=1
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Sales Invoice", source_name, target_doc)

def set_account_for_mode_of_payment(self):
	for data in self.payments:
		if not data.account:
			data.account = get_bank_cash_account(data.mode_of_payment, self.company).get("account")

def get_inter_company_details(doc, doctype):
	if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"]:
		parties = frappe.db.get_all("Supplier", fields=["name"], filters={"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company})
		company = frappe.get_cached_value("Customer", doc.customer, "represents_company")

		if not parties:
			frappe.throw(_('No Supplier found for Inter Company Transactions which represents company {0}').format(frappe.bold(doc.company)))

		party = get_internal_party(parties, "Supplier", doc)
	else:
		parties = frappe.db.get_all("Customer", fields=["name"], filters={"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company})
		company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

		if not parties:
			frappe.throw(_('No Customer found for Inter Company Transactions which represents company {0}').format(frappe.bold(doc.company)))

		party = get_internal_party(parties, "Customer", doc)

	return {
		"party": party,
		"company": company
	}

def get_internal_party(parties, link_doctype, doc):
	if len(parties) == 1:
			party = parties[0].name
	else:
		# If more than one Internal Supplier/Customer, get supplier/customer on basis of address
		if doc.get('company_address') or doc.get('shipping_address'):
			party = frappe.db.get_value("Dynamic Link", {"parent": doc.get('company_address') or doc.get('shipping_address'),
			"parenttype": "Address", "link_doctype": link_doctype}, "link_name")

			if not party:
				party = parties[0].name
		else:
			party = parties[0].name

	return party

def validate_inter_company_transaction(doc, doctype):

	details = get_inter_company_details(doc, doctype)
	price_list = doc.selling_price_list if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"] else doc.buying_price_list
	valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	if not valid_price_list and not doc.is_internal_transfer():
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))

	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

	company = details.get("company")
	default_currency = frappe.get_cached_value('Company', company, "default_currency")
	if default_currency != doc.currency:
		frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))

	return

@frappe.whitelist()
def make_inter_company_purchase_invoice(source_name, target_doc=None):
	return make_inter_company_transaction("Sales Invoice", source_name, target_doc)

def make_inter_company_transaction(doctype, source_name, target_doc=None):
	if doctype in ["Sales Invoice", "Sales Order"]:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
		target_detail_field = "sales_invoice_item" if doctype == "Sales Invoice" else "sales_order_item"
		source_document_warehouse_field = 'target_warehouse'
		target_document_warehouse_field = 'from_warehouse'
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"
		source_document_warehouse_field = 'from_warehouse'
		target_document_warehouse_field = 'target_warehouse'

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

	def update_details(source_doc, target_doc, source_parent):
		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			currency = frappe.db.get_value('Supplier', details.get('party'), 'default_currency')
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.is_internal_supplier = 1
			target_doc.ignore_pricing_rule = 1
			target_doc.buying_price_list = source_doc.selling_price_list

			# Invert Addresses
			update_address(target_doc, 'supplier_address', 'address_display', source_doc.company_address)
			update_address(target_doc, 'shipping_address', 'shipping_address_display', source_doc.customer_address)

			if currency:
				target_doc.currency = currency

			update_taxes(target_doc, party=target_doc.supplier, party_type='Supplier', company=target_doc.company,
				doctype=target_doc.doctype, party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address)

		else:
			currency = frappe.db.get_value('Customer', details.get('party'), 'default_currency')
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list

			update_address(target_doc, 'company_address', 'company_address_display', source_doc.supplier_address)
			update_address(target_doc, 'shipping_address_name', 'shipping_address', source_doc.shipping_address)
			update_address(target_doc, 'customer_address', 'address_display', source_doc.shipping_address)

			if currency:
				target_doc.currency = currency

			update_taxes(target_doc, party=target_doc.customer, party_type='Customer', company=target_doc.company,
				doctype=target_doc.doctype, party_address=target_doc.customer_address,
				company_address=target_doc.company_address, shipping_address_name=target_doc.shipping_address_name)

	item_field_map = {
		"doctype": target_doctype + " Item",
		"field_no_map": [
			"income_account",
			"expense_account",
			"cost_center",
			"warehouse"
		],
		"field_map": {
			'rate': 'rate',
		}
	}

	if doctype in ["Sales Invoice", "Sales Order"]:
		item_field_map["field_map"].update({
			"name": target_detail_field,
		})

	if source_doc.get('update_stock'):
		item_field_map["field_map"].update({
			source_document_warehouse_field: target_document_warehouse_field,
			'batch_no': 'batch_no',
			'serial_no': 'serial_no'
		})

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": target_doctype,
			"postprocess": update_details,
			"set_target_warehouse": "set_from_warehouse",
			"field_no_map": [
				"taxes_and_charges",
				"set_warehouse",
				"shipping_address"
			]
		},
		doctype +" Item": item_field_map

	}, target_doc, set_missing_values)

	return doclist

def set_purchase_references(doc):
	# add internal PO or PR links if any
	if doc.is_internal_transfer():
		if doc.doctype == 'Purchase Receipt':
			so_item_map = get_delivery_note_details(doc.inter_company_invoice_reference)

			if so_item_map:
				pd_item_map, parent_child_map, warehouse_map = \
					get_pd_details('Purchase Order Item', so_item_map, 'sales_order_item')

				update_pr_items(doc, so_item_map, pd_item_map, parent_child_map, warehouse_map)

		elif doc.doctype == 'Purchase Invoice':
			dn_item_map, so_item_map = get_sales_invoice_details(doc.inter_company_invoice_reference)
			# First check for Purchase receipt
			if list(dn_item_map.values()):
				pd_item_map, parent_child_map, warehouse_map = \
					get_pd_details('Purchase Receipt Item', dn_item_map, 'delivery_note_item')

				update_pi_items(doc, 'pr_detail', 'purchase_receipt',
					dn_item_map, pd_item_map, parent_child_map, warehouse_map)

			if list(so_item_map.values()):
				pd_item_map, parent_child_map, warehouse_map = \
					get_pd_details('Purchase Order Item', so_item_map, 'sales_order_item')

				update_pi_items(doc, 'po_detail', 'purchase_order',
					so_item_map, pd_item_map, parent_child_map, warehouse_map)

def update_pi_items(doc, detail_field, parent_field, sales_item_map,
	purchase_item_map, parent_child_map, warehouse_map):
	for item in doc.get('items'):
		item.set(detail_field, purchase_item_map.get(sales_item_map.get(item.sales_invoice_item)))
		item.set(parent_field, parent_child_map.get(sales_item_map.get(item.sales_invoice_item)))
		if doc.update_stock:
			item.warehouse = warehouse_map.get(sales_item_map.get(item.sales_invoice_item))

def update_pr_items(doc, sales_item_map, purchase_item_map, parent_child_map, warehouse_map):
	for item in doc.get('items'):
		item.purchase_order_item = purchase_item_map.get(sales_item_map.get(item.delivery_note_item))
		item.warehouse = warehouse_map.get(sales_item_map.get(item.delivery_note_item))
		item.purchase_order = parent_child_map.get(sales_item_map.get(item.delivery_note_item))

def get_delivery_note_details(internal_reference):
	so_item_map = {}

	si_item_details = frappe.get_all('Delivery Note Item', fields=['name', 'so_detail'],
		filters={'parent': internal_reference})

	for d in si_item_details:
		so_item_map.setdefault(d.name, d.so_detail)

	return so_item_map

def get_sales_invoice_details(internal_reference):
	dn_item_map = {}
	so_item_map = {}

	si_item_details = frappe.get_all('Sales Invoice Item', fields=['name', 'so_detail',
		'dn_detail'], filters={'parent': internal_reference})

	for d in si_item_details:
		if d.dn_detail:
			dn_item_map.setdefault(d.name, d.dn_detail)
		if d.so_detail:
			so_item_map.setdefault(d.name, d.so_detail)

	return dn_item_map, so_item_map

def get_pd_details(doctype, sd_detail_map, sd_detail_field):
	pd_item_map = {}
	accepted_warehouse_map = {}
	parent_child_map = {}

	pd_item_details = frappe.get_all(doctype,
		fields=[sd_detail_field, 'name', 'warehouse', 'parent'], filters={sd_detail_field: ('in', list(sd_detail_map.values()))})

	for d in pd_item_details:
		pd_item_map.setdefault(d.get(sd_detail_field), d.name)
		parent_child_map.setdefault(d.get(sd_detail_field), d.parent)
		accepted_warehouse_map.setdefault(d.get(sd_detail_field), d.warehouse)

	return pd_item_map, parent_child_map, accepted_warehouse_map

def update_taxes(doc, party=None, party_type=None, company=None, doctype=None, party_address=None,
	company_address=None, shipping_address_name=None, master_doctype=None):
	# Update Party Details
	party_details = get_party_details(party=party, party_type=party_type, company=company,
		doctype=doctype, party_address=party_address, company_address=company_address,
		shipping_address=shipping_address_name)

	# Update taxes and charges if any
	doc.taxes_and_charges = party_details.get('taxes_and_charges')
	doc.set('taxes', party_details.get('taxes'))

def update_address(doc, address_field, address_display_field, address_name):
	doc.set(address_field, address_name)
	fetch_values = get_fetch_values(doc.doctype, address_field, address_name)

	for key, value in fetch_values.items():
		doc.set(key, value)

	doc.set(address_display_field, get_address_display(doc.get(address_field)))

@frappe.whitelist()
def get_loyalty_programs(customer):
	''' sets applicable loyalty program to the customer or returns a list of applicable programs '''
	from erpnext.selling.doctype.customer.customer import get_loyalty_programs

	customer = frappe.get_doc('Customer', customer)
	if customer.loyalty_program: return [customer.loyalty_program]

	lp_details = get_loyalty_programs(customer)

	if len(lp_details) == 1:
		frappe.db.set(customer, 'loyalty_program', lp_details[0])
		return lp_details
	else:
		return lp_details

def on_doctype_update():
	frappe.db.add_index("Sales Invoice", ["customer", "is_return", "return_against"])

@frappe.whitelist()
def create_invoice_discounting(source_name, target_doc=None):
	invoice = frappe.get_doc("Sales Invoice", source_name)
	invoice_discounting = frappe.new_doc("Invoice Discounting")
	invoice_discounting.company = invoice.company
	invoice_discounting.append("invoices", {
		"sales_invoice": source_name,
		"customer": invoice.customer,
		"posting_date": invoice.posting_date,
		"outstanding_amount": invoice.outstanding_amount
	})

	return invoice_discounting

def update_multi_mode_option(doc, pos_profile):
	def append_payment(payment_mode):
		payment = doc.append('payments', {})
		payment.default = payment_mode.default
		payment.mode_of_payment = payment_mode.parent
		payment.account = payment_mode.default_account
		payment.type = payment_mode.type

	doc.set('payments', [])
	invalid_modes = []
	for pos_payment_method in pos_profile.get('payments'):
		pos_payment_method = pos_payment_method.as_dict()

		payment_mode = get_mode_of_payment_info(pos_payment_method.mode_of_payment, doc.company)
		if not payment_mode:
			invalid_modes.append(get_link_to_form("Mode of Payment", pos_payment_method.mode_of_payment))
			continue

		payment_mode[0].default = pos_payment_method.default
		append_payment(payment_mode[0])

	if invalid_modes:
		if invalid_modes == 1:
			msg = _("Please set default Cash or Bank account in Mode of Payment {}")
		else:
			msg = _("Please set default Cash or Bank account in Mode of Payments {}")
		frappe.throw(msg.format(", ".join(invalid_modes)), title=_("Missing Account"))

def get_all_mode_of_payments(doc):
	return frappe.db.sql("""
		select mpa.default_account, mpa.parent, mp.type as type
		from `tabMode of Payment Account` mpa,`tabMode of Payment` mp
		where mpa.parent = mp.name and mpa.company = %(company)s and mp.enabled = 1""",
	{'company': doc.company}, as_dict=1)

def get_mode_of_payment_info(mode_of_payment, company):
	return frappe.db.sql("""
		select mpa.default_account, mpa.parent, mp.type as type
		from `tabMode of Payment Account` mpa,`tabMode of Payment` mp
		where mpa.parent = mp.name and mpa.company = %s and mp.enabled = 1 and mp.name = %s""",
	(company, mode_of_payment), as_dict=1)

@frappe.whitelist()
def create_dunning(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	from erpnext.accounts.doctype.dunning.dunning import get_dunning_letter_text, calculate_interest_and_amount
	def set_missing_values(source, target):
		target.sales_invoice = source_name
		target.outstanding_amount = source.outstanding_amount
		overdue_days = (getdate(target.posting_date) - getdate(source.due_date)).days
		target.overdue_days = overdue_days
		if frappe.db.exists('Dunning Type', {'start_day': [
	                                '<', overdue_days], 'end_day': ['>=', overdue_days]}):
			dunning_type = frappe.get_doc('Dunning Type', {'start_day': [
	                                '<', overdue_days], 'end_day': ['>=', overdue_days]})
			target.dunning_type = dunning_type.name
			target.rate_of_interest = dunning_type.rate_of_interest
			target.dunning_fee = dunning_type.dunning_fee
			letter_text = get_dunning_letter_text(dunning_type = dunning_type.name, doc = target.as_dict())
			if letter_text:
				target.body_text = letter_text.get('body_text')
				target.closing_text = letter_text.get('closing_text')
				target.language = letter_text.get('language')
			amounts = calculate_interest_and_amount(target.posting_date, target.outstanding_amount,
				target.rate_of_interest, target.dunning_fee, target.overdue_days)
			target.interest_amount = amounts.get('interest_amount')
			target.dunning_amount = amounts.get('dunning_amount')
			target.grand_total = amounts.get('grand_total')

	doclist = get_mapped_doc("Sales Invoice", source_name,	{
		"Sales Invoice": {
			"doctype": "Dunning",
		}
	}, target_doc, set_missing_values)
	return doclist
