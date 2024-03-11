frappe.listview_settings["Material Request"] = {
	add_fields: ["material_request_type", "status", "per_ordered", "per_received", "transfer_status"],
	get_indicator: function (doc) {
		var precision = frappe.defaults.get_default("float_precision");
		if (doc.status == "Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if (doc.transfer_status && doc.docstatus != 2) {
			if (doc.transfer_status == "Not Started") {
				return [__("Not Started"), "orange"];
			} else if (doc.transfer_status == "In Transit") {
				return [__("In Transit"), "yellow"];
			} else if (doc.transfer_status == "Completed") {
				return [__("Completed"), "green"];
			}
		} else if (doc.docstatus == 1 && flt(doc.per_ordered, precision) == 0) {
			return [__("Pending"), "orange", "per_ordered,=,0"];
		} else if (doc.docstatus == 1 && flt(doc.per_ordered, precision) < 100) {
			return [__("Partially ordered"), "yellow", "per_ordered,<,100"];
		} else if (doc.docstatus == 1 && flt(doc.per_ordered, precision) == 100) {
			if (
				doc.material_request_type == "Purchase" &&
				flt(doc.per_received, precision) < 100 &&
				flt(doc.per_received, precision) > 0
			) {
				return [__("Partially Received"), "yellow", "per_received,<,100"];
			} else if (doc.material_request_type == "Purchase" && flt(doc.per_received, precision) == 100) {
				return [__("Received"), "green", "per_received,=,100"];
			} else if (doc.material_request_type == "Purchase") {
				return [__("Ordered"), "green", "per_ordered,=,100"];
			} else if (doc.material_request_type == "Material Transfer") {
				return [__("Transfered"), "green", "per_ordered,=,100"];
			} else if (doc.material_request_type == "Material Issue") {
				return [__("Issued"), "green", "per_ordered,=,100"];
			} else if (doc.material_request_type == "Customer Provided") {
				return [__("Received"), "green", "per_ordered,=,100"];
			} else if (doc.material_request_type == "Manufacture") {
				return [__("Manufactured"), "green", "per_ordered,=,100"];
			}
		}
	},
};
