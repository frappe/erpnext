import frappe

def execute():
	frappe.db.sql("""update `tabJournal Entry` set title =
		if(ifnull(pay_to_recd_from, "")!="", pay_to_recd_from,
			(select account from `tabJournal Entry Account`
				where parent=`tabJournal Entry`.name and idx=1 limit 1))""")
