# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import comma_or, flt, get_link_to_form, getdate, now, nowdate


class OverAllowanceError(frappe.ValidationError):
	pass


def validate_status(status, options):
	if status not in options:
		frappe.throw(_("Status must be one of {0}").format(comma_or(options)))


status_map = {
	"Lead": [
		["Lost Quotation", "has_lost_quotation"],
		["Opportunity", "has_opportunity"],
		["Quotation", "has_quotation"],
		["Converted", "has_customer"],
	],
	"Opportunity": [
		["Lost", "eval:self.status=='Lost'"],
		["Lost", "has_lost_quotation"],
		["Quotation", "has_active_quotation"],
		["Converted", "has_ordered_quotation"],
		["Closed", "eval:self.status=='Closed'"],
	],
	"Quotation": [
		["Draft", None],
		["Open", "eval:self.docstatus==1"],
		["Lost", "eval:self.status=='Lost'"],
		["Partially Ordered", "is_partially_ordered"],
		["Ordered", "is_fully_ordered"],
		["Cancelled", "eval:self.docstatus==2"],
	],
	"Sales Order": [
		["Draft", None],
		[
			"To Deliver and Bill",
			"eval:self.per_delivered < 100 and self.per_billed < 100 and self.docstatus == 1",
		],
		[
			"To Bill",
			"eval:(self.per_delivered >= 100 or self.skip_delivery_note) and self.per_billed < 100 and self.docstatus == 1",
		],
		[
			"To Deliver",
			"eval:self.per_delivered < 100 and self.per_billed >= 100 and self.docstatus == 1 and not self.skip_delivery_note",
		],
		[
			"Completed",
			"eval:(self.per_delivered >= 100 or self.skip_delivery_note) and self.per_billed >= 100 and self.docstatus == 1",
		],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed' and self.docstatus != 2"],
		["On Hold", "eval:self.status=='On Hold'"],
	],
	"Purchase Order": [
		["Draft", None],
		[
			"To Receive and Bill",
			"eval:self.per_received < 100 and self.per_billed < 100 and self.docstatus == 1",
		],
		["To Bill", "eval:self.per_received >= 100 and self.per_billed < 100 and self.docstatus == 1"],
		[
			"To Receive",
			"eval:self.per_received < 100 and self.per_billed == 100 and self.docstatus == 1",
		],
		[
			"Completed",
			"eval:self.per_received >= 100 and self.per_billed == 100 and self.docstatus == 1",
		],
		["Delivered", "eval:self.status=='Delivered'"],
		["Cancelled", "eval:self.docstatus==2"],
		["On Hold", "eval:self.status=='On Hold'"],
		["Closed", "eval:self.status=='Closed' and self.docstatus != 2"],
	],
	"Delivery Note": [
		["Draft", None],
		["To Bill", "eval:self.per_billed < 100 and self.docstatus == 1"],
		["Return Issued", "eval:self.per_returned == 100 and self.docstatus == 1"],
		["Completed", "eval:self.per_billed == 100 and self.docstatus == 1"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed' and self.docstatus != 2"],
	],
	"Purchase Receipt": [
		["Draft", None],
		["To Bill", "eval:self.per_billed < 100 and self.docstatus == 1"],
		["Return Issued", "eval:self.per_returned == 100 and self.docstatus == 1"],
		["Completed", "eval:self.per_billed == 100 and self.docstatus == 1"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed' and self.docstatus != 2"],
	],
	"Material Request": [
		["Draft", None],
		["Stopped", "eval:self.status == 'Stopped'"],
		["Cancelled", "eval:self.docstatus == 2"],
		["Pending", "eval:self.status != 'Stopped' and self.per_ordered == 0 and self.docstatus == 1"],
		[
			"Ordered",
			"eval:self.status != 'Stopped' and self.per_ordered == 100 and self.docstatus == 1 and self.material_request_type == 'Purchase'",
		],
		[
			"Transferred",
			"eval:self.status != 'Stopped' and self.per_ordered == 100 and self.docstatus == 1 and self.material_request_type == 'Material Transfer'",
		],
		[
			"Issued",
			"eval:self.status != 'Stopped' and self.per_ordered == 100 and self.docstatus == 1 and self.material_request_type == 'Material Issue'",
		],
		[
			"Received",
			"eval:self.status != 'Stopped' and self.per_received == 100 and self.docstatus == 1 and self.material_request_type == 'Purchase'",
		],
		[
			"Partially Received",
			"eval:self.status != 'Stopped' and self.per_received > 0 and self.per_received < 100 and self.docstatus == 1 and self.material_request_type == 'Purchase'",
		],
		[
			"Partially Ordered",
			"eval:self.status != 'Stopped' and self.per_ordered < 100 and self.per_ordered > 0 and self.docstatus == 1",
		],
		[
			"Manufactured",
			"eval:self.status != 'Stopped' and self.per_ordered == 100 and self.docstatus == 1 and self.material_request_type == 'Manufacture'",
		],
	],
	"Bank Transaction": [
		["Unreconciled", "eval:self.docstatus == 1 and self.unallocated_amount>0"],
		["Reconciled", "eval:self.docstatus == 1 and self.unallocated_amount<=0"],
		["Cancelled", "eval:self.docstatus == 2"],
	],
	"POS Opening Entry": [
		["Draft", None],
		["Open", "eval:self.docstatus == 1 and not self.pos_closing_entry"],
		["Closed", "eval:self.docstatus == 1 and self.pos_closing_entry"],
		["Cancelled", "eval:self.docstatus == 2"],
	],
	"POS Closing Entry": [
		["Draft", None],
		["Submitted", "eval:self.docstatus == 1"],
		["Queued", "eval:self.status == 'Queued'"],
		["Failed", "eval:self.status == 'Failed'"],
		["Cancelled", "eval:self.docstatus == 2"],
	],
	"Transaction Deletion Record": [
		["Draft", None],
		["Completed", "eval:self.docstatus == 1"],
	],
}


class StatusUpdater(Document):
	"""
	Updates the status of the calling records
	Delivery Note: Update Delivered Qty, Update Percent and Validate over delivery
	Sales Invoice: Update Billed Amt, Update Percent and Validate over billing
	Installation Note: Update Installed Qty, Update Percent Qty and Validate over installation
	"""

	def update_prevdoc_status(self):
		self.update_qty()
		self.validate_qty()

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		if self.doctype in status_map:
			_status = self.status
			if status and update:
				self.db_set("status", status)

			sl = status_map[self.doctype][:]
			sl.reverse()
			for s in sl:
				if not s[1]:
					self.status = s[0]
					break
				elif s[1].startswith("eval:"):
					if frappe.safe_eval(
						s[1][5:],
						None,
						{
							"self": self.as_dict(),
							"getdate": getdate,
							"nowdate": nowdate,
							"get_value": frappe.db.get_value,
						},
					):
						self.status = s[0]
						break
				elif getattr(self, s[1])():
					self.status = s[0]
					break

			if self.status != _status and self.status not in (
				"Cancelled",
				"Partially Ordered",
				"Ordered",
				"Issued",
				"Transferred",
			):
				self.add_comment("Label", _(self.status))

			if update:
				self.db_set("status", self.status, update_modified=update_modified)

	def validate_qty(self):
		"""Validates qty at row level"""
		self.item_allowance = {}
		self.global_qty_allowance = None
		self.global_amount_allowance = None

		for args in self.status_updater:
			if "target_ref_field" not in args:
				# if target_ref_field is not specified, the programmer does not want to validate qty / amount
				continue

			# get unique transactions to update
			for d in self.get_all_children():
				if hasattr(d, "qty") and d.qty < 0 and not self.get("is_return"):
					frappe.throw(_("For an item {0}, quantity must be positive number").format(d.item_code))

				if hasattr(d, "qty") and d.qty > 0 and self.get("is_return"):
					frappe.throw(_("For an item {0}, quantity must be negative number").format(d.item_code))

				if not frappe.db.get_single_value("Selling Settings", "allow_negative_rates_for_items"):
					if hasattr(d, "item_code") and hasattr(d, "rate") and flt(d.rate) < 0:
						frappe.throw(
							_(
								"For item {0}, rate must be a positive number. To Allow negative rates, enable {1} in {2}"
							).format(
								frappe.bold(d.item_code),
								frappe.bold(_("`Allow Negative rates for Items`")),
								get_link_to_form("Selling Settings", "Selling Settings"),
							),
						)

				if d.doctype == args["source_dt"] and d.get(args["join_field"]):
					args["name"] = d.get(args["join_field"])

					# get all qty where qty > target_field
					item = frappe.db.sql(
						"""select item_code, `{target_ref_field}`,
						`{target_field}`, parenttype, parent from `tab{target_dt}`
						where `{target_ref_field}` < `{target_field}`
						and name=%s and docstatus=1""".format(
							**args
						),
						args["name"],
						as_dict=1,
					)
					if item:
						item = item[0]
						item["idx"] = d.idx
						item["target_ref_field"] = args["target_ref_field"].replace("_", " ")

						# if not item[args['target_ref_field']]:
						# 	msgprint(_("Note: System will not check over-delivery and over-booking for Item {0} as quantity or amount is 0").format(item.item_code))
						if args.get("no_allowance"):
							item["reduce_by"] = item[args["target_field"]] - item[args["target_ref_field"]]
							if item["reduce_by"] > 0.01:
								self.limits_crossed_error(args, item, "qty")

						elif item[args["target_ref_field"]]:
							self.check_overflow_with_allowance(item, args)

	def check_overflow_with_allowance(self, item, args):
		"""
		Checks if there is overflow condering a relaxation allowance
		"""
		qty_or_amount = "qty" if "qty" in args["target_ref_field"] else "amount"

		# check if overflow is within allowance
		(
			allowance,
			self.item_allowance,
			self.global_qty_allowance,
			self.global_amount_allowance,
		) = get_allowance_for(
			item["item_code"],
			self.item_allowance,
			self.global_qty_allowance,
			self.global_amount_allowance,
			qty_or_amount,
		)

		role_allowed_to_over_deliver_receive = frappe.db.get_single_value(
			"Stock Settings", "role_allowed_to_over_deliver_receive"
		)
		role_allowed_to_over_bill = frappe.db.get_single_value(
			"Accounts Settings", "role_allowed_to_over_bill"
		)
		role = (
			role_allowed_to_over_deliver_receive if qty_or_amount == "qty" else role_allowed_to_over_bill
		)

		overflow_percent = (
			(item[args["target_field"]] - item[args["target_ref_field"]]) / item[args["target_ref_field"]]
		) * 100

		if overflow_percent - allowance > 0.01:
			item["max_allowed"] = flt(item[args["target_ref_field"]] * (100 + allowance) / 100)
			item["reduce_by"] = item[args["target_field"]] - item["max_allowed"]

			if role not in frappe.get_roles():
				self.limits_crossed_error(args, item, qty_or_amount)
			else:
				self.warn_about_bypassing_with_role(item, qty_or_amount, role)

	def limits_crossed_error(self, args, item, qty_or_amount):
		"""Raise exception for limits crossed"""
		if (
			self.doctype in ["Sales Invoice", "Delivery Note"]
			and qty_or_amount == "amount"
			and self.is_internal_customer
		):
			return

		elif (
			self.doctype in ["Purchase Invoice", "Purchase Receipt"]
			and qty_or_amount == "amount"
			and self.is_internal_supplier
		):
			return

		if qty_or_amount == "qty":
			action_msg = _(
				'To allow over receipt / delivery, update "Over Receipt/Delivery Allowance" in Stock Settings or the Item.'
			)
		else:
			action_msg = _(
				'To allow over billing, update "Over Billing Allowance" in Accounts Settings or the Item.'
			)

		frappe.throw(
			_(
				"This document is over limit by {0} {1} for item {4}. Are you making another {3} against the same {2}?"
			).format(
				frappe.bold(_(item["target_ref_field"].title())),
				frappe.bold(item["reduce_by"]),
				frappe.bold(_(args.get("target_dt"))),
				frappe.bold(_(self.doctype)),
				frappe.bold(item.get("item_code")),
			)
			+ "<br><br>"
			+ action_msg,
			OverAllowanceError,
			title=_("Limit Crossed"),
		)

	def warn_about_bypassing_with_role(self, item, qty_or_amount, role):
		if qty_or_amount == "qty":
			msg = _("Over Receipt/Delivery of {0} {1} ignored for item {2} because you have {3} role.")
		else:
			msg = _("Overbilling of {0} {1} ignored for item {2} because you have {3} role.")

		frappe.msgprint(
			msg.format(
				_(item["target_ref_field"].title()),
				frappe.bold(item["reduce_by"]),
				frappe.bold(item.get("item_code")),
				role,
			),
			indicator="orange",
			alert=True,
		)

	def update_qty(self, update_modified=True):
		"""Updates qty or amount at row level

		:param update_modified: If true, updates `modified` and `modified_by` for target parent doc
		"""
		for args in self.status_updater:
			# condition to include current record (if submit or no if cancel)
			if self.docstatus == 1:
				args["cond"] = " or parent='%s'" % self.name.replace('"', '"')
			else:
				args["cond"] = " and parent!='%s'" % self.name.replace('"', '"')

			self._update_children(args, update_modified)

			if "percent_join_field" in args or "percent_join_field_parent" in args:
				self._update_percent_field_in_targets(args, update_modified)

	def _update_children(self, args, update_modified):
		"""Update quantities or amount in child table"""
		for d in self.get_all_children():
			if d.doctype != args["source_dt"]:
				continue

			self._update_modified(args, update_modified)

			# updates qty in the child table
			args["detail_id"] = d.get(args["join_field"])

			args["second_source_condition"] = ""
			if (
				args.get("second_source_dt")
				and args.get("second_source_field")
				and args.get("second_join_field")
			):
				if not args.get("second_source_extra_cond"):
					args["second_source_extra_cond"] = ""

				args["second_source_condition"] = frappe.db.sql(
					""" select ifnull((select sum(%(second_source_field)s)
					from `tab%(second_source_dt)s`
					where `%(second_join_field)s`='%(detail_id)s'
					and (`tab%(second_source_dt)s`.docstatus=1)
					%(second_source_extra_cond)s), 0) """
					% args
				)[0][0]

			if args["detail_id"]:
				if not args.get("extra_cond"):
					args["extra_cond"] = ""

				args["source_dt_value"] = (
					frappe.db.sql(
						"""
						(select ifnull(sum(%(source_field)s), 0)
							from `tab%(source_dt)s` where `%(join_field)s`='%(detail_id)s'
							and (docstatus=1 %(cond)s) %(extra_cond)s)
				"""
						% args
					)[0][0]
					or 0.0
				)

				if args["second_source_condition"]:
					args["source_dt_value"] += flt(args["second_source_condition"])

				frappe.db.sql(
					"""update `tab%(target_dt)s`
					set %(target_field)s = %(source_dt_value)s %(update_modified)s
					where name='%(detail_id)s'"""
					% args
				)

	def _update_percent_field_in_targets(self, args, update_modified=True):
		"""Update percent field in parent transaction"""
		if args.get("percent_join_field_parent"):
			# if reference to target doc where % is to be updated, is
			# in source doc's parent form, consider percent_join_field_parent
			args["name"] = self.get(args["percent_join_field_parent"])
			self._update_percent_field(args, update_modified)
		else:
			distinct_transactions = set(
				d.get(args["percent_join_field"]) for d in self.get_all_children(args["source_dt"])
			)

			for name in distinct_transactions:
				if name:
					args["name"] = name
					self._update_percent_field(args, update_modified)

	def _update_percent_field(self, args, update_modified=True):
		"""Update percent field in parent transaction"""

		self._update_modified(args, update_modified)

		if args.get("target_parent_field"):
			frappe.db.sql(
				"""update `tab%(target_parent_dt)s`
				set %(target_parent_field)s = round(
					ifnull((select
						ifnull(sum(case when abs(%(target_ref_field)s) > abs(%(target_field)s) then abs(%(target_field)s) else abs(%(target_ref_field)s) end), 0)
						/ sum(abs(%(target_ref_field)s)) * 100
					from `tab%(target_dt)s` where parent='%(name)s' and parenttype='%(target_parent_dt)s' having sum(abs(%(target_ref_field)s)) > 0), 0), 6)
					%(update_modified)s
				where name='%(name)s'"""
				% args
			)

			# update field
			if args.get("status_field"):
				frappe.db.sql(
					"""update `tab%(target_parent_dt)s`
					set %(status_field)s = (case when %(target_parent_field)s<0.001 then 'Not %(keyword)s'
					else case when %(target_parent_field)s>=99.999999 then 'Fully %(keyword)s'
					else 'Partly %(keyword)s' end end)
					where name='%(name)s'"""
					% args
				)

			if update_modified:
				target = frappe.get_doc(args["target_parent_dt"], args["name"])
				target.set_status(update=True)
				target.notify_update()

	def _update_modified(self, args, update_modified):
		if not update_modified:
			args["update_modified"] = ""
			return

		args["update_modified"] = ", modified = {0}, modified_by = {1}".format(
			frappe.db.escape(now()), frappe.db.escape(frappe.session.user)
		)

	def update_billing_status_for_zero_amount_refdoc(self, ref_dt):
		ref_fieldname = frappe.scrub(ref_dt)

		ref_docs = [
			item.get(ref_fieldname) for item in (self.get("items") or []) if item.get(ref_fieldname)
		]
		if not ref_docs:
			return

		zero_amount_refdocs = frappe.db.sql_list(
			"""
			SELECT
				name
			from
				`tab{ref_dt}`
			where
				docstatus = 1
				and base_net_total = 0
				and name in %(ref_docs)s
		""".format(
				ref_dt=ref_dt
			),
			{"ref_docs": ref_docs},
		)

		if zero_amount_refdocs:
			self.update_billing_status(zero_amount_refdocs, ref_dt, ref_fieldname)

	def update_billing_status(self, zero_amount_refdoc, ref_dt, ref_fieldname):
		for ref_dn in zero_amount_refdoc:
			ref_doc_qty = flt(
				frappe.db.sql(
					"""select ifnull(sum(qty), 0) from `tab%s Item`
				where parent=%s"""
					% (ref_dt, "%s"),
					(ref_dn),
				)[0][0]
			)

			billed_qty = flt(
				frappe.db.sql(
					"""select ifnull(sum(qty), 0)
				from `tab%s Item` where %s=%s and docstatus=1"""
					% (self.doctype, ref_fieldname, "%s"),
					(ref_dn),
				)[0][0]
			)

			per_billed = (min(ref_doc_qty, billed_qty) / ref_doc_qty) * 100

			ref_doc = frappe.get_doc(ref_dt, ref_dn)

			ref_doc.db_set("per_billed", per_billed)

			# set billling status
			if hasattr(ref_doc, "billing_status"):
				if ref_doc.per_billed < 0.001:
					ref_doc.db_set("billing_status", "Not Billed")
				elif ref_doc.per_billed > 99.999999:
					ref_doc.db_set("billing_status", "Fully Billed")
				else:
					ref_doc.db_set("billing_status", "Partly Billed")

			ref_doc.set_status(update=True)


def get_allowance_for(
	item_code,
	item_allowance=None,
	global_qty_allowance=None,
	global_amount_allowance=None,
	qty_or_amount="qty",
):
	"""
	Returns the allowance for the item, if not set, returns global allowance
	"""
	if item_allowance is None:
		item_allowance = {}
	if qty_or_amount == "qty":
		if item_allowance.get(item_code, frappe._dict()).get("qty"):
			return (
				item_allowance[item_code].qty,
				item_allowance,
				global_qty_allowance,
				global_amount_allowance,
			)
	else:
		if item_allowance.get(item_code, frappe._dict()).get("amount"):
			return (
				item_allowance[item_code].amount,
				item_allowance,
				global_qty_allowance,
				global_amount_allowance,
			)

	qty_allowance, over_billing_allowance = frappe.db.get_value(
		"Item", item_code, ["over_delivery_receipt_allowance", "over_billing_allowance"]
	)

	if qty_or_amount == "qty" and not qty_allowance:
		if global_qty_allowance == None:
			global_qty_allowance = flt(
				frappe.db.get_single_value("Stock Settings", "over_delivery_receipt_allowance")
			)
		qty_allowance = global_qty_allowance
	elif qty_or_amount == "amount" and not over_billing_allowance:
		if global_amount_allowance == None:
			global_amount_allowance = flt(
				frappe.db.get_single_value("Accounts Settings", "over_billing_allowance")
			)
		over_billing_allowance = global_amount_allowance

	if qty_or_amount == "qty":
		allowance = qty_allowance
		item_allowance.setdefault(item_code, frappe._dict()).setdefault("qty", qty_allowance)
	else:
		allowance = over_billing_allowance
		item_allowance.setdefault(item_code, frappe._dict()).setdefault("amount", over_billing_allowance)

	return allowance, item_allowance, global_qty_allowance, global_amount_allowance
