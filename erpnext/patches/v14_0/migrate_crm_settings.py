import frappe


def execute():
	frappe.db.sql("""UPDATE `tabSingles` as t1
		INNER JOIN `tabSingles` as t2 ON
			t1.doctype = 'Selling Settings' AND
			t1.field = 'campaign_naming_by' AND
			t2.doctype = 'CRM Settings' AND
			t2.field = 'campaign_naming_by'
		SET t2.value = t1.value""")

	frappe.db.sql("""UPDATE `tabSingles` as t1
		INNER JOIN `tabSingles` as t2 ON
			t1.doctype = 'Selling Settings' AND
			t1.field = 'close_opportunity_after_days' AND
			t2.doctype = 'CRM Settings' AND
			t2.field = 'close_opportunity_after_days'
		SET t2.value = t1.value""")

	frappe.db.sql("""UPDATE `tabSingles` as t1
		INNER JOIN `tabSingles` as t2 ON
			t1.doctype = 'Selling Settings' AND
			t1.field = 'default_valid_till' AND
			t2.doctype = 'CRM Settings' AND
			t2.field = 'default_valid_till'
		SET t2.value = t1.value""")
