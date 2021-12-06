// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Appointment Letter', {
	appointment_letter_template: function(frm){
		if (frm.doc.appointment_letter_template){
			frappe.call({
				method: 'erpnext.hr.doctype.appointment_letter.appointment_letter.get_appointment_letter_details',
				args : {
					template : frm.doc.appointment_letter_template
				},
				callback: function(r){
					if(r.message){
						let message_body = r.message;
						frm.set_value("introduction", message_body[0].introduction);
						frm.set_value("closing_notes", message_body[0].closing_notes);
						frm.doc.terms = []
						for (var i in message_body[1].description){
							frm.add_child("terms");
							frm.fields_dict.terms.get_value()[i].title = message_body[1].description[i].title;
							frm.fields_dict.terms.get_value()[i].description = message_body[1].description[i].description;
						}
						frm.refresh();
					}
				}

			});
		}
	},
});
