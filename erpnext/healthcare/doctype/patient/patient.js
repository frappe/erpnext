// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient', {
	refresh: function (frm) {
		frm.set_query('patient', 'patient_relation', function () {
			return {
				filters: [
					['Patient', 'name', '!=', frm.doc.name]
				]
			};
		});
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});

		if (frappe.defaults.get_default('patient_name_by') != 'Naming Series') {
			frm.toggle_display('naming_series', false);
		} else {
			erpnext.toggle_naming_series();
		}

		if (frappe.defaults.get_default('collect_registration_fee') && frm.doc.status == 'Disabled') {
			frm.add_custom_button(__('Invoice Patient Registration'), function () {
				invoice_registration(frm);
			});
		}

		if (frm.doc.patient_name && frappe.user.has_role('Physician')) {
			frm.add_custom_button(__('Patient History'), function() {
				frappe.route_options = {'patient': frm.doc.name};
				frappe.set_route('patient_history');
			},'View');
		}

		if (!frm.doc.__islocal && (frappe.user.has_role('Nursing User') || frappe.user.has_role('Physician'))) {
			frm.add_custom_button(__('Vital Signs'), function () {
				create_vital_signs(frm);
			}, 'Create');
			frm.add_custom_button(__('Medical Record'), function () {
				create_medical_record(frm);
			}, 'Create');
			frm.add_custom_button(__('Patient Encounter'), function () {
				create_encounter(frm);
			}, 'Create');
			frm.toggle_enable(['customer'], 0); // ToDo, allow change only if no transactions booked or better, add merge option
		}
	},
	onload: function (frm) {
		if (!frm.doc.dob) {
			$(frm.fields_dict['age_html'].wrapper).html('');
		}
		if (frm.doc.dob) {
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${get_age(frm.doc.dob)}`);
		}
	}
});

frappe.ui.form.on('Patient', 'dob', function(frm) {
	if (frm.doc.dob) {
		let today = new Date();
		let birthDate = new Date(frm.doc.dob);
		if (today < birthDate){
			frappe.msgprint(__('Please select a valid Date'));
			frappe.model.set_value(frm.doctype,frm.docname, 'dob', '');
		}
		else {
			let age_str = get_age(frm.doc.dob);
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${age_str}`);
		}
	}
	else {
		$(frm.fields_dict['age_html'].wrapper).html('');
	}
});

frappe.ui.form.on('Patient Relation', {
	patient_relation_add: function(frm){
		frm.fields_dict['patient_relation'].grid.get_field('patient').get_query = function(doc){
			let patient_list = [];
			if(!doc.__islocal) patient_list.push(doc.name);
			$.each(doc.patient_relation, function(idx, val){
				if (val.patient) patient_list.push(val.patient);
			});
			return { filters: [['Patient', 'name', 'not in', patient_list]] };
		};
	}
});

let create_medical_record = function (frm) {
	frappe.route_options = {
		'patient': frm.doc.name,
		'status': 'Open',
		'reference_doctype': 'Patient Medical Record',
		'reference_owner': frm.doc.owner
	};
	frappe.new_doc('Patient Medical Record');
};

let get_age = function (birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years = age.getFullYear() - 1970;
	return years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
};

let create_vital_signs = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the patient first'));
	}
	frappe.route_options = {
		'patient': frm.doc.name,
	};
	frappe.new_doc('Vital Signs');
};

let create_encounter = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the patient first'));
	}
	frappe.route_options = {
		'patient': frm.doc.name,
	};
	frappe.new_doc('Patient Encounter');
};

let invoice_registration = function (frm) {
	frappe.call({
		doc: frm.doc,
		method: 'invoice_patient_registration',
		callback: function(data) {
			if (!data.exc) {
				if (data.message.invoice) {
					frappe.set_route('Form', 'Sales Invoice', data.message.invoice);
				}
				cur_frm.reload_doc();
			}
		}
	});
};
