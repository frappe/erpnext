cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

//dropbox
cur_frm.cscript.allow_dropbox_access = function(doc) {
	if (doc.send_notifications_to == '') {
		msgprint("Please enter email address.")
	}
	else {
		wn.call({
			method: "setup.doctype.backup_manager.backup_dropbox.get_dropbox_authorize_url",
			callback: function(r) {
				if(!r.exc) {
					cur_frm.set_value("dropbox_access_secret", r.message.secret);
					cur_frm.set_value("dropbox_access_key", r.message.key);
					cur_frm.save(null, function() {
						window.open(r.message.url);
					});
				}
			}
		})
	}
}

cur_frm.cscript.backup_right_now = function(doc) {
	msgprint("Backing up and uploading. This may take a few minutes.")
	wn.call({
		method: "setup.doctype.backup_manager.backup_manager.take_backups_dropbox",
		callback: function(r) {
			msgprint("Backups taken. Please check your email for the response.")
		}
	})
}
//gdrive
cur_frm.cscript.allow_gdrive_access = function(doc) {
	if (doc.send_notifications_to == '') {
		msgprint("Please enter email address.")
	}
	else {
		wn.call({
			method: "setup.doctype.backup_manager.backup_googledrive.get_gdrive_authorize_url",
			callback: function(r) {
				if(!r.exc) {
					window.open(r.message.authorize_url);
				}
			}
		})
	}
}

cur_frm.cscript.validate_gdrive = function(doc) {
	wn.call({
		method: "setup.doctype.backup_manager.backup_googledrive.gdrive_callback",
		args: {
			verification_code: doc.verification_code
		},
	});
}

cur_frm.cscript.upload_backups_to_dropbox = function(doc) {
	cur_frm.save()
}

cur_frm.cscript.upload_backups_to_gdrive = function(doc) {
	cur_frm.save()
}
