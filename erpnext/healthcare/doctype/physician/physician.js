// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physician', {
	setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d	= locals[cdt][cdn];
			return {
				filters: {
					'root_type': 'Income',
					'company': d.company,
				}
			};
		});
	},
	refresh: function(frm) {
		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Physician'};
		if(!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		}
	}
});

frappe.ui.form.on("Physician", "user_id",function(frm) {
	if(frm.doc.user_id){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "User",
				name: frm.doc.user_id
			},
			callback: function (data) {
				if(!frm.doc.employee){
					frappe.model.get_value('Employee', {'user_id': frm.doc.user_id}, 'name',
						function(data) {
							if(data)
								frappe.model.set_value(frm.doctype,frm.docname, "employee", data.name);
						});
				}
				if(!frm.doc.first_name)
					frappe.model.set_value(frm.doctype,frm.docname, "first_name", data.message.first_name);
				if(!frm.doc.middle_name)
					frappe.model.set_value(frm.doctype,frm.docname, "middle_name", data.message.middle_name);
				if(!frm.doc.last_name)
					frappe.model.set_value(frm.doctype,frm.docname, "last_name", data.message.last_name);
				if(!frm.doc.mobile_phone)
					frappe.model.set_value(frm.doctype,frm.docname, "mobile_phone", data.message.phone);
			}
		});
	}
});

frappe.ui.form.on("Physician", "employee", function(frm) {
	if(frm.doc.employee){
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Employee",
				name: frm.doc.employee
			},
			callback: function (data) {
				if(!frm.doc.designation)
					frappe.model.set_value(frm.doctype,frm.docname, "designation", data.message.designation);
				if(!frm.doc.first_name)
					frappe.model.set_value(frm.doctype,frm.docname, "first_name", data.message.employee_name);
				if(!frm.doc.mobile_phone)
					frappe.model.set_value(frm.doctype,frm.docname, "mobile_phone", data.message.cell_number);
				if(!frm.doc.address)
					frappe.model.set_value(frm.doctype,frm.docname, "address", data.message.current_address);
			}
		});
	}
});
