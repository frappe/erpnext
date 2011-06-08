report.customize_filters = function() {

  this.filter_fields_dict['Maintenance Schedule Detail'+FILTER_SEP +'From Scheduled Date'].df.in_first_page = 1;
  this.filter_fields_dict['Maintenance Schedule Detail'+FILTER_SEP +'To Scheduled Date'].df.in_first_page = 1;
  this.filter_fields_dict['Maintenance Schedule Detail'+FILTER_SEP +'Incharge Name'].df.in_first_page = 1;
  this.filter_fields_dict['Maintenance Schedule'+FILTER_SEP +'Customer'].df.in_first_page = 1;
  this.filter_fields_dict['Maintenance Schedule'+FILTER_SEP +'Customer Name'].df.in_first_page = 1;
  this.filter_fields_dict['Maintenance Schedule'+FILTER_SEP +'Sales Order No'].df.in_first_page = 1;
  //this.filter_fields_dict['Maintenance Schedule'+FILTER_SEP +'Status'].df.in_first_page = 0;
  this.filter_fields_dict['Maintenance Schedule'+FILTER_SEP +'Company'].df['report_default'] = sys_defaults.company;
}

this.mytabs.items['Select Columns'].hide()