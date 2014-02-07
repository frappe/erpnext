// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['Setup'].onload = function(wrapper) { 
	if(msg_dialog && msg_dialog.display) msg_dialog.hide();
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Setup'),
		single_column: true
	});

	wrapper.appframe.add_module_icon("Setup");
	wrapper.appframe.set_title_right(wn._("Refresh"), function() {
		wn.setup.make(wrapper);
	});
	
	wn.setup.make(wrapper);
	
}

wn.setup = {
	make: function(wrapper) {
		wn.call({
			method: "webnotes.core.page.setup.setup.get",
			callback: function(r) {
				wrapper.find(".layout-main").empty().html(r.message);
			}
		})
	}
}
