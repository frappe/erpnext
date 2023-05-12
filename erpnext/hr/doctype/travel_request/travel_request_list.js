
frappe.listview_settings['Travel Request'] =
frappe.get_indicator = function(doc, doctype) {
	
	var settings = frappe.listview_settings[doctype] || {};

	var is_submittable = frappe.model.is_submittable(doctype),
		workflow_fieldname = frappe.workflow.get_state_fieldname(doctype);
    if (doc.status === "Draft") {
		    return [__("Draft"), "red", "status,=,Draft"];
    }
	else if (doc.docstatus === 0 && doc.status === "Request For Approval") {
		return [__("Request For Approval"), "pink", "status,=,Request For Approval"];
	}
	else if (doc.docstatus === 1 && doc.status === "Approved") {
		    return [__("Approved"), "green", "status,=,Approved"];
    }
    else if (doc.status === "Check" && doc.docstatus === 0 ) {
		    return [__("Check"), "blue", "status,=,Check"];
    }
};