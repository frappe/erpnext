this.mytabs.items['Select Columns'].hide();

this.mytabs.tabs['More Filters'].hide();

report.customize_filters = function() {
	this.add_filter({
		fieldname:'fiscal_year',
		label:'Fiscal Year', 
		fieldtype:'Link',
		ignore : 1,
		options: 'Fiscal Year',
		parent:'Leave Allocation',
		in_first_page:1
	});
	this.add_filter({
		fieldname:'employee_name',
		label:'Employee Name', 
		fieldtype:'Data',
		ignore : 1,
		options: '',
		parent:'Leave Allocation',
		in_first_page:1
	});
}