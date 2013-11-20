// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Module CRM

cur_frm.cscript.tname = "Sales Order Item";
cur_frm.cscript.fname = "sales_order_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";


wn.require('app/selling/sales_common.js');
wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/accounts/doctype/sales_invoice/pos.js');

erpnext.selling.SalesOrderController = erpnext.selling.SellingController.extend({
	refresh: function(doc, dt, dn) {
		this._super();
		this.frm.dashboard.reset();
		
		if(doc.docstatus==1) {
			if(doc.status != 'Stopped') {
				
				cur_frm.dashboard.add_progress(cint(doc.per_delivered) + wn._("% Delivered"), 
					doc.per_delivered);
				cur_frm.dashboard.add_progress(cint(doc.per_billed) + wn._("% Billed"), 
					doc.per_billed);

				cur_frm.add_custom_button(wn._('Send SMS'), cur_frm.cscript.send_sms, "icon-mobile-phone");
				// delivery note
				if(flt(doc.per_delivered, 2) < 100 && doc.order_type=='Sales')
					cur_frm.add_custom_button(wn._('Make Delivery'), this.make_delivery_note);
			
				// maintenance
				if(flt(doc.per_delivered, 2) < 100 && (doc.order_type !='Sales')) {
					cur_frm.add_custom_button(wn._('Make Maint. Visit'), this.make_maintenance_visit);
					cur_frm.add_custom_button(wn._('Make Maint. Schedule'), 
						this.make_maintenance_schedule);
				}

				// indent
				if(!doc.order_type || (doc.order_type == 'Sales'))
					cur_frm.add_custom_button(wn._('Make ') + wn._('Material Request'), 
						this.make_material_request);
			
				// sales invoice
				if(flt(doc.per_billed, 2) < 100)
					cur_frm.add_custom_button(wn._('Make Invoice'), this.make_sales_invoice);
			
				// stop
				if(flt(doc.per_delivered, 2) < 100 || doc.per_billed < 100)
					cur_frm.add_custom_button(wn._('Stop!'), cur_frm.cscript['Stop Sales Order'],"icon-exclamation");
			} else {	
				// un-stop
				cur_frm.dashboard.set_headline_alert(wn._("Stopped"), "alert-danger", "icon-stop");
				cur_frm.add_custom_button(wn._('Unstop'), cur_frm.cscript['Unstop Sales Order'], "icon-check");
			}
		}

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Quotation'), 
				function() {
					wn.model.map_current_doc({
						method: "selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Lost"],
							order_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
		}

		this.order_type(doc);
	},
	
	order_type: function() {
		this.frm.toggle_reqd("delivery_date", this.frm.doc.order_type == "Sales");
	},

	tc_name: function() {
		this.get_terms();
	},
	
	reserved_warehouse: function(doc, cdt, cdn) {
		var item = wn.model.get_doc(cdt, cdn);
		if(item.item_code && item.reserved_warehouse) {
			return this.frm.call({
				method: "selling.utils.get_available_qty",
				child: item,
				args: {
					item_code: item.item_code,
					warehouse: item.reserved_warehouse,
				},
			});
		}
	},

	make_material_request: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.sales_order.sales_order.make_material_request",
			source_name: cur_frm.doc.name
		})
	},

	make_delivery_note: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.sales_order.sales_order.make_delivery_note",
			source_name: cur_frm.doc.name
		})
	},

	make_sales_invoice: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.sales_order.sales_order.make_sales_invoice",
			source_name: cur_frm.doc.name
		})
	},
	
	make_maintenance_schedule: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			source_name: cur_frm.doc.name
		})
	}, 
	
	make_maintenance_visit: function() {
		wn.model.open_mapped_doc({
			method: "selling.doctype.sales_order.sales_order.make_maintenance_visit",
			source_name: cur_frm.doc.name
		})
	},
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));

cur_frm.cscript.new_contact = function(){
	tn = wn.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}

cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	return {
		query: "controllers.queries.get_project_name",
		filters: {
			'customer': doc.customer
		}
	}
}

cur_frm.cscript['Stop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm(wn._("Are you sure you want to STOP ") + doc.name);

	if (check) {
		return $c('runserverobj', {
			'method':'stop_sales_order', 
			'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))
			}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

cur_frm.cscript['Unstop Sales Order'] = function() {
	var doc = cur_frm.doc;

	var check = confirm(wn._("Are you sure you want to UNSTOP ") + doc.name);

	if (check) {
		return $c('runserverobj', {
			'method':'unstop_sales_order', 
			'docs': wn.model.compress(make_doclist(doc.doctype, doc.name))
		}, function(r,rt) {
			cur_frm.refresh();
		});
	}
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.sales_order)) {
		cur_frm.email_doc(wn.boot.notification_settings.sales_order_message);
	}
};
