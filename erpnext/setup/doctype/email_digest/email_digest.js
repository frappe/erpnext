// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, dt, dn) {
	doc = locals[dt][dn];
	var save_msg = __("You must Save the form before proceeding");
	var err_msg = __("There was an error. One probable reason could be that you haven't saved the form. Please contact support@erpnext.com if the problem persists.")

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

	if(frappe.session.user==="Administrator") {
		cur_frm.add_custom_button(__('Send Now'), function() {
			doc = locals[dt][dn];
			if(doc.__unsaved != 1) {
				return $c_obj(doc, 'send', '', function(r, rt) {
					if(r.exc) {
						frappe.msgprint(err_msg);
						console.log(r.exc);
					} else {
						//console.log(arguments);
						frappe.msgprint(__('Message Sent'));
					}
				});
			} else {
				frappe.msgprint(save_msg);
			}
		}, "fa fa-envelope", "btn-default");
	}
}

cur_frm.cscript.addremove_recipients = function(doc, dt, dn) {
	// Get user list
	return $c_obj(doc, 'get_users', '', function(r, rt) {
		if(r.exc) {
			frappe.msgprint(r.exc);
		} else {
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
		}
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
