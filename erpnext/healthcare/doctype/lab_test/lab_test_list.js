/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test'] = {
	add_fields: ["name", "status", "invoice"],
	filters:[["docstatus","=","0"]],
	get_indicator: function(doc) {
		if(doc.status=="Approved"){
			return [__("Approved"), "green", "status,=,Approved"];
		}
		if(doc.status=="Rejected"){
			return [__("Rejected"), "yellow", "status,=,Rejected"];
		}
	}
};
