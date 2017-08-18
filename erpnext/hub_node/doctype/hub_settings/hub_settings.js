frappe.ui.form.on("Hub Settings", {
	onload: function(frm) {
		if(!frm.doc.country) {
			frm.set_value("country", frappe.defaults.get_default("Country"));
		}
		if(!frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("Company"));
		}
		// Set seller details as well if it makes sense

		if(!frm.doc.enabled) {
			frm.trigger("set_enable_hub_primary_button");
		} else {
			frm.page.set_primary_action(__("Save Settings"), () => {
				frm.save();
			});
		}
	},
	onload_post_render: function(frm) {
		if(frm.get_field("unregister_from_hub").$input)
			frm.get_field("unregister_from_hub").$input.addClass("btn-danger");
		// if(frm.get_field("disable_hub_profile").$input)
		// 	frm.get_field("disable_hub_profile").$input.addClass("btn-danger");
	},
	refresh: function(frm) {
	},
	on_update: function(frm) {
	},
	enabled: function(frm) {
		if(frm.doc.enabled) {
			// frm.toggle_display("access_token", true);
		} else {
			frm.trigger("set_enable_hub_primary_button");
		}
	},

	set_enable_hub_primary_button: (frm) => {
		frm.page.set_primary_action(__("Enable Hub"), () => {
			frappe.verify_password(() => {
				// enabled has to be passed to hub
				frm.set_value("enabled", 1);
				this.frm.call({
					doc: this.frm.doc,
					method: "register",
					args: {},
					freeze: true,
					callback: function(r) {
						frm.page.set_primary_action(__("Save Settings"), () => {
							frm.save();
						});
						frm.save();
						// TODO: Handle bad response
						if(!frm.doc.access_token.length) {
							frm.set_value("enabled", 0);
							frm.save();
							frappe.throw(__('No access token received.'));
						}
					},
					onerror: function() {
						frappe.msgprint(__("Wrong Password"));
						frm.set_value("enabled", 0);
					}
				});
			});
		});
	},

	// call_update_hub: (frm) => {
	// 	this.frm.call({
	// 		doc: this.frm.doc,
	// 		method: "update_hub",
	// 		args: {},
	// 		freeze: true,
	// 		callback: function(r) {

	// 		},
	// 		onerror: function() {
	// 			frappe.msgprint(__("Wrong Password"));
	// 		}
	// 	});
	// },

	disable_hub: (frm) => {
		frm.set_value("enabled", 0);
		frm.set_value("publish", 0);
		frm.set_value("access_token", '');
		frm.save();
	},

	unregister_from_hub: (frm) => {
		var me = this;
		frappe.verify_password(() => {
			var d = frappe.confirm(__('Are you sure you want to unregister?'), () => {
				this.frm.call({
					doc: me.frm.doc,
					method: "unregister_from_hub",
					args: {},
					freeze: true,
					callback: function(r) {
						if(!r.exc){
							frm.trigger('disable_hub');
							frappe.msgprint(__("Successfully unregistered."));
						}
					},
					onerror: function() {
						frappe.msgprint(__("Wrong Password"));
					}
				});
			}, () => {}, __('Confirm Action'));
			d.get_primary_btn().addClass("btn-danger");
		});
	},
});