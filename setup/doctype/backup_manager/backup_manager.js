cur_frm.cscript.allow_dropbox_access = function(doc) {
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

cur_frm.cscript.backup_right_now = function(doc) {
	msgprint("Backing up and uploading. This may take a few minutes.")
	wn.call({
		method: "setup.doctype.backup_manager.backup_manager.take_backups",
		callback: function(r) {
			msgprint("Backups taken. Please check your email for the response.")
		}
	})
}