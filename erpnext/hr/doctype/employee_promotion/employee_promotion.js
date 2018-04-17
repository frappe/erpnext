// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Promotion', {
	onload: function(frm){
		if(frm.doc.__islocal){
			frm.doc.promotion_details = [];
		}
	},
	refresh: function(frm) {
		cur_frm.fields_dict["promotion_details"].grid.wrapper.find('.grid-add-row').hide();
		cur_frm.fields_dict["promotion_details"].grid.add_custom_button(__('Add Row'), () => {
			if(!frm.doc.employee){
				frappe.msgprint(__("Please select Employee"))
				return
			}
			frappe.call({
				method: 'erpnext.hr.utils.get_employee_fields_label',
				callback: function(r) {
					if(r.message){
						show_dialog(frm, r.message);
					}
				}
			});
		});
	}
});

var show_dialog = function(frm, field_labels) {
	var d = new frappe.ui.Dialog({
		title: "Update Property",
		fields: [
			{fieldname: "property", label: __('Select Property'), fieldtype:"Select", options: field_labels},
			{fieldname: "current", fieldtype: "Data", label:__('Current'), read_only: true},
			{fieldname: "field_html", fieldtype: "HTML"}
		],
		primary_action_label: __('Add to Details'),
		primary_action: () => {
			var values = d.get_values();
			d.get_primary_btn().attr('disabled', true);
			if(d.data){
				get_property_name(field_labels, d, function(){
					add_to_details(frm, d);
				});
			}
		}
	});
	d.fields_dict["property"].df.onchange = () => {
		let property = d.get_values().property;
		d.data.fieldname = property;
		if(!property){return;}
		frappe.call({
			method: 'erpnext.hr.utils.get_employee_field_property',
			args: {employee: frm.doc.employee, fieldname: property},
			callback: function(r) {
				if(r.message){
					if(r.message.datatype == "Date" || r.message.datatype =="Datetime"){
						d.message.value = frappe.datetime.get_user_fmt(d.message.value)
						console.log(frappe.datetime.get_user_fmt(d.message.value));
					}
					d.data.current = r.message.value;
					d.fields_dict.field_html.$wrapper.html("")
					d.set_value('current', r.message.value);
					render_dynamic_field(d, r.message.datatype, r.message.options, property);
					d.get_primary_btn().attr('disabled', false);
				}
			}
		});
	}
	d.get_primary_btn().attr('disabled', true);
	d.data = {};
	d.show()
}

var render_dynamic_field = function(d, fieldtype, options, fieldname) {
	d.data.new = null;
	var dynamic_field = frappe.ui.form.make_control({
		df: {
			"fieldtype": fieldtype,
			"fieldname": fieldname,
			"options": options || ''
		},
		parent: d.fields_dict.field_html.wrapper,
		only_input: false
	});
	dynamic_field.make_input();
	$(dynamic_field.label_area).text(__("New"));
	dynamic_field.$input.on("change", function(e) {
		d.data.new = e.target.value;
	}).on("awesomplete-close", function(e) {
		d.data.new = e.target.value;
	});
}

var add_to_details = function(frm, d) {
	let data = d.data
	if(data.fieldname){
		if(validate_duplicate(frm, data.fieldname)){
			frappe.show_alert({message:__("Property already added"), indicator:'orange'});
			return false;
		}
		if(data.current == data.new){
			frappe.show_alert({message:__("Nothing to change"), indicator:'orange'});
			d.get_primary_btn().attr('disabled', false);
			return false;
		}
		frm.add_child('promotion_details', {
			fieldname: data.fieldname,
			property: data.property,
			current: data.current,
			new: data.new
		});
		frm.refresh_field('promotion_details');
		d.fields_dict.field_html.$wrapper.html("");
		d.set_value("property", "")
		d.set_value('current', "");
		frappe.show_alert({message:__("Added to details"),indicator:'green'});
		d.data = {}
	}else {
		frappe.show_alert({message:__("Value missing"),indicator:'red'});
	}
}

var validate_duplicate =  function(frm, fieldname){
	let duplicate = false;
	$.each(frm.doc.promotion_details, function(i, detail) {
		if(detail.fieldname === fieldname){
			duplicate = true;
			return;
		}
	});
	return duplicate;
}

var get_property_name = function(labels, d, callback) {
	$.each(labels, function(i, item) {
		if(item.value == d.data.fieldname){
			d.data.property = item.label;
			return;
		}
	});
	callback();
}
