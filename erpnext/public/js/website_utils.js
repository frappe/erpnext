// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

if (!window.erpnext) window.erpnext = {};

<<<<<<< HEAD
// Add / update a new Lead / Communication
// subject, sender, description
frappe.send_message = function(opts, btn) {
	return frappe.call({
		type: "POST",
		method: "erpnext.templates.utils.send_message",
		btn: btn,
		args: opts,
		callback: opts.callback
	});
};

erpnext.subscribe_to_newsletter = function(opts, btn) {
=======
erpnext.subscribe_to_newsletter = function (opts, btn) {
>>>>>>> ec74a5e566 (style: format js files)
	return frappe.call({
		type: "POST",
		method: "frappe.email.doctype.newsletter.newsletter.subscribe",
		btn: btn,
		args: { email: opts.email },
		callback: opts.callback,
	});
<<<<<<< HEAD
}

// for backward compatibility
erpnext.send_message = frappe.send_message;
=======
};
>>>>>>> ec74a5e566 (style: format js files)
