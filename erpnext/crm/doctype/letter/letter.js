// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Letter", {
	refresh(frm) {
		// Filter for recipient address
		frm.set_query("recipient_address", () => {
			if (!frm.doc.recipient_type || !frm.doc.recipient) {
				return { filters: { name: "" } }; 
			}
			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: frm.doc.recipient_type,
					link_name: frm.doc.recipient,
				},
			};
		});

		// Filter for company address
		frm.set_query("company_address", () => {
			if (!frm.doc.company) {
				return { filters: { name: "" } }; 
			}
			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: "Company",
					link_name: frm.doc.company,
				},
			};
		});
	},

	recipient(frm) {
		if (frm.doc.recipient_type && frm.doc.recipient) {
			frappe.call({
				method: "erpnext.crm.doctype.letter.letter.get_recipient_details",
				args: {
					recipient_type: frm.doc.recipient_type,
					recipient: frm.doc.recipient,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("recipient_name", r.message.recipient_name);
						if (r.message.language) {
							frm.set_value("language", r.message.language);
						}
					}
				},
			});
		} else {
			frm.set_value("recipient_name", "");
			frm.set_value("language", "");
		}
		frm.set_value("recipient_address", "");
		frm.set_value("address_display", "");
	},

	recipient_type(frm) {
		frm.set_value("recipient", "");
		frm.set_value("recipient_name", "");
		frm.set_value("recipient_address", "");
		frm.set_value("address_display", "");
	},

	recipient_address(frm) {
		if (frm.doc.recipient_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {
					address_dict: frm.doc.recipient_address,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("address_display", r.message);
					}
				},
			});
		} else {
			frm.set_value("address_display", "");
		}
	},

	company(frm) {
		frm.set_value("company_address", "");
		frm.set_value("company_address_display", "");

		// Set default letter head from company
		erpnext.utils.set_letter_head(frm);
	},

	company_address(frm) {
		if (frm.doc.company_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {
					address_dict: frm.doc.company_address,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("company_address_display", r.message);
					}
				},
			});
		} else {
			frm.set_value("company_address_display", "");
		}
	},

	letter_template(frm) {
		if (frm.doc.letter_template) {
			frappe.call({
				method: "erpnext.crm.doctype.letter_template.letter_template.get_letter_template",
				args: {
					template_name: frm.doc.letter_template,
					doc: frm.doc,
				},
				callback: function (r) {
					if (r && r.message) {
						if (r.message.subject) {
							frm.set_value("subject", r.message.subject);
						}
						if (r.message.content) {
							frm.set_value("content", r.message.content);
						}
					}
				},
			});
		}
	},
});
