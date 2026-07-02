frappe.listview_settings["Journal Entry"] = {
<<<<<<< HEAD
	add_fields: ["voucher_type", "posting_date", "total_debit", "company", "user_remark"],
	get_indicator: function (doc) {
		if (doc.docstatus == 0) {
			return [__("Draft", "red", "docstatus,=,0")];
		} else if (doc.docstatus == 2) {
			return [__("Cancelled", "grey", "docstatus,=,2")];
		} else {
			return [__(doc.voucher_type), "blue", "voucher_type,=," + doc.voucher_type];
=======
	add_fields: ["voucher_type", "posting_date", "total_debit", "company", "remark", "reversal_of"],
	get_indicator: function (doc) {
		if (doc.docstatus === 1) {
			if (doc.reversal_of && doc.voucher_type == "Exchange Rate Revaluation") {
				return [__("Reversal Of Exchange Rate Revaluation"), "blue"];
			}
			return [__(doc.voucher_type), "blue", `voucher_type,=,${doc.voucher_type}`];
>>>>>>> a0b14c0607 (refactor: reversal capability on exchange rate revaluation)
		}
	},
};
