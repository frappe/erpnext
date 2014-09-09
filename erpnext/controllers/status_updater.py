# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _, throw
from frappe.model.document import Document

status_map = {
	"Contact": [
		["Replied", "communication_sent"],
		["Open", "communication_received"]
	],
	"Job Applicant": [
		["Replied", "communication_sent"],
		["Open", "communication_received"]
	],
	"Lead": [
		["Replied", "communication_sent"],
		["Converted", "has_customer"],
		["Opportunity", "has_opportunity"],
		["Open", "communication_received"],
	],
	"Opportunity": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Lost", "eval:self.status=='Lost'"],
		["Quotation", "has_quotation"],
		["Replied", "communication_sent"],
		["Cancelled", "eval:self.docstatus==2"],
		["Open", "communication_received"],
	],
	"Quotation": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Lost", "eval:self.status=='Lost'"],
		["Ordered", "has_sales_order"],
		["Replied", "communication_sent"],
		["Cancelled", "eval:self.docstatus==2"],
		["Open", "communication_received"],
	],
	"Sales Order": [
		["Draft", None],
		["Submitted", "eval:self.docstatus==1"],
		["Stopped", "eval:self.status=='Stopped'"],
		["Cancelled", "eval:self.docstatus==2"],
	],
	"Support Ticket": [
		["Replied", "communication_sent"],
		["Open", "communication_received"]
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

	def set_status(self, update=False):
		if self.is_new():
			return

		if self.doctype in status_map:
			_status = self.status
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

			if self.status != _status:
				self.add_comment("Label", self.status)

			if update:
				frappe.db.set_value(self.doctype, self.name, "status", self.status)

	def on_communication(self):
		if not self.get("communications"): return
		self.communication_set = True
		self.get("communications").sort(key=lambda d: d.creation)
		self.set_status(update=True)
		del self.communication_set

	def communication_received(self):
		if getattr(self, "communication_set", False):
			last_comm = self.get("communications")
			if last_comm:
				return last_comm[-1].sent_or_received == "Received"

	def communication_sent(self):
		if getattr(self, "communication_set", False):
			last_comm = self.get("communications")
			if last_comm:
				return last_comm[-1].sent_or_received == "Sent"

	def validate_qty(self):
		"""
			Validates qty at row level
		"""
		self.tolerance = {}
		self.global_tolerance = None

		for args in self.status_updater:
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
		"""
			Updates qty at row level
		"""
		for args in self.status_updater:
			# condition to include current record (if submit or no if cancel)
			if self.docstatus == 1:
				args['cond'] = ' or parent="%s"' % self.name.replace('"', '\"')
			else:
				args['cond'] = ' and parent!="%s"' % self.name.replace('"', '\"')

			args['modified_cond'] = ''
			if change_modified:
				args['modified_cond'] = ', modified = now()'

			# update quantities in child table
			for d in self.get_all_children():
				if d.doctype == args['source_dt']:
					# updates qty in the child table
					args['detail_id'] = d.get(args['join_field'])

					args['second_source_condition'] = ""
					if args.get('second_source_dt') and args.get('second_source_field') \
							and args.get('second_join_field'):
						args['second_source_condition'] = """ + ifnull((select sum(%(second_source_field)s)
							from `tab%(second_source_dt)s`
							where `%(second_join_field)s`="%(detail_id)s"
							and (docstatus=1)), 0)""" % args

					if args['detail_id']:
						frappe.db.sql("""update `tab%(target_dt)s`
							set %(target_field)s = (select sum(%(source_field)s)
								from `tab%(source_dt)s` where `%(join_field)s`="%(detail_id)s"
								and (docstatus=1 %(cond)s)) %(second_source_condition)s
							where name='%(detail_id)s'""" % args)

			# get unique transactions to update
			for name in set([d.get(args['percent_join_field']) for d in self.get_all_children(args['source_dt'])]):
				if name:
					args['name'] = name

					# update percent complete in the parent table
					frappe.db.sql("""update `tab%(target_parent_dt)s`
						set %(target_parent_field)s = (select sum(if(%(target_ref_field)s >
							ifnull(%(target_field)s, 0), %(target_field)s,
							%(target_ref_field)s))/sum(%(target_ref_field)s)*100
							from `tab%(target_dt)s` where parent="%(name)s") %(modified_cond)s
						where name='%(name)s'""" % args)

					# update field
					if args.get('status_field'):
						frappe.db.sql("""update `tab%(target_parent_dt)s`
							set %(status_field)s = if(ifnull(%(target_parent_field)s,0)<0.001,
								'Not %(keyword)s', if(%(target_parent_field)s>=99.99,
								'Fully %(keyword)s', 'Partly %(keyword)s'))
							where name='%(name)s'""" % args)


	def update_billing_status_for_zero_amount_refdoc(self, ref_dt):
		ref_fieldname = ref_dt.lower().replace(" ", "_")
		zero_amount_refdoc = []
		all_zero_amount_refdoc = frappe.db.sql_list("""select name from `tab%s`
			where docstatus=1 and net_total = 0""" % ref_dt)

		for item in self.get("entries"):
			if item.get(ref_fieldname) \
				and item.get(ref_fieldname) in all_zero_amount_refdoc \
				and item.get(ref_fieldname) not in zero_amount_refdoc:
					zero_amount_refdoc.append(item.get(ref_fieldname))

		if zero_amount_refdoc:
			self.update_biling_status(zero_amount_refdoc, ref_dt, ref_fieldname)

	def update_biling_status(self, zero_amount_refdoc, ref_dt, ref_fieldname):
		for ref_dn in zero_amount_refdoc:
			ref_doc_qty = flt(frappe.db.sql("""select sum(ifnull(qty, 0)) from `tab%s Item`
				where parent=%s""" % (ref_dt, '%s'), (ref_dn))[0][0])

			billed_qty = flt(frappe.db.sql("""select sum(ifnull(qty, 0))
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
