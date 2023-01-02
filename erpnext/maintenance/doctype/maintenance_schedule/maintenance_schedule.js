// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.maintenance");

erpnext.maintenance.MaintenanceSchedule = class MaintenanceSchedule extends frappe.ui.form.Controller {
	onload() {
		this.setup_queries();
	}

	refresh() {
		erpnext.hide_company();
		this.set_dynamic_link();
	}

	set_dynamic_link() {
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'customer', doctype: 'Customer'};
	}

	setup_queries() {
		this.frm.set_query('customer', erpnext.queries.customer);
		this.frm.set_query('contact_person', erpnext.queries.contact_query);

		this.frm.set_query("item_code", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_sales_item': 1}
			};
		});
	}

	serial_no() {
		var me = this;

		if (me.frm.doc.serial_no) {
			frappe.call({
				method: "erpnext.stock.doctype.serial_no.serial_no.get_serial_no_item_customer",
				args: {
					serial_no: me.frm.doc.serial_no
				},
				callback: function (r) {
					if (r.message) {
						me.frm.set_value(r.message);
					}
				}
			});
		}
	}

	customer() {
		return erpnext.utils.get_party_details(this.frm);
	}

	contact_person() {
		return erpnext.utils.get_contact_details(this.frm);
	}

	create_opportunity(doc, cdt, cdn) {
		frappe.call({
			method: "erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule.create_maintenance_opportunity",
			args: {
				maintenance_schedule: doc.name,
				row: cdn
			},
			freeze: 1,
			freeze_message: __("Creating Opportunity"),
			callback: function(r) {
				if (!r.exc) {
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			}
		});
	}
}

extend_cscript(cur_frm.cscript, new erpnext.maintenance.MaintenanceSchedule({frm: cur_frm}));
