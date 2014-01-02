// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.support");

wn.ui.form.on_change("Maintenance Schedule", "customer", function(frm) { 
	erpnext.utils.get_customer_details(frm) });
wn.ui.form.on_change("Maintenance Schedule", "customer_address", 
	erpnext.utils.get_address_display);
wn.ui.form.on_change("Maintenance Schedule", "contact_person", 
	erpnext.utils.get_contact_details);	

// TODO commonify this code
erpnext.support.MaintenanceSchedule = wn.ui.form.Controller.extend({
	refresh: function() {
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Sales Order'), 
				function() {
					wn.model.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							order_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
		} else if (this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(wn._("Make Maintenance Visit"), function() {
				wn.model.open_mapped_doc({
					method: "erpnext.support.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
					source_name: cur_frm.doc.name
				})
			})
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
  return{
    filters:{ 'customer': doc.customer}
  }
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
  return{
    filters:{ 'customer': doc.customer}
  }
}

//
cur_frm.fields_dict['item_maintenance_detail'].grid.get_field('item_code').get_query = function(doc, cdt, cdn) {
  return{
    filters:{ 'is_service_item': "Yes"}
  }
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
  var fname = cur_frm.cscript.fname;
  var d = locals[cdt][cdn];
  if (d.item_code) {
    return get_server_fields('get_item_details',d.item_code, 'item_maintenance_detail',doc,cdt,cdn,1);
  }
}

cur_frm.cscript.periodicity = function(doc, cdt, cdn){
  var d = locals[cdt][cdn];
  if(d.start_date && d.end_date){
    arg = {}
    arg.start_date = d.start_date;
    arg.end_date = d.end_date;
    arg.periodicity = d.periodicity;
    return get_server_fields('get_no_of_visits',docstring(arg),'item_maintenance_detail',doc, cdt, cdn, 1);
  }
  else{
    msgprint(wn._("Please enter Start Date and End Date"));
  }
}

cur_frm.cscript.generate_schedule = function(doc, cdt, cdn) {
  if (!doc.__islocal) {
    return $c('runserverobj', args={'method':'generate_schedule', 'docs':wn.model.compress(make_doclist(cdt,cdn))},
      function(r,rt){
        refresh_field('maintenance_schedule_detail');
      }
    );
  } else {
    alert(wn._("Please save the document before generating maintenance schedule"));
  }  
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
  return{ query: "erpnext.controllers.queries.customer_query" } }
