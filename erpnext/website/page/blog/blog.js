
pscript.onload_blog = function(wrapper) {
	wrapper.blog_list = new wn.widgets.Listing({
		parent: $(wrapper).find('.web-main-section').get(0),
		query: 'select tabBlog.name, title, left(content, 300) as content, tabBlog.modified, \
			ifnull(first_name, "") as first_name, ifnull(last_name, "") as last_name \
			from tabProfile, tabBlog\
		 	where ifnull(published,1)=1 and tabBlog.owner = tabProfile.name',
		hide_refresh: true,
		render_row: function(parent, data) {
			if(data.content.length==300) data.content += '...';
			data.date = prettyDate(data.modified);
			parent.innerHTML = repl('<h4><a href="#!%(name)s">%(title)s</a></h4>\
				<div class="help">By %(first_name)s %(last_name)s on %(date)s</div>\
				<p><div class="comment">%(content)s</div></p><br>', data);
		},
		page_length: 10
	});
	wrapper.blog_list.run();
	
	// subscribe button
	$('#blog-subscribe').click(function() {
		var email = $(wrapper).find('input[name="blog-subscribe"]').val();
		if(!validate_email(email)) {
			msgprint('Please enter a valid email!');
		}
		wn.call({
			module:'website',
			page:'blog',
			method:'subscribe',
			args:email,
			btn: this,
			callback: function() {
				$(wrapper).find('input[name="blog-subscribe"]').val('');
			}
		});		
	})
}