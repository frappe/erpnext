frappe.ui.form.on("Communication", {
	refresh: function(frm) {
		if(frm.doc.reference_doctype !== "Issue") {
			frm.add_custom_button(__("Issue"), function() {
				frappe.confirm("Are you sure you want to create Issue from this email", function(){
					frm.trigger('make_issue_from_communication');
				})
			}, "Make");
		}

		if(!inList(["Lead", "Opportunity"], frm.doc.reference_doctype)) {
			frm.add_custom_button(__("Lead"), function() {
				frappe.confirm("Are you sure you want to create Lead from this email", function(){
					frm.trigger('make_lead_from_communication');	
				})
			}, "Make");

			frm.add_custom_button(__("Opportunity"), function() {
				frappe.confirm("Are you sure you want to create Opportunity from this email", function(){
					frm.trigger('make_opportunity_from_communication');
				})
			}, "Make");
		}


		frm.page.set_inner_btn_group_as_primary(__("Make"));
	},

	make_lead_from_communication: function(frm) {
		return frappe.call({
			method: "frappe.email.inbox.make_lead_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: function(r) {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	},

	make_issue_from_communication: function(frm) {
		return frappe.call({
			method: "frappe.email.inbox.make_issue_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: function(r) {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	},

	make_opportunity_from_communication: function(frm) {
		return frappe.call({
			method: "frappe.email.inbox.make_opportunity_from_communication",
			args: {
				communication: frm.doc.name
			},
			freeze: true,
			callback: function(r) {
				if(r.message) {
					frm.reload_doc()
				}
			}
		})
	}
});