import frappe
from frappe import _
from erpnext.stock.utils import get_bin

def execute():
	def_warehouse = frappe.db.sql("""select min(name) from `tabWarehouse` where is_group = 0""")[0][0]

	po_item = list(frappe.db.sql(("""select distinct po.name as poname, poitem.rm_item_code as rm_item_code
					from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitem
					where po.name = poitem.parent
					and po.is_subcontracted = "Yes"
					and po.docstatus = 1"""),as_dict=1))

	items = list(set([d.rm_item_code for d in po_item]))
	item_wh = frappe._dict(frappe.db.sql("""select item_code, default_warehouse
					from `tabItem` where name in ({0})""".format(", ".join(["%s"] * len(items))), items))
	#Update reserved warehouse
	for item in po_item:
		reserve_warehouse = item_wh.get(item.rm_item_code) or def_warehouse
		update_res_warehouse = frappe.db.sql("""update `tabPurchase Order Item Supplied`
								set reserve_warehouse = %s
								where parent = %s and rm_item_code = %s""",(reserve_warehouse
								,item["poname"],item["rm_item_code"]))
	#Update bin
	item_wh_bin = frappe.db.sql(("""select distinct poitemsup.rm_item_code as rm_item_code, 
					poitemsup.reserve_warehouse as reserve_warehouse
					from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
					where po.name = poitemsup.parent
					and po.is_subcontracted = "Yes"
					and po.docstatus = 1"""),as_dict=1)
	for d in item_wh_bin:
		stock_bin = get_bin(d["rm_item_code"], d["reserve_warehouse"])
		stock_bin.update_reserved_qty_for_sub_contracting()