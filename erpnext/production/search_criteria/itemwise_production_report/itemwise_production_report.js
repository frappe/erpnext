report.customize_filters = function() {

  //to hide all filters
  this.hide_all_filters();

  // to unhide required filters
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'ID'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'Production Order'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'From Posting Date'].df.filter_hide = 0;
  this.filter_fields_dict['Stock Entry'+FILTER_SEP +'To Posting Date'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry Detail'+FILTER_SEP +'Target Warehouse'].df.filter_hide = 0;

  this.filter_fields_dict['Stock Entry Detail'+FILTER_SEP +'Item Code'].df.filter_hide = 0;
}