// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Closing Entry", {
	refresh(frm) {
		frm.trigger("generate_closing_balance");
		frm.trigger("regenerate_closing_balance");
	},

	generate_closing_balance(frm) {
		if (["Queued", "Failed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Generate Stock Closing Entry"), () => {
				frm.call({
					method: "enqueue_job",
					doc: frm.doc,
					freeze: true,
					callback: () => {
						frm.reload_doc();
					},
				});
			});
		}
	},

	regenerate_closing_balance(frm) {
		if (frm.doc.status == "Completed") {
			frm.add_custom_button(__("Regenerate Stock Closing Entry"), () => {
				frm.call({
					method: "regenerate_closing_balance",
					doc: frm.doc,
					freeze: true,
					callback: () => {
						frm.reload_doc();
					},
				});
			});
		}
	},
});
