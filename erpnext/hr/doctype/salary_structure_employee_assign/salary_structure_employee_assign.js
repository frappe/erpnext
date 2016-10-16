// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Structure Employee Assign', {
	refresh: function(frm) {
		frm.disable_save();
		frm.add_custom_button('Sync Employee',function () {
			var employee_add = [],
				employee_remove = [];
				$(frm.fields_dict.employees_html.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if($(check).is(":checked")) {
						employee_add.push([$(this).val(), $(this).attr('data-emaployee-name')]);
					}
				});
				$(frm.fields_dict.marked_salary_structure_html.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if(!($(check).is(":checked"))) {
						employee_remove.push($(this).val());
					}
				});
			console.log([employee_add,employee_remove]);
				frappe.call({
					method: "erpnext.hr.doctype.salary_structure_employee_assign.salary_structure_employee_assign.add_or_update",
					args:{
						"employee_add": employee_add,
						"employee_remove": employee_remove,
						"salary_structure": frm.doc.salary_structure,
						"update_base_and_variable": frm.doc.update_base_variable,
						"base": frm.doc.base,
						"variable": frm.doc.variable
					},

					callback: function() {
						erpnext.salary_structure_employee_assign.load_employees(frm);
					}
				});
		})
	},
	company:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	},
	employment_type:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	},
	branch:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	},
	department:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	},
	designation:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	},
	salary_structure:function (frm) {
		erpnext.salary_structure_employee_assign.load_employees(frm)
	}
});

erpnext.salary_structure_employee_assign = {
		load_employees: function(frm) {
		if(frm.doc.salary_structure) {
			frappe.call({
				method: "erpnext.hr.doctype.salary_structure_employee_assign.salary_structure_employee_assign.get_employees",
				args: {
					salary_structure: frm.doc.salary_structure,
					company: frm.doc.company,
					employment_type: frm.doc.employment_type,
					branch: frm.doc.branch,
					department: frm.doc.department,
					designation: frm.doc.designation
				},
				callback: function(r) {
					if(r.message['unmarked'].length > 0) {
						unhide_field('unmarked_salary_structure');
						if(!frm.employees_html) {
							frm.employees_html = $('<div>')
							.appendTo(frm.fields_dict.employees_html.wrapper);
						}
						new erpnext.EmployeeSelector(frm, frm.fields_dict.employees_html.wrapper, r.message['unmarked'],0)
					}
					else{
						hide_field('unmarked_salary_structure')
					}

					if(r.message['marked'].length > 0) {
						unhide_field('marked_salary_structure');
						if(!frm.marked_salary_structure_html) {
							frm.marked_salary_structure_html = $('<div>')
								.appendTo(frm.fields_dict.marked_salary_structure_html.wrapper);
						}
						new erpnext.EmployeeSelector(frm, frm.fields_dict.marked_salary_structure_html.wrapper, r.message['marked'],1)
					}
					else{
						hide_field('marked_salary_structure')
					}
				}
			});
		}
	}

};

erpnext.EmployeeSelector = Class.extend({
	init: function(frm, wrapper, employee, is_check) {
		this.wrapper = wrapper;
		this.frm = frm;
		this.check = is_check;
		this.make(frm, employee);
	},
	make: function(frm, employee) {
		var me = this;

		$(this.wrapper).empty();
		var employee_toolbar = $('<div class="col-sm-12 top-toolbar">' +
			'<button class="btn btn-default btn-add btn-xs"></button>' +
			'<button class="btn btn-xs btn-default btn-remove"></button>' +
			'</div>').appendTo($(this.wrapper));

		employee_toolbar.find(".btn-add")
			.html(__('Check all'))
			.on("click", function() {
				$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if(!$(check).is(":checked")) {
						check.checked = true;
					}
				});
			});

		employee_toolbar.find(".btn-remove")
			.html(__('Uncheck all'))
			.on("click", function() {
				$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
					if($(check).is(":checked")) {
						check.checked = false;
					}
				});
			});

		var row;
		$.each(employee, function(i, m) {
			if (i===0 || (i % 4) === 0) {
				row = $('<div class="row"></div>').appendTo(me.wrapper);
			}

			var $imput =$(repl('<div class="col-sm-3 unmarked-employee-checkbox">\
				<div class="checkbox">\
				<label><input type="checkbox" data-emaployee-name="%(employee_name)s"  class="employee-check" value="%(employee)s"/>\
				%(employee_name)s</label>\
				</div></div>', {employee: m.employee, employee_name: m.employee_name|| m.employee})).appendTo(row);
			if (me.check) {
				$imput.find('input.employee-check').attr('checked', 'checked')
			}
		});
	}
});
