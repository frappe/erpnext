frappe.ui.form.on("Communication", {
	refresh: (frm) => {
		// setup custom Make button only if Communication is Email
		if(frm.doc.communication_medium == "Email" && frm.doc.sent_or_received == "Received") {
			frm.events.setup_custom_buttons(frm);
		}
	},

	setup_custom_buttons: (frm) => {
		let confirm_msg = "Are you sure you want to create {0} from this email";
		var issue_counter = false;
		var lead_opportunity_counter = false;
		for(var idx in frm.doc.dynamic_links) {
			let dynamic_link = frm.doc.dynamic_links[idx];
			if(dynamic_link.link_doctype === "Issue") {
				issue_counter = true;
			}
			if(!in_list(["Lead", "Opportunity"], dynamic_link.link_doctype)) {
				lead_opportunity_counter = true;
			}
		}
		if(issue_counter){
			frm.add_custom_button(__("Issue"), () => {
				frappe.confirm(__(confirm_msg, [__("Issue")]), () => {
					frm.trigger('make_issue_from_communication');
				})
			}, "Make");
		}

		if(lead_opportunity_counter) {
			frm.add_custom_button(__("Lead"), () => {
				frappe.confirm(__(confirm_msg, [__("Lead")]), () => {
					frm.trigger('make_lead_from_communication');
				})
			}, __('Create'));

			frm.add_custom_button(__("Opportunity"), () => {
				frappe.confirm(__(confirm_msg, [__("Opportunity")]), () => {
					frm.trigger('make_opportunity_from_communication');
				})
			}, __('Create'));
		}
	},

	make_lead_from_communication: (frm) => {
		return frappe.call({
			method: "erpnext.crm.doctype.lead.lead.make_lead_from_communication",
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
			method: "erpnext.support.doctype.issue.issue.make_issue_from_communication",
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
			method: "erpnext.crm.doctype.opportunity.opportunity.make_opportunity_from_communication",
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