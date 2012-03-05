fields = ["customer_name, per_delivered, per_billed, currency, grand_total_export"]

// render
wn.provide('wn.pages.doclistview.renderfn');

wn.pages.doclistview.renderfn['Sales Order'] = function(parent, data) {
	$(parent).html(repl('<span class="avatar-small"><img src="%(imgsrc)s" /></span>\
		<a href="#!Form/Sales Order/%(name)s">%(name)s</a>\
		<span style="display: inline-block; width: 50%%">%(customer_name)s</span>\
		<span style="display: inline-block; width: 10%%; height: 12px; \
			border: 2px solid #aaa;"><span style="display: inline-block; width: %(per_delivered)s;></span>
		', data))
}