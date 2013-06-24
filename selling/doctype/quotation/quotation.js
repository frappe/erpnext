// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// Module CRM
cur_frm.cscript.tname = "Quotation Item";
cur_frm.cscript.fname = "quotation_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

// =====================================================================================
wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/selling/doctype/sales_common/sales_common.js');

erpnext.selling.QuotationController = erpnext.selling.SellingController.extend({
	refresh: function(doc, dt, dn) {
		this._super();
		
		if(doc.docstatus == 1 && doc.status!='Order Lost') {
			cur_frm.add_custom_button('Make Sales Order', cur_frm.cscript['Make Sales Order']);
			cur_frm.add_custom_button('Set as Lost', cur_frm.cscript['Declare Order Lost']);
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);
		}

		if (!doc.__islocal) {
			cur_frm.communication_view = new wn.views.CommunicationList({
				list: wn.model.get("Communication", {"quotation": doc.name}),
				parent: cur_frm.fields_dict.communication_html.wrapper,
				doc: doc,
				recipients: doc.contact_email
			});		
		}
		
		this.quotation_to();
	},
	
	quotation_to: function() {
		this.frm.toggle_reqd("lead", this.frm.doc.quotation_to == "Lead");
		this.frm.toggle_reqd("customer", this.frm.doc.quotation_to == "Customer");
	},
	
	validate_company_and_party: function(party_field) {
		if(this.frm.doc.quotation_to == "Lead") {
			return true;
		} else if(!this.frm.doc.quotation_to) {
			msgprint(wn._("Please select a value for" + " " + wn.meta.get_label(this.frm.doc.doctype,
				"quotation_to", this.frm.doc.name)));
			return false;
		} else {
			return this._super(party_field);
		}
	},
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.selling.QuotationController({frm: cur_frm}));

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({
		customer: doc.customer, 
		address: doc.customer_address, 
		contact: doc.contact_person
	}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict.lead.get_query = erpnext.utils.lead_query;

cur_frm.cscript.lead = function(doc, cdt, cdn) {
	if(doc.lead) {
		get_server_fields('get_lead_details', doc.lead,'', doc, cdt, cdn, 1);
		unhide_field('territory');
	}
}


// =====================================================================================
cur_frm.fields_dict['enq_no'].get_query = function(doc,cdt,cdn){
	var cond='';
	var cond1='';
	if(doc.order_type) cond = 'ifnull(`tabOpportunity`.enquiry_type, "") = "'+doc.order_type+'" AND';
	if(doc.customer) cond1 = '`tabOpportunity`.customer = "'+doc.customer+'" AND';
	else if(doc.lead) cond1 = '`tabOpportunity`.lead = "'+doc.lead+'" AND';

	return repl('SELECT `tabOpportunity`.`name` FROM `tabOpportunity` WHERE `tabOpportunity`.`docstatus` = 1 AND `tabOpportunity`.status = "Submitted" AND %(cond)s %(cond1)s `tabOpportunity`.`name` LIKE "%s" ORDER BY `tabOpportunity`.`name` ASC LIMIT 50', {cond:cond, cond1:cond1});
}

// Make Sales Order
// =====================================================================================
cur_frm.cscript['Make Sales Order'] = function() {
	var doc = cur_frm.doc;

	if (doc.docstatus == 1) {
		var n = wn.model.make_new_doc_and_get_name("Sales Order");
		$c('dt_map', args={
			'docs':wn.model.compress([locals["Sales Order"][n]]),
			'from_doctype':'Quotation',
			'to_doctype':'Sales Order',
			'from_docname':doc.name,
			'from_to_list':"[['Quotation', 'Sales Order'], ['Quotation Item', 'Sales Order Item'],['Sales Taxes and Charges','Sales Taxes and Charges'], ['Sales Team', 'Sales Team'], ['TC Detail', 'TC Detail']]"
		}, function(r,rt) {
			loaddoc("Sales Order", n);
		});
	}
}

//pull enquiry details
cur_frm.cscript.pull_enquiry_detail = function(doc,cdt,cdn){

	var callback = function(r,rt){
		if(r.message){
			doc.quotation_to = r.message;

			if(doc.quotation_to == 'Lead') {
					unhide_field('lead');
			}
			else if(doc.quotation_to == 'Customer') {
				unhide_field(['customer','customer_address','contact_person','territory','customer_group']);
			}
			refresh_many(['quotation_details','quotation_to','customer','customer_address', 
				'contact_person', 'lead', 'address_display', 'contact_display', 'contact_mobile', 
				'contact_email', 'territory', 'customer_group', 'order_type']);
		}
	}

	$c_obj(make_doclist(doc.doctype, doc.name),'pull_enq_details','',callback);

}

// declare order lost
//-------------------------
cur_frm.cscript['Declare Order Lost'] = function(){
	var qtn_lost_dialog;

	set_qtn_lost_dialog = function(){
		qtn_lost_dialog = new Dialog(400,400,'Add Quotation Lost Reason');
		qtn_lost_dialog.make_body([
			['HTML', 'Message', '<div class="comment">Please add quotation lost reason</div>'],
			['Text', 'Quotation Lost Reason'],
			['HTML', 'Response', '<div class = "comment" id="update_quotation_dialog_response"></div>'],
			['HTML', 'Add Reason', '<div></div>']
		]);

		var add_reason_btn1 = $a($i(qtn_lost_dialog.widgets['Add Reason']), 'button', 'button');
		add_reason_btn1.innerHTML = 'Add';
		add_reason_btn1.onclick = function(){ qtn_lost_dialog.add(); }

		var add_reason_btn2 = $a($i(qtn_lost_dialog.widgets['Add Reason']), 'button', 'button');
		add_reason_btn2.innerHTML = 'Cancel';
		$y(add_reason_btn2,{marginLeft:'4px'});
		add_reason_btn2.onclick = function(){ qtn_lost_dialog.hide();}

		qtn_lost_dialog.onshow = function() {
			qtn_lost_dialog.widgets['Quotation Lost Reason'].value = '';
			$i('update_quotation_dialog_response').innerHTML = '';
		}

		qtn_lost_dialog.add = function() {
			// sending...
			$i('update_quotation_dialog_response').innerHTML = 'Processing...';
			var arg =	strip(qtn_lost_dialog.widgets['Quotation Lost Reason'].value);
			var call_back = function(r,rt) {
				if(r.message == 'true'){
					$i('update_quotation_dialog_response').innerHTML = 'Done';
					qtn_lost_dialog.hide();
					cur_frm.refresh();
				}
			}
			if(arg) $c_obj(make_doclist(cur_frm.doc.doctype, cur_frm.doc.name),'declare_order_lost',arg,call_back);
			else msgprint("Please add Quotation lost reason");
		}
	}

	if(!qtn_lost_dialog){
		set_qtn_lost_dialog();
	}
	qtn_lost_dialog.show();
}

//================ Last Quoted Price and Last Sold Price suggestion ======================
cur_frm.fields_dict['quotation_details'].grid.get_field('item_code').get_query= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	var cond = (doc.order_type == 'Maintenance') ? " and item.is_service_item = 'Yes'" : " and item.is_sales_item = 'Yes'";
	if(doc.customer) {
		var export_rate_field = wn.meta.get_docfield(cdt, 'export_rate', cdn);
		var precision = (export_rate_field && export_rate_field.fieldtype) === 'Float' ? 6 : 2;
		return repl("\
			select \
				item.name, \
				( \
					select concat('Last Quote @ ', q.currency, ' ', \
						format(q_item.export_rate, %(precision)s)) \
					from `tabQuotation` q, `tabQuotation Item` q_item \
					where \
						q.name = q_item.parent \
						and q_item.item_code = item.name \
						and q.docstatus = 1 \
						and q.customer = \"%(cust)s\" \
					order by q.transaction_date desc \
					limit 1 \
				) as quote_rate, \
				( \
					select concat('Last Sale @ ', si.currency, ' ', \
						format(si_item.basic_rate, %(precision)s)) \
					from `tabSales Invoice` si, `tabSales Invoice Item` si_item \
					where \
						si.name = si_item.parent \
						and si_item.item_code = item.name \
						and si.docstatus = 1 \
						and si.customer = \"%(cust)s\" \
					order by si.posting_date desc \
					limit 1 \
				) as sales_rate, \
				item.item_name, item.description \
			from `tabItem` item \
			where \
				item.%(key)s like \"%s\" \
				%(cond)s \
				limit 25", {
					cust: doc.customer,
					cond: cond,
					precision: precision
				});
	} else {
		return repl("SELECT name, item_name, description FROM `tabItem` item WHERE item.%(key)s LIKE '%s' %(cond)s ORDER BY item.item_code DESC LIMIT 50", {cond:cond});
	}
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.quotation)) {
		cur_frm.email_doc(wn.boot.notification_settings.quotation_message);
	}
}