// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transactions Cleanup', {
	// after_save(frm) {
	// 	frappe.confirm(__("Are you sure you want to delete all this?"), function() {
	// 		frappe.call({
	// 			method:
	// 			"erpnext.setup.doctype.transaction_cleanup.transaction_cleanup.on_submit",
	// 			args: {name: doc.name},
	// 			callback: function(data){
	// 				if(!data.exc){
	// 					frm.reload_doc();
	// 				}
	// 			}
	// 		})
	// 	} , () => this.handle_save_fail(btn, on_error) );
	// }
});
	

			// frappe.validated = true;
			// this.script_manager.trigger("before_submit").then(function() {
			// 	if(!frappe.validated) {
			// 		return this.handle_save_fail(btn, on_error);
			// 	}

			// 	this.save('Submit', function(r) {
			// 		if(r.exc) {
			// 			this.handle_save_fail(btn, on_error);
			// 		} else {
			// 			frappe.utils.play_sound("submit");
			// 			callback && callback();
			// 			this.script_manager.trigger("on_submit")
			// 				.then(() => resolve(this))
			// 				.then(() => {
			// 					if (frappe.route_hooks.after_submit) {
			// 						let route_callback = frappe.route_hooks.after_submit;
			// 						delete frappe.route_hooks.after_submit;
			// 						route_callback(this);
			// 					}
			// 				});
			// 		}
			// 	}, btn, () => this.handle_save_fail(btn, on_error), resolve);
			// });
