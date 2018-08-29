frappe.ui.form.on("Hub Settings", {
	refresh: function(frm) {
		frm.disable_save();
	},

	onload_post_render: function(frm) {
		if(frm.get_field("unregister_from_hub").$input)
			frm.get_field("unregister_from_hub").$input.addClass("btn-danger");
	},

	hub_user_email: function(frm) {
		if(frm.doc.hub_user_email){
			frm.set_value("hub_user_name", frappe.user.full_name(frm.doc.hub_user_email));
		}
	},

	call_register: (frm) => {
		this.frm.call({
			doc: this.frm.doc,
			method: "register",
			args: {},
			freeze: true,
			callback: function(r) {},
			onerror: function() {
				frappe.msgprint(__("Wrong Password"));
				frm.set_value("enabled", 0);
			}
		});
	},

	unregister_from_hub: (frm) => {
		frappe.verify_password(() => {
			var d = frappe.confirm(__('Are you sure you want to unregister?'), () => {
				frm.call('unregister');
			}, () => {}, __('Confirm Action'));
			d.get_primary_btn().addClass("btn-danger");
		});
	},
});
