report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide()
  this.mytabs.items['More Filters'].hide()
  
  this.hide_all_filters();
  this.add_filter({fieldname:'follow_up_on', label:'Follow up on', fieldtype:'Select', options:''+NEWLINE+'Lead'+NEWLINE+'Enquiry'+NEWLINE+'Quotation',ignore : 1,parent:'Follow up', in_first_page : 1, single_select :1});
  this.add_filter({fieldname:'lead_name', label:'Lead', fieldtype:'Link', options:'Lead', report_default:'', ignore : 1, parent:'Follow up', in_first_page : 1});
  this.add_filter({fieldname:'enq_name', label:'Enquiry', fieldtype:'Link', options:'Enquiry', report_default:'', ignore : 1, parent:'Follow up', in_first_page : 1});
  this.add_filter({fieldname:'qtn_name', label:'Quotation', fieldtype:'Link', options:'Quotation', report_default:'', ignore : 1, parent:'Follow up', in_first_page : 1});
  
  this.get_filter('Follow up', 'Follow up type').set_as_single();
  this.set_filter_properties('Follow up', 'Follow up by', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Follow up', 'Follow up type', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Follow up', 'From Date', {filter_hide:0, in_first_page : 1});
  this.set_filter_properties('Follow up', 'To Date', {filter_hide:0, in_first_page : 1});

  this.orig_sort_list = [['Date','`tabFollow up`.`date`'],['Document Type','`tabFollow up`.`parenttype`'],['Document','`tabFollow up`.`parent`'],['Follow Up By','`tabFollow up`.`follow_up_by`'],['Follow Up Type','`tabFollow up`.`follow_up_type`']];
}


report.get_query = function() {
  var lead_id = this.filter_fields_dict['Follow up'+FILTER_SEP+'Lead'].get_value();
  var enq_id = this.filter_fields_dict['Follow up'+FILTER_SEP+'Enquiry'].get_value();
  var quo_id = this.filter_fields_dict['Follow up'+FILTER_SEP+'Quotation'].get_value();

  var follow_up_on = this.filter_fields_dict['Follow up'+FILTER_SEP+'Follow up on'].get_value();
  var follow_up_by = this.filter_fields_dict['Follow up'+FILTER_SEP+'Follow up by'].get_value();

  var on_type = this.filter_fields_dict['Follow up'+FILTER_SEP+'Follow up type'].get_value();
  var from_date = this.filter_fields_dict['Follow up'+FILTER_SEP+'From Date'].get_value();
  var to_date = this.filter_fields_dict['Follow up'+FILTER_SEP+'To Date'].get_value();
  
  var cond = 'parenttype IN ("Lead","Enquiry","Quotation")';
  if(follow_up_on) cond = 'parenttype = "'+follow_up_on+'"';

  if((follow_up_on == 'Lead' && lead_id) || (lead_id && !follow_up_on)) cond +=' AND parent = "'+lead_id+'"';
  if((follow_up_on == 'Enquiry' && enq_id) || (enq_id && !follow_up_on)) cond +=' AND parent = "'+enq_id+'"';
  if((follow_up_on == 'Quotation' && quo_id) || (quo_id && !follow_up_on)) cond +=' AND parent = "'+quo_id+'"';

  if(on_type) cond += ' AND follow_up_type ="'+on_type+'"';
  if(from_date) cond += ' AND date >="'+from_date+'"';
  if(to_date) cond += ' AND date <="'+to_date+'"';
  if(follow_up_by) cond += ' AND follow_up_by = "'+follow_up_by+'"';

  var q ='SELECT distinct `tabFollow up`.`parenttype`, `tabFollow up`.`parent`, `tabFollow up`.`date`, `tabFollow up`.`notes`, `tabFollow up`.`follow_up_type`, `tabFollow up`.`follow_up_by` FROM `tabFollow up` WHERE '+cond+' ORDER BY '+sel_val(this.dt.sort_sel)+' '+this.dt.sort_order;
  return q;
}
