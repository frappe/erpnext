wn.require('lib/js/lib/jquery/jquery.ui.sortable.js');

$.extend(wn.pages.modules_setup, {
	modules: ['Activity', 'Accounts', 'Selling', 'Buying', 'Stock', 'Manufacturing', 'Projects', 
		'Support', 'HR', 'Website', 'To Do', 'Messages', 'Calendar', 'Knowledge Base'],	
	onload: function(wrapper) {
		wn.pages.modules_setup.refresh_page(JSON.parse(wn.boot.modules_list || "[]"));
	},
	refresh_page: function(ml) {
		$('#modules-list').empty();

		// Hide Setup and Dashboard modules
		ml.indexOf('Setup')!=-1 && ml.splice(ml.indexOf('Setup'), 1);

		// checked modules
		for(i in ml) {
			$('#modules-list').append(repl('<p style="cursor:move;">\
				<input type="checkbox" data-module="%(m)s"> \
				%(m)s</p>', {m:ml[i]}));
		}
		$('#modules-list [data-module]').attr('checked', true);
		
		// unchecked modules
		var all = wn.pages.modules_setup.modules;
		for(i in all) {
			if(!$('#modules-list [data-module="'+all[i]+'"]').length) {
				$('#modules-list').append(repl('<p style="cursor:move;">\
					<input type="checkbox" data-module="%(m)s"> \
					%(m)s</p>', {m:all[i]}));				
			}
		}
		
	},
	update: function() {
		var ml = [];
		$('#modules-list [data-module]').each(function() {
			if($(this).attr('checked')) 
				ml.push($(this).attr('data-module'));
		});
		
		wn.call({
			method: 'setup.page.modules_setup.modules_setup.update',
			args: {
				ml: JSON.stringify(ml)
			},
			callback: function(r) {
			},
			btn: $('#modules-update').get(0)
		});
	}
});
