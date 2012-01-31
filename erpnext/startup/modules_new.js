// Tools Page
erpnext.ListPage = Class.extend({
	init: function(opts) {
		var me = this;
		this.opts = opts;
		this.page = page_body.add_page[opts.title];
		this.page.wrapper = $a(this.page, 'div', 'layout_wrapper');
		this.page.head = new PageHeading(this.wrapper, this.title)
		this.page.list = new wn.widgets.Listing({
			parent: this.page.wrapper,
			query: opts.query,
			render:row: opts.render_row
		});
	},
	show: function() {
		if(this.first) {
			this.page.list.run();
			this.first = false;
		}
		page_body.change_to(this.opts.title);
	}
});

erpnext.ToolsPage = erpnext.ListPage.extend({
	init: function(opts) {
		this._super({
			title: opts.module + ' Settings',
			query: repl('select name, description from tabDocType where \
				module=%(module)s and ifnull(issingle,0)=1 order by name asc', opts),
			render_row: function(parent, data) {
				parent.innerHTML = repl('<a href="#!Form/%(name)s/%(name)s">%(name)s</a>\
					<div class="comment">%(description)s</div>', data)
			}
		})
	}
});