frappe.listview_settings["Journal Entry"] = {
	add_fields: [
		"voucher_type",
		"posting_date",
		"total_debit",
		"company",
		"user_remark",
	],
	has_indicator_for_draft: 1,
	has_indicator_for_cancelled: 1,
	get_indicator: function (doc) {
		if (doc.docstatus == 0) {
			return [__("Draft"), "red", "docstatus,=,0"];
		} else if (doc.docstatus == 2) {
			return [__("Cancelled"), "grey", "docstatus,=,2"];
		} else {
			return [
				__(doc.voucher_type),
				"blue",
				"voucher_type,=," + doc.voucher_type,
			];
		}
	},
};
