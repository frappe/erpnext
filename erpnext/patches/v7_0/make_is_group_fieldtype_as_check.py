import frappe

def execute():
	for doctype in ["Sales Person", "Customer Group", "Item Group", "Territory"]:

		frappe.reload_doctype(doctype)

		#In MySQL, you can't modify the same table which you use in the SELECT part.

		frappe.db.sql(""" update `tab{doctype}` set is_group = 1
			where name in (select parent_{field} from (select distinct parent_{field} from `tab{doctype}`
				where parent_{field} != '') as dummy_table)
			""".format(doctype=doctype, field=doctype.strip().lower().replace(' ','_')))
