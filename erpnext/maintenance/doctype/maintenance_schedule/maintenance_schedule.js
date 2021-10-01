// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.maintenance");
frappe.ui.form.on('Maintenance Schedule', {
	setup: function (frm) {
		frm.set_query('contact_person', erpnext.queries.contact_query);
		frm.set_query('customer_address', erpnext.queries.address_query);
		frm.set_query('customer', erpnext.queries.customer);
	},
	onload: function (frm) {
		if (!frm.doc.status) {
			frm.set_value({ status: 'Draft' });
		}
		if (frm.doc.__islocal) {
			frm.set_value({ transaction_date: frappe.datetime.get_today() });
		}
	},
	refresh: function (frm) {
		setTimeout(() => {
			frm.toggle_display('generate_schedule', !(frm.is_new() || frm.doc.docstatus));
			frm.toggle_display('schedule', !(frm.is_new()));
		}, 10);
	},
	customer: function (frm) {
		erpnext.utils.get_party_details(frm)
	},
	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, 'customer_address', 'address_display');
	},
	contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},
	generate_schedule: function (frm) {
		if (frm.is_new()) {
			frappe.msgprint(__('Please save first'));
		} else {
			frm.call('generate_schedule');
		}
	}
})

// TODO commonify this code
erpnext.maintenance.MaintenanceSchedule = frappe.ui.form.Controller.extend({
	refresh: function () {
		frappe.dynamic_link = { doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer' };

		var me = this;

		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(__('Sales Order'),
				function () {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
						source_doctype: "Sales Order",
						target: me.frm,
						setters: {
							customer: me.frm.doc.customer || undefined
						},
						get_query_filters: {
							docstatus: 1,
							company: me.frm.doc.company
						}
					});
				}, __("Get Items From"));
		} else if (this.frm.doc.docstatus === 1) {
			let schedules = me.frm.doc.schedules;
			let flag = schedules.some(schedule => schedule.completion_status === "Pending");
			if (flag) {
				this.frm.add_custom_button(__('Maintenance Visit'), function () {
					let options = "";

					me.frm.call('get_pending_data', {data_type: "items"}).then(r => {
						options = r.message;

						let schedule_id = "";
						let d = new frappe.ui.Dialog({
							title: __("Enter Visit Details"),
							fields: [{
								fieldtype: "Select",
								fieldname: "item_name",
								label: __("Item Name"),
								options: options,
								reqd: 1,
								onchange: function () {
									let field = d.get_field("scheduled_date");
									me.frm.call('get_pending_data',
										{
											item_name: this.value,
											data_type: "date"
										}).then(r => {
										field.df.options = r.message;
										field.refresh();
									});
								}
							},
							{
								label: __('Scheduled Date'),
								fieldname: 'scheduled_date',
								fieldtype: 'Select',
								options: "",
								reqd: 1,
								onchange: function () {
									let field = d.get_field('item_name');
									me.frm.call(
										'get_pending_data',
										{
											item_name: field.value,
											s_date: this.value,
											data_type: "id"
										}).then(r => {
										schedule_id = r.message;
									});
								}
							},
							],
							primary_action_label: 'Create Visit',
							primary_action(values) {
								frappe.call({
									method: "erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
									args: {
										item_name: values.item_name,
										s_id: schedule_id,
										source_name: me.frm.doc.name,
									},
									callback: function (r) {
										if (!r.exc) {
											frappe.model.sync(r.message);
											frappe.set_route("Form", r.message.doctype, r.message.name);
										}
									}
								});
								d.hide();
							}
						});
						d.show();
				});
				}, __('Create'));
			}
		}
	},

	start_date: function (doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	end_date: function (doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	periodicity: function (doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);

	},
	no_of_visits: function (doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	set_no_of_visits: function (doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		let me = this;
		if (item.start_date && item.periodicity) {
			me.frm.call('validate_end_date_visits');

		}
	},
});

$.extend(cur_frm.cscript, new erpnext.maintenance.MaintenanceSchedule({ frm: cur_frm }));
