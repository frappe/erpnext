report.customize_filters = function() {
	this.hide_all_filters();

	this.add_filter({fieldname:'date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'GL Entry', 'in_first_page':1});

	this.filter_fields_dict['GL Entry'+FILTER_SEP +'From Date'].df['report_default']=dateutil.obj_to_str(new Date());
//	this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Date'].df['report_default']=dateutil.obj_to_str(new Date());

	this.filter_fields_dict['GL Entry'+FILTER_SEP +'To Date'].df.filter_hide=1;

}

$dh(this.mytabs.tabs['More Filters']);
$dh(this.mytabs.tabs['Select Columns']);
