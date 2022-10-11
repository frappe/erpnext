/* ERPNext Status
  frappe.listview_settings['Purchase Receipt'] = {
	add_fields: ["supplier", "supplier_name", "base_grand_total", "is_subcontracted",
		"transporter_name", "is_return", "status", "per_billed", "currency"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "gray", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.per_returned, 2) === 100) {
			return [__("Return Issued"), "grey", "per_returned,=,100"];
		} else if (flt(doc.grand_total) !== 0 && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_billed, 2) === 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	}
};  */

frappe.listview_settings['Purchase Receipt'] = {
    get_indicator: function(doc) {
        if (doc.status === "Draft" || doc.docstatus === 0) {
            return [__("Open"), "orange", "status,=,Draft"];
        } else if (doc.status === "Ready" || doc.docstatus==1) {
            return [__("Ready"), "green", "status,=,Ready"];
        } else if (doc.status === "Shipped") {
            return [__("Shipped"), "green", "status,=,Shipped"];
        }
    },
};
