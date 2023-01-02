# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _, qb, throw, bold
from frappe.utils import flt, cint, cstr,getdate, nowtime
from erpnext.custom_utils import check_future_date
from erpnext.production.doctype.cop_rate.cop_rate import get_cop_rate
from erpnext.controllers.stock_controller import StockController

class Production(StockController):
	def __init__(self, *args, **kwargs):
		super(Production, self).__init__(*args, **kwargs)
	def validate(self):
		check_future_date(self.posting_date)
		self.check_cop()
		self.validate_data()
		self.validate_items()
		self.validate_transportation()
		self.validate_raw_material_product_qty()
		if self.coal_raising_type:
			self.validate_coal_raising()

	def before_submit(self):
		self.assign_default_dummy()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()
		self.make_production_entry()
		self.make_auto_production()

	def on_cancel(self):
		self.assign_default_dummy()
		self.delete_production_entry()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
	
	def make_auto_production(self):
		if self.docstatus == 1:
			sort_prod_wise = frappe._dict()
			for item in self.items:
				data = frappe.db.sql('''
							select parent from `tabAuto Production Setting Item` where item_code = '{}'
						'''.format(item.item_code))
				if data:
					sort_prod_wise.setdefault(data[0][0], []).append(item)
			if sort_prod_wise:
				prod = frappe.new_doc("Production")
				prod.branch = self.branch
				prod.cost_center = self.cost_center
				prod.posting_date = self.posting_date
				prod.entry_date = self.entry_date
				prod.posting_time = nowtime()
				prod.cop_list = self.cop_list
				prod.warehouse = self.warehouse if cint(self.transfer) == 0 else self.to_warehouse
				prod.production_type = self.production_type
				prod.company = self.company
				prod.currency = self.currency
				prod.check_raw_material_product_qty = 0
				prod.reference = self.name
				prod.set("raw_materials",[])
				prod.set("items",[])
				for key, item in sort_prod_wise.items():
					total_qty = 0
					for d in item:
						total_qty += flt(d.qty)
						prod.append("raw_materials",{
							"item_code":d.item_code,
							"qty":d.qty,
							"uom":d.uom,
							"item_name":d.item_name,
							"item_type":d.item_type
						})

					item_name, item_group, uom = frappe.db.get_value("Item",key, ["item_name","item_group","stock_uom"])
					prod.append("items",{
						"item_code":key,
						"item_name":item_name,
						"item_group":item_group,
						"uom":uom,
						"cost_center":self.cost_center,
						"cop":get_cop_rate(key, self.posting_date, self.cop_list, uom)[0].rate,
						"qty":total_qty,
						"expense_account":get_expense_account(self.company, key),
						"warehouse":self.warehouse if cint(self.transfer) == 0 else self.to_warehouse
					})
			
				prod.insert()
				prod.submit()

	def update_stock_ledger(self):
		sl_entries = []
		# make sl entries for source warehouse first, then do the target warehouse
		for d in self.get('raw_materials'):
			if cstr(d.warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.warehouse),
					"actual_qty": -1 * flt(d.qty),
					"incoming_rate": 0
				}))

		for d in self.get('items'):
			if cstr(d.warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.warehouse),
					"actual_qty": flt(d.qty),
					"incoming_rate": flt(d.cop, 2)
				}))

		if self.transfer:
			if not self.to_warehouse:
				frappe.throw("Receiving warehouse is mandatory while transferring item")

			for d in self.get('items'):
				if cstr(d.warehouse):
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": cstr(d.warehouse),
						"actual_qty": -1 * flt(d.qty),
						"incoming_rate": 0
					}))

				if cstr(self.to_warehouse):
					sl_entries.append(self.get_sl_entries(d, {
						"warehouse": cstr(self.to_warehouse),
						"actual_qty": flt(d.qty),
						"incoming_rate": flt(d.cop, 2)
					}))
	
		if self.docstatus == 2:
				sl_entries.reverse()
		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')
	def get_gl_entries(self, warehouse_account):
			gl_entries = super(Production, self).get_gl_entries(
				warehouse_account)
			return gl_entries
	""" ++++++++++ Ver 1.0.190401 Ends ++++++++++++ """

	def assign_default_dummy(self):
		self.pol_type = None
		self.stock_uom = None

	def make_products_sl_entry(self):
		sl_entries = []
		for a in self.items:
			sl_entries.append(prepare_sl(self,
				{
					"stock_uom": a.uom,
					"item_code": a.item_code,
					"actual_qty": a.qty,
					"warehouse": self.warehouse,
					"incoming_rate": flt(a.cop, 2)
				}))

		if sl_entries:
			if self.docstatus == 2:
				sl_entries.reverse()
			self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')


	def assign_default_dummy(self):
		self.pol_type = None
		self.stock_uom = None
	def check_cop(self):
		for a in self.items:
			if flt(a.cop) <= 0:
				a.cop = get_cop_rate(a.item_code, self.posting_date, self.cop_list, a.uom)[0].rate		
			if flt(a.cop) <= 0:
				frappe.throw("COP Cannot be zero or less")
	def validate_data(self):
		if self.production_type == "Adhoc" and not self.adhoc_production:
			frappe.throw("Select Adhoc Production to Proceed")
		if self.production_type == "Planned":
			self.adhoc_production = None
		if self.work_type == "Private" and not self.supplier:
			frappe.throw("Contractor is Mandatory if work type is private")

	def validate_transportation(self):
		tr = qb.DocType("Transporter Rate")
		tdr = qb.DocType("Transporter Distance Rate")
		for d in self.items:
			if not d.transporter_payment_eligible:
				d.rate = 0
				d.transportation_expense_account = ''
				d.transporter_rate = ''
				d.amount = 0
			else:
				if not self.transporter_rate_base_on:
					frappe.throw("Please select transporter rate based on Location or Warehouse")

				if not d.equipment:
					frappe.throw("Please Select Equipment or Vehicle for transportation")

				if self.transporter_rate_base_on == "Location":
					rate = 0
					expense_account = 0
					qty = 0
					if not self.location:
						frappe.throw("Please Select Location")
						# self.distance = frappe.db.get_value("Location", self.location, "distance")

					if self.location:
						for a in (qb.from_(tr)
									.inner_join(tdr)
									.on(tr.name == tdr.parent)
									.select(tr.name,tdr.rate,tr.expense_account,tdr.distance)
									.where(	(tr.disabled == 0) 
											& (tdr.location == self.location)
											& (tr.from_warehouse == self.warehouse)
											& (self.posting_date >= tr.from_date)
											& (self.posting_date <= tr.to_date))
									).run(as_dict=1):
							rate = a.rate
							expense_account = a.expense_account
							transporter_rate = a.name

					if flt(rate) > 0:
						d.rate = rate
						d.transportation_expense_account = expense_account
						d.transporter_rate = transporter_rate
						if d.qty > 0:
							d.amount = flt(d.rate) * flt(d.qty)
						else:
							frappe.throw("Please provide the Quantity")			
					else:
						frappe.throw("Define Transporter Rate for location {} in Transporter Rate ".format(self.location))

	def validate_raw_material_product_qty(self):
		raw_material_qty = 0.0
		product_item_qty = 0.0
		for a in self.raw_materials:
			raw_material_qty += flt(a.qty)

		for b in self.items:
			product_item_qty += flt(b.qty)

		for c in self.production_waste:
			product_item_qty += flt(c.qty)

		self.raw_material_qty = raw_material_qty
		self.product_qty = product_item_qty
		
		if self.check_raw_material_product_qty:
			if round(self.product_qty,4) > round(self.raw_material_qty,4):
				frappe.throw("Sum of Crushed products should be less than or equivalent to raw materials feed.")

	def validate_items(self):
		prod_items = self.get_production_items()
		# validate raw material
		for item in self.get("raw_materials"):
			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))

			if not item.cost_center:
				item.cost_center = self.cost_center
			if not item.warehouse:
				item.warehouse = self.warehouse
			if not item.expense_account:
				item.expense_account = get_expense_account(	self.company, item.item_code)

		for item in self.get("items"):
			item.production_type = self.production_type
			item.item_name, item.item_group = frappe.db.get_value("Item", item.item_code, ["item_name", "item_group"])

			if item.item_code not in prod_items:
				frappe.throw(_("{0} is not a Production Item").format(item.item_code))
			if flt(item.qty) <= 0:
				frappe.throw(_("Quantity for <b>{0}</b> cannot be zero or less").format(item.item_code))
			if flt(item.cop) <= 0:
				frappe.throw(_("COP for <b>{0}</b> cannot be zero or less").format(item.item_code))

			if self.production_type == "Planned":
				continue
			if item.item_sub_group == "Pole" and flt(item.qty_in_no) <= 0:
				frappe.throw("Number of Poles is required for Adhoc Loggings")
				
			if item.item_sub_group:
				reading_required, par, min_val, max_val = frappe.db.get_value("Item Sub Group", item.item_sub_group, [
															"reading_required", "reading_parameter", "minimum_value", "maximum_value"])
				if reading_required:
					if not flt(min_val) <= flt(item.reading) <= flt(max_val):
						frappe.throw("<b>{0}</b> reading should be between {1} and {2} for {3} for Adhoc Production".format(
							par, frappe.bold(min_val), frappe.bold(max_val), frappe.bold(item.item_code)))
			else:
				item.reading = 0

			in_inches = 0
			f = str(item.reading).split(".")
			in_inches = cint(f[0]) * 12
			if len(f) > 1:
				if cint(f[1]) > 11:
					frappe.throw("Inches should be smaller than 12 on row {0}".format(item.idx))
				in_inches += cint(f[1])
			item.reading_inches = in_inches

			if not item.cost_center:
				item.cost_center = self.cost_center
			if not item.warehouse:
				item.warehouse = self.warehouse
			if not item.expense_account:
				item.expense_account = get_expense_account(	self.company, item.item_code)

	def get_production_items(self):
		prod_items = []
		pro_codes = list(set(item.item_code for item in self.get("items")))
		raw_codes = list(set(item.item_code for item in self.get("raw_materials")))
		item_codes = list(set(pro_codes + raw_codes))

		if item_codes:
				prod_items = [r[0] for r in frappe.db.sql("""select name
						from `tabItem` where name in (%s) and is_production_item=1""" % \
						(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return prod_items

	def validate_coal_raising(self):
		self.validate_master_data()
		is_exist = False
		for item in self.items:
			if frappe.db.exists({'doctype': 'Coal Raising Master Item','item': item.item_code}):
				is_exist = True
				if not self.coal_raising_type:
					frappe.throw("Coal Rasing Type is Required")
		if not is_exist and self.coal_raising_type :
			frappe.throw("Coal Rasing Type is Not Required for above item")

		if self.coal_raising_type in ('Manual','Machine Sharing'):
			if not self.mineral_raising_group:
				frappe.throw("Mineral Raising Group is Required")
			if not self.no_of_labours:
				frappe.throw("No. of Labours is Required")
			
			if getdate(self.posting_date) > getdate(self.contract_end_date):
				frappe.throw(str("Mineral Raising Group <b>{}</b> is not applicable as its contract date ended on <b>{}</b>".format(self.mineral_raising_group,self.contract_end_date)))
		
		if self.coal_raising_type == 'Manual':
			self.oms = flt(flt(self.product_qty) / flt(self.no_of_labours),2)
			self.manual_calculation()
			self.machine_hours = 0
		elif self.coal_raising_type == 'Machine Sharing':
			self.machine_sharing_calculation()
			self.penalty_amount = 0
		elif self.coal_raising_type == 'SMCL Machine':
			self.mineral_raising_group = None
			self.no_of_labours = 0 
			self.machine_hours = 0
			self.tier = None
			self.oms = 0
			self.amount = 0
			self.penalty_amount = 0
			self.machine_payable = 0
			self.grand_amount = 0
	def validate_master_data(self):
		coal_raising_master = frappe.db.get_value("Coal Raising Branch",{"branch":self.branch},"parent")
		if not coal_raising_master:
			throw("Coal Raising Master not found for branch {}".format(bold(self.branch)))
		if not frappe.db.exists('Coal Raising Master',{'name':coal_raising_master,'from_date':('<=',self.posting_date),'to_date':('>=',self.posting_date)}):
			frappe.throw('Coal Raising Master is not valid for branch <b>{}</b>'.format(self.branch))

	def machine_sharing_calculation(self):
		coal_raising_master = frappe.db.get_value("Coal Raising Branch",{"branch":self.branch},"parent")
		amount, qty_payable = 0,0
		rate1, rate_per_mt_tire2, working_hr = frappe.db.get_value('Coal Raising Master',coal_raising_master ,['oms1_tier1','rate_per_mt_tier2','working_hr'])
		
		oms_previous_month = frappe.db.sql("""
			SELECT avg(oms) 
			FROM `tabProduction` 
			WHERE oms > 0 
			AND posting_date between 
				(SELECT DATE_FORMAT(LAST_DAY(DATE_ADD('{0}', INTERVAL -1 MONTH)),'%Y-%m-01') PREV_MONTH_START_DATE) 
			AND 
				(SELECT LAST_DAY(DATE_ADD('{0}', INTERVAL -1 MONTH)) PREV_MONTH_END_DATE) 
			AND coal_raising_type = 'Manual'
			AND docstatus = 1
			AND mineral_raising_group = '{1}'
			AND tier = '{2}'
		""".format(self.posting_date,self.mineral_raising_group,self.tier))[0][0]
		# assign default oms if previous month oms is null or 0
		if not oms_previous_month:
			oms_previous_month = frappe.db.get_value('Mineral Raising Group',self.mineral_raising_group,['default_oms'])
		
		if self.labor_type == 'Bhutanese':
			qty_payable = flt(self.no_of_labours) * flt(self.machine_hours) * (flt(oms_previous_month)/flt(working_hr))
			amount = flt(rate1) * flt(qty_payable)
		elif self.labor_type == 'Indian':
			amount =flt(rate_per_mt_tire2) * flt(self.no_of_labours) * flt(self.machine_hours) * (flt(oms_previous_month)/flt(working_hr))

		self.amount, self.machine_payable, self.grand_amount, self.penalty_amount = amount, qty_payable, amount, 0
		self.oms = oms_previous_month

	def manual_calculation(self):
		grand_total = 0
		coal_raising_master = frappe.db.get_value("Coal Raising Branch",{"branch":self.branch},"parent")
		if not coal_raising_master:
			throw("Coal Raising Master Not Found for branch {}".format(bold(self.branch)))
		rate1, rate2, rate_per_mt_tire2 = frappe.db.get_value('Coal Raising Master',coal_raising_master,['oms1_tier1','oms2_tier1','rate_per_mt_tier2'])
		total = 0
		penalty = 0

		if self.labor_type == 'Bhutanese':
			if flt(self.oms) > 2:
				oms1 = 2
				oms2 = flt(flt(self.oms) - flt(oms1), 2)
				amount1 = flt(flt(self.no_of_labours) * flt(rate1) * flt(oms1), 2)
				amount2 = flt(flt(self.no_of_labours) * flt(rate2) * flt(oms2), 2)
				total = flt(flt(amount1) + flt(amount2), 2)
			else:
				total = flt(self.no_of_labours) * flt(rate1) * flt(self.oms)

			# calculate penalty
			if flt(self.no_of_labours) < flt(self.minimum_labor) and flt(self.eligible_for_penalty) == 1:
				p_oms = self.get_previous_day_oms()
				penalty = flt((flt(self.minimum_labor) - flt(self.no_of_labours)) * flt(p_oms) * flt(rate1),2)
				grand_total = flt(flt(total) - flt(penalty),2)
			else:
				grand_total = total
		
		elif self.labor_type == 'Indian':
			total = flt(rate_per_mt_tire2) * flt(self.product_qty)
			if flt(self.no_of_labours) < flt(self.minimum_labor) and flt(self.eligible_for_penalty) == 1:
				p_oms 	= self.get_previous_day_oms()
				penalty = flt((flt(self.minimum_labor) - flt(self.no_of_labours)) * flt(p_oms) * flt(rate_per_mt_tire2),2)
			grand_total = flt(total) - flt(penalty)
		self.penalty_amount = penalty
		self.grand_amount 	= total
		self.amount 		= grand_total

	def get_previous_day_oms(self):
		pro = qb.DocType("Production")
		oms = (qb.from_(pro)
				.select(pro.oms)
				.where((pro.docstatus == 1)
					& (pro.mineral_raising_group == self.mineral_raising_group)
					& (pro.tier == self.tier)
					& (pro.coal_raising_type == self.coal_raising_type)
					& (pro.posting_date < self.posting_date)
					& (pro.oms != 0)
					)
				.orderby(pro.posting_date,order=qb.desc)
				.orderby(pro.posting_time,order=qb.desc)
				.limit(1)
				).run()
		if oms:
			return oms[0][0]
		else:
			return frappe.db.get_value('Mineral Raising Group',self.mineral_raising_group,['default_oms'])
	def make_production_entry(self):
		for a in self.items:
			doc = frappe.new_doc("Production Entry")
			doc.flags.ignore_permissions = 1
			doc.item_code = a.item_code
			doc.item_name = a.item_name
			doc.item_group = a.item_group
			doc.qty = a.qty
			doc.uom = a.uom
			doc.cop = a.cop
			doc.transportation_rate = a.rate
			doc.transportation_amount = a.amount
			doc.company = self.company
			doc.currency = self.currency
			doc.branch = self.branch	
			doc.location = self.location
			doc.cost_center = self.cost_center
			doc.warehouse = self.warehouse
			doc.posting_date = str(self.posting_date) + " " + str(self.posting_time)
			doc.ref_doc = self.name
			doc.production_type = self.production_type
			doc.adhoc_production = self.adhoc_production
			doc.equipment_model = a.equipment_model
			doc.transporter_type = frappe.db.get_value("Equipment", a.equipment, "equipment_category")
			doc.unloading_by = a.unloading_by
			doc.transfer_to_warehouse = self.to_warehouse if self.transfer else ''
			doc.mineral_raising_group = self.mineral_raising_group
			doc.coal_raising_type = self.coal_raising_type
			doc.submit()

	def delete_production_entry(self):
		frappe.db.sql("delete from `tabProduction Entry` where ref_doc = %s", self.name)

	@frappe.whitelist()
	def get_finish_product(self):
		data = []
		if not self.branch and not self.posting_date:
			frappe.throw("Select branch and posting date to get the products after productions")

		if not self.raw_materials:
			frappe.throw("Please enter a raw material to get the Product")
		else:
			condition = ""
			for a in self.raw_materials:
				raw_material_item = a.item_code
				raw_material_qty = a.qty
				raw_material_unit = a.uom
				item_group = frappe.db.get_value("Item", a.item_code, "item_group")				
				cost_center = a.cost_center
				warehouse = a.warehouse
				expense_account = a.expense_account
				item_type = a.item_type
				if a.item_type:
					condition += " and item_type = '" + str(a.item_type) + "'"
				if a.warehouse:
					condition += " and warehouse = '" + str(a.warehouse) + "'"
		
		if raw_material_item:
			count = 0
			production_seting_code = ""
			for a in frappe.db.sql("""select name 
							from `tabProduction Settings`
							where branch = '{0}' and disabled = 0
							and raw_material = '{1}'
							{3}
							and '{2}' between from_date and ifnull(to_date,now())		
				""".format(self.branch, raw_material_item, self.posting_date, condition), as_dict=True):
				count += 1
				production_seting_code = a.name
			
			if count > 1:
				frappe.throw("There are more than 1 production setting for this production parameters")

			if production_seting_code:
				for a in frappe.db.sql("""
						select parameter_type, ratio, item_code, item_name, item_type
						from `tabProduction Settings Item` 
						where parent = '{0}'				
					""".format(production_seting_code), as_dict=True):
					cop = ""
					if a.parameter_type == "Item":
						cop = get_cop_rate(a.item_code, self.posting_date, self.cop_list)[0].rate
					product_qty = 0.00
					
					if flt(a.ratio) > 0:
						product_qty = (flt(a.ratio) * flt(raw_material_qty))/100
					data.append({
								"parameter_type": a.parameter_type,
								"item_code":a.item_code, 
								"item_name":a.item_name,
								"item_type":a.item_type, 
								"qty": product_qty,
								"uom": raw_material_unit,
								"cop": cop,
								"cost_center": cost_center,
								"warehouse": warehouse,
								"expense_account": expense_account,
								"ratio": flt(a.ratio)
								})
		if data:			
			return data
		else:
			frappe.msgprint("No records in production settings")
	@frappe.whitelist()
	def get_raw_material(self):
		data = []
		if not self.branch and not self.posting_date:
			frappe.throw("Select branch and posting date to get the raw materials")

		if not self.items:
			frappe.throw("Please enter a product to get the raw material")
		else:
			condition = ""
			for a in self.items:
				product_item = a.item_code
				product_qty = a.qty
				product_unit = a.uom				
				cost_center = a.cost_center
				warehouse = a.warehouse
				expense_account = a.expense_account
				item_type = a.item_type
				if a.item_type:
					condition += " and item_type = '" + str(a.item_type) + "'"
				# if a.warehouse:
				# 	condition += " and warehouse = '" + str(a.warehouse) + "'"
		
		if product_item:
			count = 0
			production_seting_code = ""
			for a in frappe.db.sql("""select name 
							from `tabProduction Settings`
							where branch = '{0}' and disabled =0
							and product = '{1}'
							{3}
							and '{2}' between from_date and ifnull(to_date,now())		
				""".format(self.branch, product_item, self.posting_date, condition), as_dict=True):
				count += 1
				production_seting_code = a.name
			
			if count > 1:
				frappe.throw("There are more than 1 production setting for this production parameters")

			if production_seting_code:
				for a in frappe.db.sql("""
						select parameter_type, ratio, item_code, item_name, item_type
						from `tabProduction Settings Item` 
						where parent = '{0}'				
				""".format(production_seting_code), as_dict=True):
					raw_material_qty = 0.00
					if flt(a.ratio) > 0:
						raw_material_qty = (flt(a.ratio) * flt(product_qty))/100
					data.append({
								"parameter_type": a.parameter_type,
								"item_code":a.item_code, 
								"item_name":a.item_name, 
								"item_type":a.item_type,
								"qty": raw_material_qty,
								"uom": product_unit,
								"cost_center": cost_center,
								"warehouse": warehouse,
								"expense_account": expense_account,
								})
		if data:			
			return data
		else:
			frappe.msgprint("No records in production settings")

@frappe.whitelist()
def get_expense_account(company, item):
	expense_account = frappe.db.get_value("Company", company, "default_production_account")
	if not expense_account:
		expense_account = frappe.db.get_value("Item Default", item, "expense_account")
	return expense_account
@frappe.whitelist()
def check_item_applicable_for_coal_raising(item=None):
# added by Birendra for coal raising purpose on 20/05/2021
	return frappe.db.exists({
		'doctype': 'Coal Raising Master Item',
		'item': item
		})