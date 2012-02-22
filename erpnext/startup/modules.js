wn.provide('erpnext.module_page');

erpnext.module_page.setup_page = function(module, wrapper) {
	erpnext.module_page.hide_links(wrapper);
	erpnext.module_page.make_list(module, wrapper);
	$(wrapper).find("a[title]").tooltip({
		delay: { show: 500, hide: 100 }
	});	
}

// hide list links where the user does
// not have read permissions

erpnext.module_page.hide_links = function(wrapper) {
	// lists
	$(wrapper).find('[href*="List/"]').each(function() {
		var href = $(this).attr('href');
		var dt = href.split('/')[1];
		if(wn.boot.profile.can_read.indexOf(get_label_doctype(dt))==-1) {
			var txt = $(this).text();
			$(this).parent().css('color', '#999').html(txt);
		}
	});
	
	// reports
	$(wrapper).find('[data-doctype]').each(function() {
		var dt = $(this).attr('data-doctype');
		if(wn.boot.profile.can_read.indexOf(dt)==-1) {
			var txt = $(this).text();
			$(this).parent().css('color', '#999').html(txt);
		}
	});
	
	// single (forms)
	$(wrapper).find('[href*="Form/"]').each(function() {
		var href = $(this).attr('href');
		var dt = href.split('/')[1];
		if(wn.boot.profile.can_read.indexOf(get_label_doctype(dt))==-1) {
			var txt = $(this).text();
			$(this).parent().css('color', '#999').html(txt);
		}
	});}

// make list of reports

erpnext.module_page.make_list = function(module, wrapper) {
	// make project listing
	wrapper.list = new wn.widgets.Listing({
		parent: $(wrapper).find('.reports-list').get(0),
		method: 'utilities.get_report_list',
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