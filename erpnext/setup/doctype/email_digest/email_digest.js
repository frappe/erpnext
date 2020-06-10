// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, dt, dn) {
	doc = locals[dt][dn];
	cur_frm.add_custom_button(__('View Now'), function() {
		frappe.call({
			method: 'erpnext.setup.doctype.email_digest.email_digest.get_digest_msg',
			args: {
				name: doc.name
			},
			callback: function(r) {
				var d = new frappe.ui.Dialog({
					title: __('Email Digest: ') + dn,
					width: 800
				});
				$(d.body).html(r.message);
				d.show();
			}
		});
	}, "fa fa-eye-open", "btn-default");

	if (!cur_frm.is_new()) {
		cur_frm.add_custom_button(__('Send Now'), function() {
			return cur_frm.call('send', null, (r) => {
				frappe.show_alert(__('Message Sent'));
			});
		});
	}
};

cur_frm.cscript.addremove_recipients = function(doc, dt, dn) {
	// Get user list

	return cur_frm.call('get_users', null, function(r) {
		// Open a dialog and display checkboxes against email addresses
		doc = locals[dt][dn];
		var d = new frappe.ui.Dialog({
			title: __('Add/Remove Recipients'),
			width: 400
		});

		$.each(r.user_list, function(i, v) {
			var fullname = frappe.user.full_name(v.name);
			if(fullname !== v.name) fullname = fullname + " &lt;" + v.name + "&gt;";

			if(v.enabled==0) {
				fullname = repl("<span style='color: red'> %(name)s (" + __("disabled user") + ")</span>", {name: v.name});
			}

			$('<div class="checkbox"><label>\
				<input type="checkbox" data-id="' + v.name + '"'+
					(v.checked ? 'checked' : '') +
			'> '+ fullname +'</label></div>').appendTo(d.body);
		});

		// Display add recipients button
		d.set_primary_action("Update", function() {
			cur_frm.cscript.add_to_rec_list(doc, d.body, r.user_list.length);
		});

		cur_frm.rec_dialog = d;
		d.show();
	});
}

cur_frm.cscript.add_to_rec_list = function(doc, dialog, length) {
	// add checked users to list of recipients
	var rec_list = [];
	$(dialog).find('input:checked').each(function(i, input) {
		rec_list.push($(input).attr('data-id'));
	});

	doc.recipient_list = rec_list.join('\n');
	cur_frm.rec_dialog.hide();
	cur_frm.save();
	cur_frm.refresh_fields();
}
