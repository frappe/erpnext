frappe.listview_settings['Job Card'] = {
	get_indicator: function(doc) {
		if (doc.status === "Work In Progress") {
			return [__("Work In Progress"), "orange", "status,=,Work In Progress"];
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if (doc.docstatus == 2) {
			return [__("Cancelled"), "red", "status,=,Cancelled"];
		} else if (doc.status === "Material Transferred") {
			return [__('Material Transferred'), "blue", "status,=,Material Transferred"];
		} else {
			return [__("Open"), "red", "status,=,Open"];
		}
	}
};