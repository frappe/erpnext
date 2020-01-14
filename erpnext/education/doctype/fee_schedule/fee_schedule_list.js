frappe.listview_settings['Fee Schedule'] = {
	add_fields: ["fee_creation_status", "due_date", "grand_total"],
	get_indicator: function(doc) {
		if (doc.fee_creation_status=="Successful") {
			return [__("Fee Created"), "blue", "fee_creation_status,=,Successful"];
		} else if(doc.fee_creation_status == "In Process") {
			return [__("Creating Fees"), "orange", "fee_creation_status,=,In Process"];
		} else if(doc.fee_creation_status == "Failed") {
			return [__("Fee Creation Failed"), "red", "fee_creation_status,=,Failed"];
		} else {
			return [__("Fee Creation Pending"), "green", "fee_creation_status,=,"];
		}
	}
};
