# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, cstr
from webnotes import msgprint

from webnotes.model.controller import DocListController

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
		["Submitted", "eval:self.doc.docstatus==1"],
		["Lost", "eval:self.doc.status=='Lost'"],
		["Quotation", "has_quotation"],
		["Replied", "communication_sent"],
		["Cancelled", "eval:self.doc.docstatus==2"],
		["Open", "communication_received"],
	],
	"Quotation": [
		["Draft", None],
		["Submitted", "eval:self.doc.docstatus==1"],
		["Lost", "eval:self.doc.status=='Lost'"],
		["Ordered", "has_sales_order"],
		["Replied", "communication_sent"],
		["Cancelled", "eval:self.doc.docstatus==2"],
		["Open", "communication_received"],
	],
	"Sales Order": [
		["Draft", None],
		["Submitted", "eval:self.doc.docstatus==1"],
		["Stopped", "eval:self.doc.status=='Stopped'"],
		["Cancelled", "eval:self.doc.docstatus==2"],
	],
	"Support Ticket": [
		["Replied", "communication_sent"],
		["Open", "communication_received"]
	],
}

class StatusUpdater(DocListController):
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
		if self.doc.get("__islocal"):
			return
			
		if self.doc.doctype in status_map:
			sl = status_map[self.doc.doctype][:]
			sl.reverse()
			for s in sl:
				if not s[1]:
					self.doc.status = s[0]
					break
				elif s[1].startswith("eval:"):
					if eval(s[1][5:]):
						self.doc.status = s[0]
						break
				elif getattr(self, s[1])():
					self.doc.status = s[0]
					break
		
			if update:
				webnotes.conn.set_value(self.doc.doctype, self.doc.name, "status", self.doc.status)
	
	def on_communication(self):
		self.communication_set = True
		self.set_status(update=True)
		del self.communication_set
	
	def communication_received(self):
		if getattr(self, "communication_set", False):
			last_comm = self.doclist.get({"doctype":"Communication"})
			if last_comm:
				return last_comm[-1].sent_or_received == "Received"

	def communication_sent(self):
		if getattr(self, "communication_set", False):
			last_comm = self.doclist.get({"doctype":"Communication"})
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
			for d in self.doclist:
				if d.doctype == args['source_dt'] and d.fields.get(args["join_field"]):
					args['name'] = d.fields[args['join_field']]

					# get all qty where qty > target_field
					item = webnotes.conn.sql("""select item_code, `%(target_ref_field)s`, 
						`%(target_field)s`, parenttype, parent from `tab%(target_dt)s` 
						where `%(target_ref_field)s` < `%(target_field)s` 
						and name="%(name)s" and docstatus=1""" % args, as_dict=1)
					if item:
						item = item[0]
						item['idx'] = d.idx
						item['target_ref_field'] = args['target_ref_field'].replace('_', ' ')

						if not item[args['target_ref_field']]:
							msgprint("""As %(target_ref_field)s for item: %(item_code)s in \
							%(parenttype)s: %(parent)s is zero, system will not check \
							over-delivery or over-billed""" % item)
						elif args.get('no_tolerance'):
							item['reduce_by'] = item[args['target_field']] - \
								item[args['target_ref_field']]
							if item['reduce_by'] > .01:
								msgprint("""
									Row #%(idx)s: Max %(target_ref_field)s allowed for <b>Item \
									%(item_code)s</b> against <b>%(parenttype)s %(parent)s</b> \
									is <b>""" % item + cstr(item[args['target_ref_field']]) +
									 """</b>.<br>You must reduce the %(target_ref_field)s by \
									%(reduce_by)s""" % item, raise_exception=1)
					
						else:
							self.check_overflow_with_tolerance(item, args)
						
	def check_overflow_with_tolerance(self, item, args):
		"""
			Checks if there is overflow condering a relaxation tolerance
		"""
	
		# check if overflow is within tolerance
		tolerance = self.get_tolerance_for(item['item_code'])
		overflow_percent = ((item[args['target_field']] - item[args['target_ref_field']]) / 
		 	item[args['target_ref_field']]) * 100
	
		if overflow_percent - tolerance > 0.01:
			item['max_allowed'] = flt(item[args['target_ref_field']] * (100+tolerance)/100)
			item['reduce_by'] = item[args['target_field']] - item['max_allowed']
		
			msgprint("""
				Row #%(idx)s: Max %(target_ref_field)s allowed for <b>Item %(item_code)s</b> \
				against <b>%(parenttype)s %(parent)s</b> is <b>%(max_allowed)s</b>. 
				
				If you want to increase your overflow tolerance, please increase tolerance %% in \
				Global Defaults or Item master. 
				
				Or, you must reduce the %(target_ref_field)s by %(reduce_by)s
				
				Also, please check if the order item has already been billed in the Sales Order""" % 
				item, raise_exception=1)
				
	def get_tolerance_for(self, item_code):
		"""
			Returns the tolerance for the item, if not set, returns global tolerance
		"""
		if self.tolerance.get(item_code): return self.tolerance[item_code]
		
		tolerance = flt(webnotes.conn.get_value('Item',item_code,'tolerance') or 0)

		if not tolerance:
			if self.global_tolerance == None:
				self.global_tolerance = flt(webnotes.conn.get_value('Global Defaults', None, 
					'tolerance'))
			tolerance = self.global_tolerance
		
		self.tolerance[item_code] = tolerance
		return tolerance
	

	def update_qty(self, change_modified=True):
		"""
			Updates qty at row level
		"""
		for args in self.status_updater:
			# condition to include current record (if submit or no if cancel)
			if self.doc.docstatus == 1:
				args['cond'] = ' or parent="%s"' % self.doc.name
			else:
				args['cond'] = ' and parent!="%s"' % self.doc.name
			
			args['modified_cond'] = ''
			if change_modified:
				args['modified_cond'] = ', modified = now()'
		
			# update quantities in child table
			for d in self.doclist:
				if d.doctype == args['source_dt']:
					# updates qty in the child table
					args['detail_id'] = d.fields.get(args['join_field'])
					
					args['second_source_condition'] = ""
					if args.get('second_source_dt') and args.get('second_source_field') \
							and args.get('second_join_field'):
						args['second_source_condition'] = """ + (select sum(%(second_source_field)s) 
							from `tab%(second_source_dt)s` 
							where `%(second_join_field)s`="%(detail_id)s" 
							and (docstatus=1))""" % args
			
					if args['detail_id']:
						webnotes.conn.sql("""update `tab%(target_dt)s` 
							set %(target_field)s = (select sum(%(source_field)s) 
								from `tab%(source_dt)s` where `%(join_field)s`="%(detail_id)s" 
								and (docstatus=1 %(cond)s)) %(second_source_condition)s
							where name='%(detail_id)s'""" % args)
		
			# get unique transactions to update
			for name in set([d.fields.get(args['percent_join_field']) for d in self.doclist 
					if d.doctype == args['source_dt']]):
				if name:
					args['name'] = name
				
					# update percent complete in the parent table
					webnotes.conn.sql("""update `tab%(target_parent_dt)s` 
						set %(target_parent_field)s = (select sum(if(%(target_ref_field)s > 
							ifnull(%(target_field)s, 0), %(target_field)s, 
							%(target_ref_field)s))/sum(%(target_ref_field)s)*100 
							from `tab%(target_dt)s` where parent="%(name)s") %(modified_cond)s
						where name='%(name)s'""" % args)

					# update field
					if args.get('status_field'):
						webnotes.conn.sql("""update `tab%(target_parent_dt)s` 
							set %(status_field)s = if(ifnull(%(target_parent_field)s,0)<0.001, 
								'Not %(keyword)s', if(%(target_parent_field)s>=99.99, 
								'Fully %(keyword)s', 'Partly %(keyword)s'))
							where name='%(name)s'""" % args)