report.customize_filters = function() {
  this.hide_all_filters();
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Territory'+NEWLINE+'Sales Person',report_default:'Territory',ignore : 1,parent:'Target Detail', single_select :1});
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Target Detail'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',report_default:'Quarterly',ignore : 1, parent:'Target Detail', single_select :1});
  this.add_filter({fieldname:'under', label:'Under',fieldtype:'Select', options:'Sales Order'+NEWLINE+'Delivery Note'+NEWLINE+'Sales Invoice',report_default:'Sales Order',ignore : 1, parent:'Target Detail', single_select :1});
  this.add_filter({fieldname : 'target_on', label:'Target On', fieldtype:'Select', options:'Quantity'+NEWLINE+'Amount',report_default:'Quantity',ignore : 1,parent:'Target Detail', single_select :1});
}
report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}
this.mytabs.items['Select Columns'].hide();