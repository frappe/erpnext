erpnext.products = {}

wn.require('erpnext/website/js/product_category.js');

pscript.onload_products = function(wrapper) {
	sys_defaults.default_product_category = JSON.parse(sys_defaults.default_product_category);
	erpnext.products.wrapper = wrapper;	

	// make lists
	erpnext.make_product_categories(wrapper);
	erpnext.products.make_product_list(wrapper);
	
	// button
	$(wrapper).find('.products-search .btn').click(function() {
		wrapper.mainlist.run();
	});
	
	$(wrapper).find('.products-search input').keypress(function(ev) {
		if(ev.which==13) $(wrapper).find('.products-search .btn').click();
	});
}

pscript.onshow_products = function(wrapper) {
	// show default product category
	erpnext.products.set_group();
}

erpnext.products.get_group = function() {
	var route = window.location.hash.split('/');
	if(route.length>1) {
		// from url
		var grp = erpnext.product_item_group[route[1]];
		var label = route[1];
	} else {
		// default
		var grp = sys_defaults.default_product_category.item_group;
		var label = sys_defaults.default_product_category.label;
	}
	erpnext.products.cur_group = grp;
	return {grp:grp, label:label};
}

erpnext.products.make_product_list = function(wrapper) {
	wrapper.mainlist = new wn.widgets.Listing({
		parent: $(wrapper).find('.web-main-section').get(0),
		run_btn: $(wrapper).find('.products-search .btn').get(0),
		hide_refresh: true,
		get_query: function() {
			args = {
				searchstr: $('input[name="products-search"]').val() || '',
				cat: erpnext.products.cur_group
			};
			return repl('select t1.name, t1.title, t1.thumbnail_image, \
				t1.page_name, t1.short_description \
				from tabProduct t1, tabItem t2 \
				where t1.item = t2.name \
				and ifnull(t1.published,0)=1 \
				and t2.item_group="%(cat)s" \
				and t1.short_description like "%%(searchstr)s%"', args)
		},
		render_row: function(parent, data) {
			parent.innerHTML = repl('<div style="float:left; width: 115px;">\
				<img src="files/%(thumbnail_image)s" style="width:100px;"></div>\
				<div style="float:left; width: 400px">\
					<b><a href="#!%(page_name)s">%(title)s</a></b>\
					<p>%(short_description)s</p></div>\
				<div style="clear: both; margin-bottom: 15px; border-bottom: 1px solid #AAA"></div>', data);
		}
	});
	
}

erpnext.products.set_group = function() {
	var cat = erpnext.products.get_group();
	if(!cat.grp) {
		// still nothing
		setTimeout('erpnext.products.set_group()', 1000);
		return;		
	}
	// get erpnext.products.default_category
	var wrapper = erpnext.products.wrapper;
	
	$(wrapper).find('h1').html(cat.label);
	wrapper.mainlist.run();
}
