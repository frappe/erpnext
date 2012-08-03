wn.provide('erpnext.blog');

(function() {
	$('body').on('click', '.btn-blog-subscribe', function() {
		var d = new wn.ui.Dialog({
			title: "Get Blog Updates via Email",
			fields: [
				{label: "Your Name", fieldtype:"Data", reqd:1},
				{label: "Your Email Address", fieldtype:"Data", reqd:1
					,description: "You can unsubscribe anytime."},
				{label: "Subscribe", fieldtype:"Button"}
			]
		});
		$(d.fields_dict.subscribe.input).click(function() {
			var args = d.get_values();
			if(!args) return;
			wn.call({
				method: 'website.blog.add_subscriber',
				args: args,
				callback: function(r) {
					if(r.exc) {
						msgprint('Opps there seems to be some error, Please check back after some time.');
					} else {
						msgprint('Thanks for subscribing!');
					}
					d.hide();
				},
				btn: this
			})
		})
		d.show()
	})	
})()
