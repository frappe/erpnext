import frappe


def execute():
	qtn_lost_reasons = frappe.db.sql("select * from `tabQuotation Lost Reason`", as_dict=1)
	qtn_lost_reason_detail = frappe.db.sql("select * from `tabQuotation Lost Reason Detail`", as_dict=1)
	opp_lost_reason_detail = frappe.db.sql("select * from `tabOpportunity Lost Reason Detail`", as_dict=1)

	frappe.reload_doc("crm", "doctype", "lost_reason_detail")
	frappe.reload_doc("selling", "doctype", "quotation")
	frappe.reload_doc("vehicles", "doctype", "vehicle_quotation")
	frappe.reload_doc("crm", "doctype", "opportunity")

	for d in qtn_lost_reasons:
		if not frappe.db.exists("Opportunity Lost Reason", d.name):
			d.doctype = "Opportunity Lost Reason"
			doc = frappe.get_doc(d)
			doc.db_insert()

	for d in qtn_lost_reason_detail + opp_lost_reason_detail:
		d.doctype = "Lost Reason Detail"
		doc = frappe.get_doc(d)
		doc.db_insert()

	frappe.delete_doc_if_exists("DocType", "Opportunity Lost Reason Detail")
	frappe.delete_doc_if_exists("DocType", "Quotation Lost Reason Detail")
	frappe.delete_doc_if_exists("DocType", "Quotation Lost Reason")
