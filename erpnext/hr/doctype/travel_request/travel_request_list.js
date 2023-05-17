
frappe.listview_settings['Travel Request'] =
frappe.get_indicator = function(doc, doctype) {
	
	var settings = frappe.listview_settings[doctype] || {};

	var is_submittable = frappe.model.is_submittable(doctype),
		workflow_fieldname = frappe.workflow.get_state_fieldname(doctype);
    if (doc.status === "Draft") {
		    return [__("Draft"), "red", "status,=,Draft"];
    }
	else if (doc.docstatus === 0 && doc.status === "To Be Approved") {
		return [__("To Be Approved"), "pink", "status,=,To Be Approved"];
	}
	else if (doc.docstatus === 1 && doc.status === "Approved") {
		    return [__("Approved"), "green", "status,=,Approved"];
    }
};