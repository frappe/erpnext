// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload_post_render: function() {
		cur_frm.fields_dict.allow_dropbox_access.$input.addClass("btn-primary");

		if(cur_frm.doc.__onload && cur_frm.doc.__onload.files) {
			$(frappe.render_template("backup_files_list", {files:cur_frm.doc.__onload.files}))
				.appendTo(cur_frm.fields_dict.current_backups.$wrapper.empty());
		}
	},
	refresh: function() {
		cur_frm.disable_save();
	},

	validate_send_notifications_to: function() {
		if(!cur_frm.doc.send_notifications_to) {
			msgprint(__("Please specify") + ": " +
				__(frappe.meta.get_label(cur_frm.doctype, "send_notifications_to")));
			return false;
		}

		return true;
	},

	allow_dropbox_access: function() {
		if(cur_frm.cscript.validate_send_notifications_to()) {
			return frappe.call({
				method: "erpnext.setup.doctype.backup_manager.backup_dropbox.get_dropbox_authorize_url",
				callback: function(r) {
					if(!r.exc) {
						cur_frm.set_value("dropbox_access_secret", r.message.secret);
						cur_frm.set_value("dropbox_access_key", r.message.key);
						cur_frm.save(null, function() {
							window.open(r.message.url);
						});
					}
				}
			});
		}
	},

	allow_gdrive_access: function() {
		if(cur_frm.cscript.validate_send_notifications_to()) {
			return frappe.call({
				method: "erpnext.setup.doctype.backup_manager.backup_googledrive.get_gdrive_authorize_url",
				callback: function(r) {
					if(!r.exc) {
						window.open(r.message.authorize_url);
					}
				}
			});
		}
	},

	validate_gdrive: function() {
		return frappe.call({
			method: "erpnext.setup.doctype.backup_manager.backup_googledrive.gdrive_callback",
			args: {
				verification_code: cur_frm.doc.verification_code
			},
		});
	},

	upload_backups_to_dropbox: function() {
		cur_frm.save();
	},

	// upload_backups_to_gdrive: function() {
	// 	cur_frm.save();
	// },
});
