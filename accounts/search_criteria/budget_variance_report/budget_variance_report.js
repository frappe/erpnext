report.customize_filters = function() {

  //this.hide_all_filters();
  this.mytabs.items['Select Columns'].hide();
  this.mytabs.items['More Filters'].hide();

 
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Budget Detail'});
  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Fiscal Year'].df.in_first_page = 1;
  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Period'].df.in_first_page = 1;

  this.filter_fields_dict['Budget Detail'+FILTER_SEP +'Fiscal Year'].df['report_default'] = sys_defaults.fiscal_year;
}
report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}
this.mytabs.items['Select Columns'].hide();
