import SubPage from './subpage';

erpnext.hub.NotFound = class NotFound extends SubPage {
	refresh() {
		this.$wrapper.html(get_empty_state(
			__('Sorry! I could not find what you were looking for.'),
			`<button class="btn btn-default btn-xs" data-route="marketplace/home">${__('Back to home')}</button>`
		));
	}
}
