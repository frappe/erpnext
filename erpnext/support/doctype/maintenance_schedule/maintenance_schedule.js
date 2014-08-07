// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.support");

frappe.ui.form.on_change("Maintenance Schedule", "customer", function(frm) {
	erpnext.utils.get_party_details(frm) });
frappe.ui.form.on_change("Maintenance Schedule", "customer_address",
	erpnext.utils.get_address_display);
frappe.ui.form.on_change("Maintenance Schedule", "contact_person",
	erpnext.utils.get_contact_details);

// TODO commonify this code
erpnext.support.MaintenanceSchedule = frappe.ui.form.Controller.extend({
	refresh: function() {
		var me = this;

		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(__('From Sales Order'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							order_type: me.frm.doc.order_type,
							customer: me.frm.doc.customer || undefined,
							company: me.frm.doc.company
						}
					});
				}, "icon-download", "btn-default");
		} else if (this.frm.doc.docstatus === 1) {
			this.frm.add_custom_button(__("Make Maintenance Visit"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.support.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
					source_name: me.frm.doc.name,
					frm: me.frm
				})
			}, frappe.boot.doctype_icons["Maintenance Visit"]);
		}
	},

	start_date: function(doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	end_date: function(doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	periodicity: function(doc, cdt, cdn) {
		this.set_no_of_visits(doc, cdt, cdn);
	},

	set_no_of_visits: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);

		if (item.start_date && item.end_date && item.periodicity) {
			if(item.start_date > item.end_date) {
				msgprint(__("Row {0}:Start Date must be before End Date", [item.idx]));
				return;
			}

			var date_diff = frappe.datetime.get_diff(item.end_date, item.start_date) + 1;

			var days_in_period = {
				"Weekly": 7,
				"Monthly": 30,
				"Quarterly": 91,
				"Half Yearly": 182,
				"Yearly": 365
			}

			var no_of_visits = cint(date_diff / days_in_period[item.periodicity]);
			frappe.model.set_value(item.doctype, item.name, "no_of_visits", no_of_visits);
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.support.MaintenanceSchedule({frm: cur_frm}));

cur_frm.cscript.onload = function(doc, dt, dn) {
  if(!doc.status) set_multiple(dt,dn,{status:'Draft'});

  if(doc.__islocal){
    set_multiple(dt,dn,{transaction_date:get_today()});
  }
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return {
		filters:{ 'customer': doc.customer }
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return {
		filters:{ 'customer': doc.customer }
	}
}


cur_frm.fields_dict['item_maintenance_detail'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
	return {
		filters:{ 'is_service_item': "Yes" }
	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var fname = cur_frm.cscript.fname;
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return get_server_fields('get_item_details', d.item_code, 'item_maintenance_detail',
			doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.generate_schedule = function(doc, cdt, cdn) {
	if (!doc.__islocal) {
		return $c('runserverobj', args={'method':'generate_schedule', 'docs':doc},
			function(r, rt) {
				refresh_field('maintenance_schedule_detail');
			});
	} else {
		msgprint(__("Please save the document before generating maintenance schedule"));
	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return { query: "erpnext.controllers.queries.customer_query" }
}
