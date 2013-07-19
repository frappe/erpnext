wn.provide('erpnext');
erpnext.set_about = function() {
	wn.provide('wn.app');
	$.extend(wn.app, {
		name: 'ERPNext',
		license: 'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',
		source: 'https://github.com/webnotes/erpnext',
		publisher: 'Web Notes Technologies Pvt Ltd, Mumbai',
		copyright: '&copy; Web Notes Technologies Pvt Ltd',
		version: 'Please see git log for the release number'
	});
}

wn.modules_path = 'erpnext';

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	var brand = ($("<div></div>").append(wn.boot.website_settings.brand_html).text() || 'erpnext');
	$('.navbar-brand').html('<div style="display: inline-block;">\
			<object type="image/svg+xml" data="app/images/splash.svg" class="toolbar-splash"></object>\
		</div>' + brand)
	.attr("title", brand)
	.addClass("navbar-icon-home")
	.css({
		"max-width": "200px",
		"overflow": "hidden",
		"text-overflow": "ellipsis",
		"white-space": "nowrap"
	});
});
