frappe.ui.form.on("Hub Settings", {
	refresh: function(frm) {
		frm.add_custom_button(__('Logs'),
			() => frappe.set_route('List', 'Data Migration Run', {
				data_migration_plan: 'Hub Sync'
			}));

		frm.trigger("enabled");
		if (frm.doc.enabled) {
			frm.add_custom_button(__('View Hub'),
				() => frappe.set_route('hub'));
			frm.add_custom_button(__('Sync'),
				() => frm.call('sync'));
		}
	},
	onload: function(frm) {
		if(!frm.doc.country) {
			frm.set_value("country", frappe.defaults.get_default("Country"));
		}
		if(!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("Company"));
		}
	},
	onload_post_render: function(frm) {
		if(frm.get_field("unregister_from_hub").$input)
			frm.get_field("unregister_from_hub").$input.addClass("btn-danger");
	},
	on_update: function(frm) {
	},
	enabled: function(frm) {
		if(!frm.doc.enabled) {
			frm.trigger("set_enable_hub_primary_button");
		} else {
			frm.page.set_primary_action(__("Save Settings"), () => {
				frm.save();
			});
		}
	},

	hub_user_email: function(frm) {
		if(frm.doc.hub_user_email){
			frm.set_value("hub_user_name", frappe.user.full_name(frm.doc.hub_user_email));
		}
	},

	set_enable_hub_primary_button: (frm) => {
		frm.page.set_primary_action(__("Enable Hub"), () => {
			if(frappe.session.user === "Administrator") {
				frappe.msgprint("Please login as another user.")
			} else {
				frappe.verify_password(() => {
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
				} );
			}
		});
	},

	// update_hub: (frm) => {
	// 	this.frm.call({
	// 		doc: this.frm.doc,
	// 		method: "update_hub",
	// 		args: {},
	// 		freeze: true,
	// 		callback: function(r) { },
	// 		onerror: function() { }
	// 	});
	// },

	unregister_from_hub: (frm) => {
		frappe.verify_password(() => {
			var d = frappe.confirm(__('Are you sure you want to unregister?'), () => {
				frm.call('unregister');
			}, () => {}, __('Confirm Action'));
			d.get_primary_btn().addClass("btn-danger");
		});
	},
});
