frappe.listview_settings['Bank Payment'] = {
	add_fields: ["status", "docstatus"],
	//filters:[["status","=", ["Pending","Draft"]]],
	// colwidths: {"name":2, "status":2, "expected_start_date":2},
	get_indicator: function(doc) {
        var status = {"Draft": "white",
                        "Pending": "orange",
                        "In progress": "blue",
                        "Waiting Acknowledgement": "blue",
                        "Upload Failed": "red",
                        "Failed": "red",
                        "Completed": "green",
                        "Cancelled": "black"
                        };
        
        return [__(doc.status), status[doc.status], "status,=," + doc.status];
	},
};
