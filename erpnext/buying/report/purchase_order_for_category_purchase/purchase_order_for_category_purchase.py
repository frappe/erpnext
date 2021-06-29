# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns, data = [], []

	info = proccessInfo()

	return columns, data

def proccessInfo():
	dat = []
	column = []
	suppliers = []
	rows = []
	data_suppliers = []

	purchase_orders = frappe.get_all("Purchase Order", ["name, supplier"])

	for po in purchase_orders:
		if po.supplier in suppliers:
			frappe.msgprint("HOla")
		else:
			suppliers.append(po.supplier)

	for supplier in suppliers:
		purchases_orders_supplier = frappe.get_all("Purchase Order", ["name, supplier"], filters = {"supplier":supplier.name})

		for pos in purchases_orders_supplier:
			purchase_orders_items = frappe.get_all("Purchase Order Item", ["name, , item_name, qty"], filters = {"parent":pos.name})

			for poi in purchase_orders_items:
				item = frappe.get_all("Item", ["category_for_purchase"], filters = {"item_code": poi.item_code, "category_for_purchase": filters.get("category_purchase")})

				if item is None:
					frappe.msgprint("HOla")
				else:
					if len(data_suppliers) > 0:
						data_supplier = [{"item_name": poi.item_name, "category_for_purchase": filters.get("category_purchase"), "supplier": supplier.name, "quantity": poi.qty}]
						data_suppliers.append(data_supplier)
					else: 
						for data_sup in data_suppliers:
							if data_sup.item_name == poi.item_name:
								data_sup += poi.qty
							else:
								data_supplier = [{"item_name": poi.item_name, "category_for_purchase": filters.get("category_purchase"), "supplier": supplier.name, "quantity": poi.qty}]
								data_suppliers.append(data_supplier)
	
	return "Hola"