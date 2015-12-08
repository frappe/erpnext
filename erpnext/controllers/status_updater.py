# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, comma_or
from frappe import msgprint, _, throw
from frappe.model.document import Document

def validate_status(status, options):
	if status not in options:
		frappe.throw(_("Status must be one of {0}").format(comma_or(options)))

status_map = {
	"Lead": [
		["Converted", "has_customer"],
		["Opportunity", "has_opportunity"],
	],
	"Opportunity": [
		["Lost", "eval:self.status=='Lost'"],
		["Quotation", "has_quotation"],
		["Converted", "has_ordered_quotation"]
	],
	"Quotation": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Lost", "eval:self.status=='Lost'"],
		["Ordered", "has_sales_order"],
		["Cancelled", "eval:self.docstatus==2"],
	],
	"Sales Order": [
		["Draft", None],
		["To Deliver and Bill", "eval:self.per_delivered < 100 and self.per_billed < 100 and self.docstatus == 1"],
		["To Bill", "eval:self.per_delivered == 100 and self.per_billed < 100 and self.docstatus == 1"],
		["To Deliver", "eval:self.per_delivered < 100 and self.per_billed == 100 and self.docstatus == 1"],
		["Completed", "eval:self.per_delivered == 100 and self.per_billed == 100 and self.docstatus == 1"],
		["Completed", "eval:self.order_type == 'Maintenance' and self.per_billed == 100 and self.docstatus == 1"],
		["Stopped", "eval:self.status=='Stopped'"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed'"],
	],
	"Purchase Order": [
		["Draft", None],
		["To Receive and Bill", "eval:self.per_received < 100 and self.per_billed < 100 and self.docstatus == 1"],
		["To Bill", "eval:self.per_received == 100 and self.per_billed < 100 and self.docstatus == 1"],
		["To Receive", "eval:self.per_received < 100 and self.per_billed == 100 and self.docstatus == 1"],
		["Completed", "eval:self.per_received == 100 and self.per_billed == 100 and self.docstatus == 1"],
		["Delivered", "eval:self.status=='Delivered'"],
		["Stopped", "eval:self.status=='Stopped'"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed'"],
	],
	"Delivery Note": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed'"],
	],
	"Purchase Receipt": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Cancelled", "eval:self.docstatus==2"],
		["Closed", "eval:self.status=='Closed'"],
	]
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
					if eval(s[1][5:]):
						self.status = s[0]
						break
				elif getattr(self, s[1])():
					self.status = s[0]
					break

			if self.status != _status and self.status not in ("Submitted", "Cancelled"):
				self.add_comment("Label", _(self.status))
			
			if update:
				frappe.db.set_value(self.doctype, self.name, "status", self.status, 
					update_modified=update_modified)

	def validate_qty(self):
		"""Validates qty at row level"""
		self.tolerance = {}
		self.global_tolerance = None

		for args in self.status_updater:
			if "target_ref_field" not in args:
				# if target_ref_field is not specified, the programmer does not want to validate qty / amount
				continue

			# get unique transactions to update
			for d in self.get_all_children():
				if d.doctype == args['source_dt'] and d.get(args["join_field"]):
					args['name'] = d.get(args['join_field'])

					# get all qty where qty > target_field
					item = frappe.db.sql("""select item_code, `{target_ref_field}`,
						`{target_field}`, parenttype, parent from `tab{target_dt}`
						where `{target_ref_field}` < `{target_field}`
						and name=%s and docstatus=1""".format(**args),
						args['name'], as_dict=1)
					if item:
						item = item[0]
						item['idx'] = d.idx
						item['target_ref_field'] = args['target_ref_field'].replace('_', ' ')

						if not item[args['target_ref_field']]:
							msgprint(_("Note: System will not check over-delivery and over-booking for Item {0} as quantity or amount is 0").format(item.item_code))
						elif args.get('no_tolerance'):
							item['reduce_by'] = item[args['target_field']] - item[args['target_ref_field']]
							if item['reduce_by'] > .01:
								msgprint(_("Allowance for over-{0} crossed for Item {1}")
									.format(args["overflow_type"], item.item_code))
								throw(_("{0} must be reduced by {1} or you should increase overflow tolerance")
									.format(_(item.target_ref_field.title()), item["reduce_by"]))

						else:
							self.check_overflow_with_tolerance(item, args)

	def check_overflow_with_tolerance(self, item, args):
		"""
			Checks if there is overflow condering a relaxation tolerance
		"""
		# check if overflow is within tolerance
		tolerance, self.tolerance, self.global_tolerance = get_tolerance_for(item['item_code'],
			self.tolerance, self.global_tolerance)

		overflow_percent = ((item[args['target_field']] - item[args['target_ref_field']]) /
		 	item[args['target_ref_field']]) * 100

		if overflow_percent - tolerance > 0.01:
			item['max_allowed'] = flt(item[args['target_ref_field']] * (100+tolerance)/100)
			item['reduce_by'] = item[args['target_field']] - item['max_allowed']

			msgprint(_("Allowance for over-{0} crossed for Item {1}.")
				.format(args["overflow_type"], item["item_code"]))
			throw(_("{0} must be reduced by {1} or you should increase overflow tolerance")
				.format(_(item["target_ref_field"].title()), item["reduce_by"]))

	def update_qty(self, change_modified=True):
		"""Updates qty or amount at row level

			:param change_modified: If true, updates `modified` and `modified_by` for target parent doc
		"""
		for args in self.status_updater:
			# condition to include current record (if submit or no if cancel)
			if self.docstatus == 1:
				args['cond'] = ' or parent="%s"' % self.name.replace('"', '\"')
			else:
				args['cond'] = ' and parent!="%s"' % self.name.replace('"', '\"')

			args['set_modified'] = ''
			if change_modified:
				args['set_modified'] = ', modified = now(), modified_by = "{0}"'\
					.format(frappe.db.escape(frappe.session.user))

			self._update_children(args)

			if "percent_join_field" in args:
				self._update_percent_field(args)

	def _update_children(self, args):
		"""Update quantities or amount in child table"""
		for d in self.get_all_children():
			if d.doctype != args['source_dt']:
				continue

			# updates qty in the child table
			args['detail_id'] = d.get(args['join_field'])

			args['second_source_condition'] = ""
			if args.get('second_source_dt') and args.get('second_source_field') \
					and args.get('second_join_field'):
				if not args.get("second_source_extra_cond"):
					args["second_source_extra_cond"] = ""

				args['second_source_condition'] = """ + ifnull((select sum(%(second_source_field)s)
					from `tab%(second_source_dt)s`
					where `%(second_join_field)s`="%(detail_id)s"
					and (`tab%(second_source_dt)s`.docstatus=1) %(second_source_extra_cond)s), 0) """ % args

			if args['detail_id']:
				if not args.get("extra_cond"): args["extra_cond"] = ""

				frappe.db.sql("""update `tab%(target_dt)s`
					set %(target_field)s = (select ifnull(sum(%(source_field)s), 0)
						from `tab%(source_dt)s` where `%(join_field)s`="%(detail_id)s"
						and (docstatus=1 %(cond)s) %(extra_cond)s) %(second_source_condition)s
					where name='%(detail_id)s'""" % args)

	def _update_percent_field(self, args):
		"""Update percent field in parent transaction"""
		unique_transactions = set([d.get(args['percent_join_field']) for d in self.get_all_children(args['source_dt'])])

		for name in unique_transactions:
			if not name:
				continue

			args['name'] = name

			# update percent complete in the parent table
			if args.get('target_parent_field'):
				frappe.db.sql("""update `tab%(target_parent_dt)s`
					set %(target_parent_field)s = round(
						ifnull((select
							ifnull(sum(if(%(target_ref_field)s > %(target_field)s, %(target_field)s, %(target_ref_field)s)), 0)
							/ sum(%(target_ref_field)s) * 100
						from `tab%(target_dt)s` where parent="%(name)s"), 0), 2)
						%(set_modified)s
					where name='%(name)s'""" % args)

			# update field
			if args.get('status_field'):
				frappe.db.sql("""update `tab%(target_parent_dt)s`
					set %(status_field)s = if(%(target_parent_field)s<0.001,
						'Not %(keyword)s', if(%(target_parent_field)s>=99.99,
						'Fully %(keyword)s', 'Partly %(keyword)s'))
					where name='%(name)s'""" % args)

			if args.get("set_modified"):
				target = frappe.get_doc(args["target_parent_dt"], name)
				target.set_status(update=True)
				target.notify_update()

	def update_billing_status_for_zero_amount_refdoc(self, ref_dt):
		ref_fieldname = ref_dt.lower().replace(" ", "_")
		zero_amount_refdoc = []
		all_zero_amount_refdoc = frappe.db.sql_list("""select name from `tab%s`
			where docstatus=1 and base_net_total = 0""" % ref_dt)

		for item in self.get("items"):
			if item.get(ref_fieldname) \
				and item.get(ref_fieldname) in all_zero_amount_refdoc \
				and item.get(ref_fieldname) not in zero_amount_refdoc:
					zero_amount_refdoc.append(item.get(ref_fieldname))

		if zero_amount_refdoc:
			self.update_billing_status(zero_amount_refdoc, ref_dt, ref_fieldname)

	def update_billing_status(self, zero_amount_refdoc, ref_dt, ref_fieldname):
		for ref_dn in zero_amount_refdoc:
			ref_doc_qty = flt(frappe.db.sql("""select ifnull(sum(qty), 0) from `tab%s Item`
				where parent=%s""" % (ref_dt, '%s'), (ref_dn))[0][0])

			billed_qty = flt(frappe.db.sql("""select ifnull(sum(qty), 0)
				from `tab%s Item` where %s=%s and docstatus=1""" %
				(self.doctype, ref_fieldname, '%s'), (ref_dn))[0][0])

			per_billed = ((ref_doc_qty if billed_qty > ref_doc_qty else billed_qty)\
				/ ref_doc_qty)*100
			frappe.db.set_value(ref_dt, ref_dn, "per_billed", per_billed)

			if frappe.get_meta(ref_dt).get_field("billing_status"):
				if per_billed < 0.001: billing_status = "Not Billed"
				elif per_billed >= 99.99: billing_status = "Fully Billed"
				else: billing_status = "Partly Billed"

				frappe.db.set_value(ref_dt, ref_dn, "billing_status", billing_status)

def get_tolerance_for(item_code, item_tolerance={}, global_tolerance=None):
	"""
		Returns the tolerance for the item, if not set, returns global tolerance
	"""
	if item_tolerance.get(item_code):
		return item_tolerance[item_code], item_tolerance, global_tolerance

	tolerance = flt(frappe.db.get_value('Item',item_code,'tolerance') or 0)

	if not tolerance:
		if global_tolerance == None:
			global_tolerance = flt(frappe.db.get_value('Stock Settings', None, 'tolerance'))
		tolerance = global_tolerance

	item_tolerance[item_code] = tolerance
	return tolerance, item_tolerance, global_tolerance
