# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, cstr, nowdate, add_days, cint
from erpnext.accounts.utils import get_fiscal_year, FiscalYearError

def reorder_item():
	""" Reorder item if stock reaches reorder level"""
	# if initial setup not completed, return
	if not frappe.db.sql("select name from `tabFiscal Year` limit 1"):
		return

	if getattr(frappe.local, "auto_indent", None) is None:
		frappe.local.auto_indent = cint(frappe.db.get_value('Stock Settings', None, 'auto_indent'))

	if frappe.local.auto_indent:
		return _reorder_item()

def _reorder_item():
	material_requests = {"Purchase": {}, "Transfer": {}}

	item_warehouse_projected_qty = get_item_warehouse_projected_qty()

	warehouse_company = frappe._dict(frappe.db.sql("""select name, company from `tabWarehouse`"""))
	default_company = (frappe.defaults.get_defaults().get("company") or
		frappe.db.sql("""select name from tabCompany limit 1""")[0][0])

	def add_to_material_request(item_code, warehouse, reorder_level, reorder_qty, material_request_type):
		if warehouse not in item_warehouse_projected_qty[item_code]:
			# likely a disabled warehouse or a warehouse where BIN does not exist
			return

		reorder_level = flt(reorder_level)
		reorder_qty = flt(reorder_qty)
		projected_qty = item_warehouse_projected_qty[item_code][warehouse]

		if reorder_level and projected_qty < reorder_level:
			deficiency = reorder_level - projected_qty
			if deficiency > reorder_qty:
				reorder_qty = deficiency

			company = warehouse_company.get(warehouse) or default_company

			material_requests[material_request_type].setdefault(company, []).append({
				"item_code": item_code,
				"warehouse": warehouse,
				"reorder_qty": reorder_qty
			})

	for item_code in item_warehouse_projected_qty:
		item = frappe.get_doc("Item", item_code)

		if item.variant_of and not item.get("reorder_levels"):
			item.update_template_tables()

		if item.get("reorder_levels"):
			for d in item.get("reorder_levels"):
				add_to_material_request(item_code, d.warehouse, d.warehouse_reorder_level,
					d.warehouse_reorder_qty, d.material_request_type)

		else:
			# raise for default warehouse
			add_to_material_request(item_code, item.default_warehouse, item.re_order_level, item.re_order_qty, "Purchase")

	if material_requests:
		return create_material_request(material_requests)

def get_item_warehouse_projected_qty():
	item_warehouse_projected_qty = {}

	for item_code, warehouse, projected_qty in frappe.db.sql("""select item_code, warehouse, projected_qty
		from tabBin where ifnull(item_code, '') != '' and ifnull(warehouse, '') != ''
		and exists (select name from `tabItem`
			where `tabItem`.name = `tabBin`.item_code and
			is_stock_item='Yes' and (is_purchase_item='Yes' or is_sub_contracted_item='Yes') and
			(ifnull(end_of_life, '0000-00-00')='0000-00-00' or end_of_life > %s))
		and exists (select name from `tabWarehouse`
			where `tabWarehouse`.name = `tabBin`.warehouse
			and ifnull(disabled, 0)=0)""", nowdate()):

		item_warehouse_projected_qty.setdefault(item_code, {})[warehouse] = flt(projected_qty)

	return item_warehouse_projected_qty

def create_material_request(material_requests):
	"""	Create indent on reaching reorder level	"""
	mr_list = []
	defaults = frappe.defaults.get_defaults()
	exceptions_list = []

	def _log_exception():
		if frappe.local.message_log:
			exceptions_list.extend(frappe.local.message_log)
			frappe.local.message_log = []
		else:
			exceptions_list.append(frappe.get_traceback())

	try:
		current_fiscal_year = get_fiscal_year(nowdate())[0] or defaults.fiscal_year

	except FiscalYearError:
		_log_exception()
		notify_errors(exceptions_list)
		return

	for request_type in material_requests:
		for company in material_requests[request_type]:
			try:
				items = material_requests[request_type][company]
				if not items:
					continue

				mr = frappe.new_doc("Material Request")
				mr.update({
					"company": company,
					"fiscal_year": current_fiscal_year,
					"transaction_date": nowdate(),
					"material_request_type": request_type
				})

				for d in items:
					d = frappe._dict(d)
					item = frappe.get_doc("Item", d.item_code)
					mr.append("items", {
						"doctype": "Material Request Item",
						"item_code": d.item_code,
						"schedule_date": add_days(nowdate(),cint(item.lead_time_days)),
						"uom":	item.stock_uom,
						"warehouse": d.warehouse,
						"item_name": item.item_name,
						"description": item.description,
						"item_group": item.item_group,
						"qty": d.reorder_qty,
						"brand": item.brand,
					})

				mr.insert()
				mr.submit()
				mr_list.append(mr)

			except:
				_log_exception()

	if mr_list:
		if getattr(frappe.local, "reorder_email_notify", None) is None:
			frappe.local.reorder_email_notify = cint(frappe.db.get_value('Stock Settings', None,
				'reorder_email_notify'))

		if(frappe.local.reorder_email_notify):
			send_email_notification(mr_list)

	if exceptions_list:
		notify_errors(exceptions_list)

	return mr_list

def send_email_notification(mr_list):
	""" Notify user about auto creation of indent"""

	email_list = frappe.db.sql_list("""select distinct r.parent
		from tabUserRole r, tabUser p
		where p.name = r.parent and p.enabled = 1 and p.docstatus < 2
		and r.role in ('Purchase Manager','Material Manager')
		and p.name not in ('Administrator', 'All', 'Guest')""")

	msg="""<h3>Following Material Requests has been raised automatically \
		based on item reorder level:</h3>"""
	for mr in mr_list:
		msg += "<p><b><u>" + mr.name + """</u></b></p><table class='table table-bordered'><tr>
			<th>Item Code</th><th>Warehouse</th><th>Qty</th><th>UOM</th></tr>"""
		for item in mr.get("items"):
			msg += "<tr><td>" + item.item_code + "</td><td>" + item.warehouse + "</td><td>" + \
				cstr(item.qty) + "</td><td>" + cstr(item.uom) + "</td></tr>"
		msg += "</table>"
	frappe.sendmail(recipients=email_list, 
		subject='Auto Material Request Generation Notification', message = msg)

def notify_errors(exceptions_list):
	subject = "[Important] [ERPNext] Auto Reorder Errors"
	content = """Dear System Manager,

An error occured for certain Items while creating Material Requests based on Re-order level.

Please rectify these issues:
---
<pre>
%s
</pre>
---
Regards,
Administrator""" % ("\n\n".join(exceptions_list),)

	from frappe.email import sendmail_to_system_managers
	sendmail_to_system_managers(subject, content)
