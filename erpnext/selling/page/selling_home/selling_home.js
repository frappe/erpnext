pscript['onload_selling-home'] = function(wrapper) {
	erpnext.module_page.hide_links(wrapper);
	erpnext.module_page.make_list('Selling', wrapper);
}

wn.provide('erpnext.module_page');

// hide list links where the user does
// not have read permissions

erpnext.module_page.hide_links = function(wrapper) {
	$(wrapper).find('[href*="List/"]').each(function() {
		var href = $(this).attr('href');
		var dt = href.split('/')[1];
		if(wn.boot.profile.can_read.indexOf(dt)==-1) {
			$(this).toggle(false);
		}
	});
}

// make list of reports

erpnext.module_page.make_list = function(module, wrapper) {
	// make project listing
	wrapper.list = new wn.widgets.Listing({
		parent: $(wrapper).find('.reports-list').get(0),
		method: 'selling.page.selling_home.get_report_list',
		render_row: function(row, data) {
			if(!data.parent_doc_type) data.parent_doc_type = data.doc_type;
			$(row).html(repl('<a href="#!Report/%(doc_type)s/%(criteria_name)s" \
				data-doctype="%(parent_doc_type)s">\
				%(criteria_name)s</a>', data))
		},
		args: {
			module: module
		},
		no_refresh: true
	});
	wrapper.list.run();	
}