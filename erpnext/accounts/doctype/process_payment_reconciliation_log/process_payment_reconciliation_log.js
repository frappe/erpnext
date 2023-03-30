// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process Payment Reconciliation Log", {
	refresh(frm) {
		let progress = 0;
		if (frm.doc.reconciled_entries != 0) {
			progress = frm.doc.reconciled_entries / frm.doc.total_allocations * 100;
		} else if(frm.doc.total_allocations == 0){
			progress = 100;
		}
		frm.dashboard.add_progress(__('Reconciliation Progress'), progress);
	},
});
