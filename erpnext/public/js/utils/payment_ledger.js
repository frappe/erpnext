frappe.provide("erpnext.accounts");

erpnext.accounts.show_payment_ledger = function (frm) {
	if (frm.doc.docstatus > 0 && frappe.model.can_read("Payment Ledger Entry")) {
		frm.add_custom_button(
			__("Payment Ledger"),
			function () {
				frappe.route_options = {
					company: frm.doc.company,
					period_start_date: frm.doc.posting_date,
					// a future posting date is later than the last modified date
					period_end_date: moment
						.max(moment(frm.doc.posting_date), moment(frm.doc.modified))
						.format("YYYY-MM-DD"),
					voucher_no: frm.doc.name,
					show_cancelled_entries: frm.doc.docstatus === 2,
				};
				frappe.set_route("query-report", "Payment Ledger");
			},
			__("View")
		);
	}
};
