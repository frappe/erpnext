report.customize_filters = function() {

  this.add_filter({fieldname:'posting_date', label:'Posting Date', fieldtype:'Date', ignore : 1, parent:'Item'});
  //this.add_filter({fieldname:'weekly_working_days', label:'Weekly Working Days', fieldtype:'Select', options:NEWLINE+1+NEWLINE+2+NEWLINE+3+NEWLINE+4+NEWLINE+5+NEWLINE+6+NEWLINE+7, ignore : 1, parent:'Item'});

  this.filter_fields_dict['Item'+FILTER_SEP +'From Posting Date'].df.in_first_page = 1;
  this.filter_fields_dict['Item'+FILTER_SEP +'To Posting Date'].df.in_first_page = 1;
  //this.filter_fields_dict['Item'+FILTER_SEP +'Weekly Working Days'].df.in_first_page = 1;


}