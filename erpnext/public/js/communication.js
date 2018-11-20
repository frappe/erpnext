frappe.ui.form.on("Communication", {
	refresh: (frm) => {
		// setup custom Make button only if Communication is Email
		if(frm.doc.communication_medium == "Email" && frm.doc.sent_or_received == "Received") {
			frm.events.setup_custom_buttons(frm);
			console.log(frm.doc.subject);
		}
	},

	setup_custom_buttons: (frm) => {
		let confirm_msg = "Are you sure you want to create {0} from this email";
		if(frm.doc.reference_doctype !== "Issue") {
			frm.add_custom_button(__("Issue"), () => {
				frappe.confirm(__(confirm_msg, [__("Issue")]), () => {
					frm.trigger('make_issue_from_communication');
				})
			}, "Make");
		}

		if(!in_list(["Lead", "Opportunity"], frm.doc.reference_doctype)) {
			frm.add_custom_button(__("Lead"), () => {
				frappe.confirm(__(confirm_msg, [__("Lead")]), () => {
					frm.trigger('make_lead_from_communication');
				})
			}, __("Make"));

			frm.add_custom_button(__("Opportunity"), () => {
				frappe.confirm(__(confirm_msg, [__("Opportunity")]), () => {
					frm.trigger('make_opportunity_from_communication');
				})
			}, __("Make"));
		}
	},

	make_lead_from_communication: (frm) => {
		return frappe.call({
			method: "frappe.email.inbox.make_lead_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: (r) => {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	},

	make_issue_from_communication: (frm) => {
		return frappe.call({
			method: "frappe.email.inbox.make_issue_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: (r) => {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	},

	auto_make_issue_from_communication: (frm) => {
		return frappe.call({
			method: "frappe.email.inbox.make_issue_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: (r) => {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	},

	make_opportunity_from_communication: (frm) => {
		return frappe.call({
			method: "frappe.email.inbox.make_opportunity_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: (r) => {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	}
});