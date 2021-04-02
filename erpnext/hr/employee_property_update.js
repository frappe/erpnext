frappe.ui.form.on(cur_frm.doctype, {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});
	},
	onload: function(frm){
		if(frm.doc.__islocal){
			if(frm.doctype == "Employee Promotion"){
				frm.doc.promotion_details = [];
			}else if (frm.doctype == "Employee Transfer") {
				frm.doc.transfer_details = [];
			}
		}
	},
	employee: function(frm) {
		frm.add_fetch("employee", "company", "company");
	},
	refresh: function(frm) {
		var table;
		if(frm.doctype == "Employee Promotion"){
			table = "promotion_details";
		}else if (frm.doctype == "Employee Transfer") {
			table = "transfer_details";
		}
		if(!table){return;}
		cur_frm.fields_dict[table].grid.wrapper.find('.grid-add-row').hide();
		cur_frm.fields_dict[table].grid.add_custom_button(__('Add Row'), () => {
			if(!frm.doc.employee){
				frappe.msgprint(__("Please select Employee"));
				return;
			}
			frappe.call({
				method: 'erpnext.hr.utils.get_employee_fields_label',
				callback: function(r) {
					if(r.message){
						show_dialog(frm, table, r.message);
					}
				}
			});
		});
	}
});

var show_dialog = function(frm, table, field_labels) {
	var d = new frappe.ui.Dialog({
		title: "Update Property",
		fields: [
			{fieldname: "property", label: __('Select Property'), fieldtype:"Select", options: field_labels},
			{fieldname: "current", fieldtype: "Data", label:__('Current'), read_only: true},
			{fieldname: "field_html", fieldtype: "HTML"}
		],
		primary_action_label: __('Add to Details'),
		primary_action: () => {
			d.get_primary_btn().attr('disabled', true);
			if(d.data) {
				var input = $('[data-fieldname="field_html"] input');
				d.data.new = input.val();
				$(input).remove();
				add_to_details(frm, d, table);
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
					d.data.current = r.message.value;
					d.data.property = r.message.label;
					d.fields_dict.field_html.$wrapper.html("");
					d.set_value('current', r.message.value);
					render_dynamic_field(d, r.message.datatype, r.message.options, property);
					d.get_primary_btn().attr('disabled', false);
				}
			}
		});
	};
	d.get_primary_btn().attr('disabled', true);
	d.data = {};
	d.show();
};

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
};

var add_to_details = function(frm, d, table) {
	let data = d.data;
	if(data.fieldname){
		if(validate_duplicate(frm, table, data.fieldname)){
			frappe.show_alert({message:__("Property already added"), indicator:'orange'});
			return false;
		}
		if(data.current == data.new){
			frappe.show_alert({message:__("Nothing to change"), indicator:'orange'});
			d.get_primary_btn().attr('disabled', false);
			return false;
		}
		frm.add_child(table, {
			fieldname: data.fieldname,
			property: data.property,
			current: data.current,
			new: data.new
		});
		frm.refresh_field(table);
		d.fields_dict.field_html.$wrapper.html("");
		d.set_value("property", "");
		d.set_value('current', "");
		frappe.show_alert({message:__("Added to details"),indicator:'green'});
		d.data = {};
	}else {
		frappe.show_alert({message:__("Value missing"),indicator:'red'});
	}
};

var validate_duplicate =  function(frm, table, fieldname){
	let duplicate = false;
	$.each(frm.doc[table], function(i, detail) {
		if(detail.fieldname === fieldname){
			duplicate = true;
			return;
		}
	});
	return duplicate;
};
