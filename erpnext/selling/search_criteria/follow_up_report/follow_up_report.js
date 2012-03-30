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

report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide()
  this.mytabs.items['More Filters'].hide()
  
  this.hide_all_filters();
  this.add_filter({fieldname:'follow_up_on', label:'Communication on', fieldtype:'Select', options:''+NEWLINE+'Lead'+NEWLINE+'Opportunity'+NEWLINE+'Quotation',ignore : 1,parent:'Communication Log', in_first_page : 1, single_select :1});
  this.add_filter({fieldname:'lead_name', label:'Lead', fieldtype:'Link', options:'Lead', report_default:'', ignore : 1, parent:'Communication Log', in_first_page : 1});
  this.add_filter({fieldname:'enq_name', label:'Opportunity', fieldtype:'Link', options:'Opportunity', report_default:'', ignore : 1, parent:'Communication Log', in_first_page : 1});
  this.add_filter({fieldname:'qtn_name', label:'Quotation', fieldtype:'Link', options:'Quotation', report_default:'', ignore : 1, parent:'Communication Log', in_first_page : 1});
  
  this.get_filter('Communication Log', 'Communication type').set_as_single();
  this.set_filter_properties('Communication Log', 'Communication by', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Communication Log', 'Communication type', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Communication Log', 'From Date', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Communication Log', 'To Date', {filter_hide:0, in_first_page : 1});

  this.orig_sort_list = [['Date','`tabCommunication Log`.`date`'],['Document Type','`tabCommunication Log`.`parenttype`'],['Document','`tabCommunication Log`.`parent`'],['Follow Up By','`tabCommunication Log`.`follow_up_by`'],['Follow Up Type','`tabCommunication Log`.`follow_up_type`']];
}


report.get_query = function() {
  var lead_id = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Lead'].get_value();
  var enq_id = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Opportunity'].get_value();
  var quo_id = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Quotation'].get_value();

  var follow_up_on = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Communication on'].get_value();
  var follow_up_by = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Communication by'].get_value();

  var on_type = this.filter_fields_dict['Communication Log'+FILTER_SEP+'Communication type'].get_value();
  var from_date = this.filter_fields_dict['Communication Log'+FILTER_SEP+'From Date'].get_value();
  var to_date = this.filter_fields_dict['Communication Log'+FILTER_SEP+'To Date'].get_value();
  
  var cond = 'parenttype IN ("Lead","Opportunity","Quotation")';
  if(follow_up_on) cond = 'parenttype = "'+follow_up_on+'"';

  if((follow_up_on == 'Lead' && lead_id) || (lead_id && !follow_up_on)) cond +=' AND parent = "'+lead_id+'"';
  if((follow_up_on == 'Opportunity' && enq_id) || (enq_id && !follow_up_on)) cond +=' AND parent = "'+enq_id+'"';
  if((follow_up_on == 'Quotation' && quo_id) || (quo_id && !follow_up_on)) cond +=' AND parent = "'+quo_id+'"';

  if(on_type) cond += ' AND follow_up_type ="'+on_type+'"';
  if(from_date) cond += ' AND date >="'+from_date+'"';
  if(to_date) cond += ' AND date <="'+to_date+'"';
  if(follow_up_by) cond += ' AND follow_up_by = "'+follow_up_by+'"';

  var q ='SELECT distinct `tabCommunication Log`.`parenttype`, `tabCommunication Log`.`parent`, `tabCommunication Log`.`date`, `tabCommunication Log`.`notes`, `tabCommunication Log`.`follow_up_type`, `tabCommunication Log`.`follow_up_by` FROM `tabCommunication Log` WHERE '+cond+' ORDER BY '+sel_val(this.dt.sort_sel)+' '+this.dt.sort_order;
  return q;
}
