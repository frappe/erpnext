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

	onload: function(frm) {
		if (frm.doc.__islocal)
			frm.trigger("clear_property_table");
	},

	employee: function(frm) {
		frm.trigger("clear_property_table");
	},

	clear_property_table: function(frm) {
		let table = (frm.doctype == "Employee Promotion") ? "promotion_details" : "transfer_details";
		frm.clear_table(table);
		frm.refresh_field(table);

		frm.fields_dict[table].grid.wrapper.find(".grid-add-row").hide();
	},

	refresh: function(frm) {
		let table;
		if (frm.doctype == "Employee Promotion") {
			table = "promotion_details";
		} else if (frm.doctype == "Employee Transfer") {
			table = "transfer_details";
		}

		if (!table)
			return;

		frm.fields_dict[table].grid.wrapper.find(".grid-add-row").hide();
		frm.events.setup_employee_property_button(frm, table);
	},

	setup_employee_property_button: function(frm, table) {
		frm.fields_dict[table].grid.add_custom_button(__("Add Employee Property"), () => {
			if (!frm.doc.employee) {
				frappe.msgprint(__("Please select Employee first."));
				return;
			}

			const allowed_fields = [];
			const exclude_fields = ["naming_series", "employee", "first_name", "middle_name", "last_name", "marital_status", "ctc",
				"employee_name", "status", "image", "gender", "date_of_birth", "date_of_joining", "lft", "rgt", "old_parent"];

			const exclude_field_types = ["HTML", "Section Break", "Column Break", "Button", "Read Only", "Tab Break", "Table"];

			frappe.model.with_doctype("Employee", () => {
				const field_label_map = {};
				frappe.get_meta("Employee").fields.forEach(d => {
					field_label_map[d.fieldname] = __(d.label) + ` (${d.fieldname})`;
					if (!in_list(exclude_field_types, d.fieldtype) && !in_list(exclude_fields, d.fieldname)) {
						allowed_fields.push({
							label: field_label_map[d.fieldname],
							value: d.fieldname,
						});
					}
				});

				show_dialog(frm, table, allowed_fields);
			});
		});
	}
});

var show_dialog = function(frm, table, field_labels) {
	var d = new frappe.ui.Dialog({
		title: "Update Property",
		fields: [
			{fieldname: "property", label: __("Select Property"), fieldtype: "Autocomplete", options: field_labels},
			{fieldname: "current", fieldtype: "Data", label: __("Current"), read_only: true},
			{fieldname: "new_value", fieldtype: "Data", label: __("New")}
		],
		primary_action_label: __("Add to Details"),
		primary_action: () => {
			d.get_primary_btn().attr("disabled", true);
			if (d.data) {
				d.data.new = d.get_values().new_value;
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
				if (r.message) {
					d.data.current = r.message.value;
					d.data.property = r.message.label;

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
			"options": options || '',
			"label": __("New")
		},
		parent: d.fields_dict.new_value.wrapper,
		only_input: false
	});
	dynamic_field.make_input();
	d.replace_field("new_value", dynamic_field.df);
};

var add_to_details = function(frm, d, table) {
	let data = d.data;
	if (data.fieldname) {
		if (validate_duplicate(frm, table, data.fieldname)) {
			frappe.show_alert({message: __("Property already added"), indicator: "orange"});
			return false;
		}
		if (data.current == data.new) {
			frappe.show_alert({message: __("Nothing to change"), indicator: "orange"});
			d.get_primary_btn().attr("disabled", false);
			return false;
		}
		frm.add_child(table, {
			fieldname: data.fieldname,
			property: data.property,
			current: data.current,
			new: data.new
		});
		frm.refresh_field(table);

		frm.fields_dict[table].grid.wrapper.find(".grid-add-row").hide();

		d.fields_dict.new_value.$wrapper.html("");
		d.set_value("property", "");
		d.set_value("current", "");
		frappe.show_alert({message: __("Added to details"), indicator: "green"});
		d.data = {};
	} else {
		frappe.show_alert({message: __("Value missing"), indicator: "red"});
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
