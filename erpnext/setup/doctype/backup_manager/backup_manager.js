// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	refresh: function() {
		cur_frm.disable_save();
		
		if(!(cint(cur_frm.doc.dropbox_access_allowed) || 
			cint(cur_frm.doc.gdrive_access_allowed))) {
				cur_frm.set_intro(__("You can start by selecting backup frequency and granting access for sync"));
		} else {
			var services = {
				"dropbox": __("Dropbox"),
				"gdrive": __("Google Drive")
			}
			var active_services = [];
			
			$.each(services, function(service, label) {
				var access_allowed = cint(cur_frm.doc[service + "_access_allowed"]);
				var frequency = cur_frm.doc["upload_backups_to_" + service];
				if(access_allowed && frequency && frequency !== "Never") {
					active_services.push(label + " [" + frequency + "]");
				}
			});
			
			if(active_services.length > 0) {
				cur_frm.set_intro(__("Backups will be uploaded to") + ": " + 
					frappe.utils.comma_and(active_services));
			} else {
				cur_frm.set_intro("");
			}
		}
		
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
