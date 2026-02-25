frappe.listview_settings["Journal Entry"] = {
	add_fields: ["voucher_type", "posting_date", "total_debit", "company", "user_remark"],
	get_indicator: function (doc) {
		if (doc.docstatus === 1) {
			return [__(doc.voucher_type), "blue", `voucher_type,=,${doc.voucher_type}`];
		}
	},
};
