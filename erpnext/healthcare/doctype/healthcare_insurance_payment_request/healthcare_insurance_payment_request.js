// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Insurance Payment Request', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1){
			frm.add_custom_button(__('Payment'), function() {
				frm.events.make_payment_entry(frm);
			});
		}
	},
	from_date: function(frm){
		get_insurance_claim(frm);
	},
	to_date: function(frm){
		get_insurance_claim(frm);
	},
	insurance_company: function(frm){
		get_insurance_claim(frm);
	},
	posting_date_type: function(frm){
		get_insurance_claim(frm);
	},
	make_payment_entry: function(frm) {
		return frappe.call({
			method: 'create_payment_entry',
			doc: frm.doc,
			callback: function(r) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route('Form', doc[0].doctype, doc[0].name);
			}
		});
	}
});
var get_insurance_claim = function(frm){
	frm.doc.healthcare_insurance_payment_request_item = [];
	if(frm.doc.insurance_company){
		var args = {'insurance_company': frm.doc.insurance_company}
		if(frm.doc.from_date){
			args['from_date'] = frm.doc.from_date
		}
		if(frm.doc.to_date){
			args['to_date'] = frm.doc.to_date
		}
		args['posting_date_type'] = frm.doc.posting_date_type
		frappe.call({
			'method': 'erpnext.healthcare.doctype.healthcare_insurance_payment_request.healthcare_insurance_payment_request.get_claim_item',
			args:args,
			callback: function (data) {
				if(data.message){
					data.message.forEach(function(claim){
						var child_item=frappe.model.add_child(frm.doc, 'Healthcare Insurance Payment Request Item', 'healthcare_insurance_payment_request_item')
						frappe.model.set_value(child_item.doctype, child_item.name, 'insurance_claim', claim.name);
						frappe.model.set_value(child_item.doctype, child_item.name, 'patient', claim.patient);
						frappe.model.set_value(child_item.doctype, child_item.name, 'healthcare_service_type', claim.healthcare_service_type);
						frappe.model.set_value(child_item.doctype, child_item.name, 'service_template', claim.service_template);
						frappe.model.set_value(child_item.doctype, child_item.name, 'sales_invoice', claim.sales_invoice);
						frappe.model.set_value(child_item.doctype, child_item.name, 'discount', claim.discount);
						frappe.model.set_value(child_item.doctype, child_item.name, 'claim_coverage', claim.coverage);
						frappe.model.set_value(child_item.doctype, child_item.name, 'claim_amount', claim.coverage_amount);
					});
				}
				frm.refresh_fields('healthcare_insurance_payment_request_item');
				set_total_Claim_Amount(frm);
			}
		});
	}
	frm.refresh_fields();
}
let set_total_Claim_Amount = function(frm){
	var total_claim_amount=0;
	for (var i in frm.doc.healthcare_insurance_payment_request_item) {
		var item = frm.doc.healthcare_insurance_payment_request_item[i];
		if(item.claim_amount ){
			total_claim_amount = total_claim_amount + item.claim_amount
		}
	}
	frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'total_claim_amount', total_claim_amount)
}
