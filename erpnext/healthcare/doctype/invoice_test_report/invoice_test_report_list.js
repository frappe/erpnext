/*
(c) ESS 2015-16
*/
frappe.listview_settings['Invoice Test Report'] = {
	add_fields: ["name", "status", "invoice"],
	filters:[["status","!=","Completed"],["status","!=","Cancelled"]],
	get_indicator: function(doc) {
		if(doc.status=="Completed"){
        		return [__("Completed"), "green", "status,=,Completed"];
        	}
		if(doc.status=="In Progress"){
        		return [__("In Progress"), "yellow", "status,=,In Progress"];
        	}
		if(doc.status=="Cancelled"){
        		return [__("Cancelled"), "red", "status,=,Cancelled"];
        	}
	}
};

