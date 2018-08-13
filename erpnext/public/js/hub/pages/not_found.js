import SubPage from './subpage';
import { get_empty_state } from '../components/empty_state';

erpnext.hub.NotFound = class NotFound extends SubPage {
	refresh() {
		this.$wrapper.html(get_empty_state(
			__('Sorry! I could not find what you were looking for.'),
			`<button class="btn btn-default btn-xs" data-route="marketplace/home">${__('Back to home')}</button>`
		));
	}
}
