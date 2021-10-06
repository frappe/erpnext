// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contract", {
	contract_template: function (frm) {
		if (frm.doc.contract_template) {
			frappe.call({
				method: 'erpnext.crm.doctype.contract_template.contract_template.get_contract_template',
				args: {
					template_name: frm.doc.contract_template,
					doc: frm.doc
				},
				callback: function(r) {
					if (r && r.message) {
						let contract_template = r.message.contract_template;
						frm.set_value("contract_terms", r.message.contract_terms);
						frm.set_value("requires_fulfilment", contract_template.requires_fulfilment);

						if (frm.doc.requires_fulfilment) {
							// Populate the fulfilment terms table from a contract template, if any
							r.message.contract_template.fulfilment_terms.forEach(element => {
								let d = frm.add_child("fulfilment_terms");
								d.requirement = element.requirement;
							});
							frm.refresh_field("fulfilment_terms");
						}
					}
				}
			});
		}
	},
	start_date: function(frm) {
		frappe.call({
			method:"erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.start_date
			},
			callback: function(resp){
				if(resp.message){
					cur_frm.set_value("start_date_nepali",resp.message)
				}
			}
		})
		set_start_date(this.frm);
	},
	fulfilment_deadline: function(frm) {
		frappe.call({
			method:"erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.fulfilment_deadline
			},
			callback: function(resp){
				if(resp.message){
					cur_frm.set_value("fulfilment_deadline_nepali",resp.message)
				}
			}
		})
		set_fulfilment_deadline(this.frm);
	},
	signed_on: function(frm) {
		frappe.call({
			method:"erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.signed_on
			},
			callback: function(resp){
				if(resp.message){
					cur_frm.set_value("signed_on_nepal",resp.message)
				}
			}
		})
	}
});
