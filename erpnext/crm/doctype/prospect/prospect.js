// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	onload (frm) {
		frm.trigger('set_call_and_email_stats')
	},

	refresh (frm) {
		if (!frm.is_new() && frappe.boot.user.can_create.includes("Customer")) {
			frm.add_custom_button(__("Customer"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_customer",
					frm: frm
				});
			}, __("Create"));
		}
		if (!frm.is_new() && frappe.boot.user.can_create.includes("Opportunity")) {
			frm.add_custom_button(__("Opportunity"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
					frm: frm
				});
			}, __("Create"));
		}

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},

	set_call_and_email_stats (frm) {
		frappe.call({
			method: 'erpnext.crm.utils.get_call_and_email_stats',
			args: {
				'doctype': frm.doc.doctype,
				'docname': frm.doc.name
			},
			callback: function(r) {
				if (r.message) {
					let html = `<div class="row">
							<div class="col-xs-6">
								<span> ${__('Outgoing Calls')}: ${r.message.outgoing_calls} </span></span>
							</div>
							<div class="col-xs-6">
								<span> ${__('Incoming Calls')}: ${r.message.incoming_calls} </span></span>
							</div>
							<div class="col-xs-6">
								<span> ${__('Emails Sent')}: ${r.message.emails_sent} </span></span>
							</div>
							<div class="col-xs-6">
								<span> ${__('Emails Received')}: ${r.message.emails_received} </span></span>
							</div>
							</div>` ;

					cur_frm.dashboard.set_headline_alert(html)
				}
				
			}
		});
	}
});
