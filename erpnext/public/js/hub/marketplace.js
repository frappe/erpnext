frappe.provide('hub');
frappe.provide('erpnext.hub');

erpnext.hub.Marketplace = class Marketplace {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;

		frappe.db.get_doc('Hub Settings')
			.then(doc => {
				hub.settings = doc;
				this.registered = doc.registered;

				this.setup_header();
				this.make_sidebar();
				this.make_body();
				this.setup_events();
				this.refresh();
			});
	}

	setup_header() {
		this.page.set_title(__('Marketplace'));
	}

	setup_events() {
		this.$parent.on('click', '[data-route]', (e) => {
			const $target = $(e.currentTarget);
			const route = $target.data().route;
			frappe.set_route(route);
		});
	}

	make_sidebar() {
		this.$sidebar = this.$parent.find('.layout-side-section').addClass('hidden-xs');

		this.make_sidebar_nav_buttons();
		this.make_sidebar_categories();
	}

	make_sidebar_nav_buttons() {
		let $nav_group = this.$sidebar.find('[data-nav-buttons]');
		if (!$nav_group.length) {
			$nav_group = $('<ul class="list-unstyled hub-sidebar-group" data-nav-buttons>').appendTo(this.$sidebar);
		}
		$nav_group.empty();

		const user_specific_items_html = this.registered
			? `<li class="hub-sidebar-item text-muted" data-route="marketplace/profile">
					${__('Your Profile')}
				</li>
				<li class="hub-sidebar-item text-muted" data-route="marketplace/publish">
					${__('Publish Products')}
				</li>`

			: `<li class="hub-sidebar-item text-muted" data-route="marketplace/register">
					${__('Become a seller')}
				</li>`;

		$nav_group.append(`
			<li class="hub-sidebar-item" data-route="marketplace/home">
				${__('Browse')}
			</li>
			<li class="hub-sidebar-item" data-route="marketplace/favourites">
				${__('Favorites')}
			</li>
			${user_specific_items_html}
		`);
	}

	make_sidebar_categories() {
		frappe.call('erpnext.hub_node.get_categories')
			.then(r => {
				const categories = r.message.map(d => d.value).sort();
				const sidebar_items = [
					`<li class="hub-sidebar-item bold is-title">
						${__('Category')}
					</li>`,
					`<li class="hub-sidebar-item active" data-route="marketplace/home">
						${__('All')}
					</li>`,
					...(this.registered
						? [`<li class="hub-sidebar-item active" data-route="marketplace/my-products">
							${__('Your Products')}
						</li>`]
						: []),
					...categories.map(category => `
						<li class="hub-sidebar-item text-muted" data-route="marketplace/category/${category}">
							${__(category)}
						</li>
					`)
				];

				this.$sidebar.append(`
					<ul class="list-unstyled">
						${sidebar_items.join('')}
					</ul>
				`);

				this.update_sidebar();
			});
	}

	make_body() {
		this.$body = this.$parent.find('.layout-main-section');
		this.$body.on('seller-registered', () => {
			this.registered = 1;
			this.make_sidebar_nav_buttons();
		});
	}

	update_sidebar() {
		const route = frappe.get_route_str();
		const $sidebar_item = this.$sidebar.find(`[data-route="${route}"]`);

		const $siblings = this.$sidebar.find('[data-route]');
		$siblings.removeClass('active').addClass('text-muted');

		$sidebar_item.addClass('active').removeClass('text-muted');
	}

	refresh() {
		const route = frappe.get_route();
		this.subpages = this.subpages || {};

		for (let page in this.subpages) {
			this.subpages[page].hide();
		}

		if (route[1] === 'home' && !this.subpages.home) {
			this.subpages.home = new erpnext.hub.Home(this.$body);
		}

		if (route[1] === 'favourites' && !this.subpages.favourites) {
			this.subpages.favourites = new erpnext.hub.Favourites(this.$body);
		}

		if (route[1] === 'search' && !this.subpages.search) {
			this.subpages.search = new erpnext.hub.SearchPage(this.$body);
		}

		if (route[1] === 'category' && route[2] && !this.subpages.category) {
			this.subpages.category = new erpnext.hub.Category(this.$body);
		}

		if (route[1] === 'item' && route[2] && !this.subpages.item) {
			this.subpages.item = new erpnext.hub.Item(this.$body);
		}

		if (route[1] === 'register' && !this.subpages.register) {
			if (this.registered) {
				frappe.set_route('marketplace', 'home');
				return;
			}
			this.subpages.register = new erpnext.hub.Register(this.$body);
		}

		if (route[1] === 'profile' && !this.subpages.profile) {
			this.subpages.profile = new erpnext.hub.Profile(this.$body);
		}

		if (route[1] === 'publish' && !this.subpages.publish) {
			this.subpages.publish = new erpnext.hub.Publish(this.$body);
		}

		if (route[1] === 'my-products' && !this.subpages['my-products']) {
			this.subpages['my-products'] = new erpnext.hub.PublishedProducts(this.$body);
		}

		if (!Object.keys(this.subpages).includes(route[1])) {
			if (!this.subpages.not_found) {
				this.subpages.not_found = new erpnext.hub.NotFound(this.$body);
			}
			route[1] = 'not_found';
		}

		this.update_sidebar();
		frappe.utils.scroll_to(0);
		this.subpages[route[1]].show();
	}
}

class SubPage {
	constructor(parent, options) {
		this.$parent = $(parent);
		this.make_wrapper(options);

		// handle broken images after every render
		if (this.render) {
			this._render = this.render.bind(this);

			this.render = (...args) => {
				this._render(...args);
				frappe.dom.handle_broken_images(this.$wrapper);
			}
		}
	}

	make_wrapper() {
		const page_name = frappe.get_route()[1];
		this.$wrapper = $(`<div class="marketplace-page" data-page-name="${page_name}">`).appendTo(this.$parent);
		this.hide();
	}

	empty() {
		this.$wrapper.empty();
	}

	show() {
		this.refresh();
		this.$wrapper.show();
	}

	hide() {
		this.$wrapper.hide();
	}
}

erpnext.hub.Home = class Home extends SubPage {
	make_wrapper() {
		super.make_wrapper();

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				frappe.set_route('marketplace', 'search', keyword);
			}
		});
	}

	refresh() {
		this.get_items_and_render();
	}

	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_data()
			.then(data => {
				this.render(data);
			});
	}

	get_data() {
		return hub.call('get_data_for_homepage', { country: frappe.defaults.get_user_default('country') });
	}

	render(data) {
		let html = get_item_card_container_html(data.random_items, __('Explore'));
		this.$wrapper.append(html);

		if (data.items_by_country.length) {
			html = get_item_card_container_html(data.items_by_country, __('Near you'));
			this.$wrapper.append(html);
		}
	}
}

erpnext.hub.Favourites = class Favourites extends SubPage {
	refresh() {
		this.get_favourites()
			.then(r => {
				this.render(r.message);
			});
	}

	get_favourites() {
		return frappe.call('erpnext.hub_node.get_item_favourites');
	}

	render(items) {
		this.$wrapper.find('.hub-card-container').empty();
		const html = get_item_card_container_html(items, __('Favourites'));
		this.$wrapper.append(html)
	}
}

erpnext.hub.Category = class Category extends SubPage {
	refresh() {
		this.category = frappe.get_route()[2];
		this.get_items_for_category(this.category)
			.then(r => {
				this.render(r.message);
			});
	}

	get_items_for_category(category) {
		this.$wrapper.find('.hub-card-container').empty();
		return frappe.call('erpnext.hub_node.get_list', {
			doctype: 'Hub Item',
			filters: {
				hub_category: category
			}
		});
	}

	render(items) {
		const html = get_item_card_container_html(items, __(this.category));
		this.$wrapper.append(html)
	}
}

erpnext.hub.SearchPage = class SearchPage extends SubPage {
	make_wrapper() {
		super.make_wrapper();

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				frappe.set_route('marketplace', 'search', keyword);
			}
		});
	}

	refresh() {
		this.keyword = frappe.get_route()[2] || '';
		this.$wrapper.find('input').val(this.keyword);

		this.get_items_by_keyword(this.keyword)
			.then(items => this.render(items));
	}

	get_items_by_keyword(keyword) {
		return hub.call('get_items_by_keyword', { keyword });
	}

	render(items) {
		this.$wrapper.find('.hub-card-container').remove();
		const title = this.keyword ? __('Search results for "{0}"', [this.keyword]) : '';
		const html = get_item_card_container_html(items, title);
		this.$wrapper.append(html);
	}
}

erpnext.hub.Item = class Item extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.setup_events();
	}

	refresh() {
		this.show_skeleton();
		this.hub_item_code = frappe.get_route()[2];

		this.own_item = false;

		this.get_item(this.hub_item_code)
			.then(item => {
				this.own_item = item.hub_seller === hub.settings.company_email;
				this.item = item;
				this.render(item);
			});
	}

	show_skeleton() {
		const skeleton = `<div class="hub-item-container">
			<div class="row">
				<div class="col-md-3">
					<div class="hub-item-skeleton-image"></div>
				</div>
				<div class="col-md-6">
					<h2 class="hub-skeleton" style="width: 75%;">Name</h2>
					<div class="text-muted">
						<p class="hub-skeleton" style="width: 35%;">Details</p>
						<p class="hub-skeleton" style="width: 50%;">Ratings</p>
					</div>
					<hr>
					<div class="hub-item-description">
						<p class="hub-skeleton">Desc</p>
						<p class="hub-skeleton" style="width: 85%;">Desc</p>
					</div>
				</div>
			</div>
		</div>`;

		this.$wrapper.html(skeleton);
	}

	setup_events() {
		this.$wrapper.on('click', '.btn-contact-seller', () => {
			const d = new frappe.ui.Dialog({
				title: __('Send a message'),
				fields: [
					{
						fieldname: 'to',
						fieldtype: 'Read Only',
						label: __('To'),
						default: this.item.company
					},
					{
						fieldtype: 'Text',
						fieldname: 'message',
						label: __('Message')
					}
				]
			});

			d.show();
		});
	}

	get_item(hub_item_code) {
		return hub.call('get_item_details', { hub_item_code });
	}

	render(item) {
		const title = item.item_name || item.name;
		const seller = item.company;

		const who = __('Posted By {0}', [seller]);
		const when = comment_when(item.creation);

		const city = item.city ? item.city + ', ' : '';
		const country = item.country ? item.country : '';
		const where = `${city}${country}`;

		const dot_spacer = '<span aria-hidden="true"> · </span>';

		const description = item.description || '';

		const rating_html = get_rating_html(item.average_rating);
		const rating_count = item.no_of_ratings > 0 ? `${item.no_of_ratings} reviews` : __('No reviews yet');

		let edit_buttons_html = '';

		if(this.own_item) {
			edit_buttons_html = `<div style="margin-top: 20px">
				<button class="btn btn-secondary btn-default btn-xs margin-right edit-item">Edit Details</button>
				<button class="btn btn-secondary btn-danger btn-xs unpublish">Unpublish</button>
			</div>`;
		}

		const html = `
			<div class="hub-item-container">
				<div class="row visible-xs">
					<div class="col-xs-12 margin-bottom">
						<button class="btn btn-xs btn-default" data-route="marketplace/home">Back to home</button>
					</div>
				</div>
				<div class="row">
					<div class="col-md-3">
						<div class="hub-item-image">
							<img src="${item.image}">
						</div>
					</div>
					<div class="col-md-8">
						<h2>${title}</h2>
						<div class="text-muted">
							<p>${where}${dot_spacer}${when}</p>
							<p>${rating_html} (${rating_count})</p>
						</div>
						<hr>
						<div class="hub-item-description">
						${description ?
							`<b>${__('Description')}</b>
							<p>${description}</p>
							` : `<p>${__('No description')}<p>`
						}
						</div>
						${edit_buttons_html}
					</div>
					<div class="col-md-1">
						<button class="btn btn-xs btn-default">
							Menu
						</button>
					</div>
				</div>
				<div class="row hub-item-seller">
					<div class="col-md-12 margin-top margin-bottom">
						<b class="text-muted">Seller Information</b>
					</div>
					<div class="col-md-1">
						<img src="https://picsum.photos/200">
					</div>
					<div class="col-md-8">
						<div class="margin-bottom"><a href="#marketplace/seller/${seller}" class="bold">${seller}</a></div>
						<button class="btn btn-xs btn-default text-muted btn-contact-seller">
							${__('Contact Seller')}
						</button>
					</div>
				</div>
				<!-- review area -->
				<div class="row hub-item-review-container">
					<div class="col-md-12 form-footer">
						<div class="form-comments">
							<div class="timeline">
								<div class="timeline-head"></div>
								<div class="timeline-items"></div>
							</div>
						</div>
						<div class="pull-right scroll-to-top">
							<a onclick="frappe.utils.scroll_to(0)"><i class="fa fa-chevron-up text-muted"></i></a>
						</div>
					</div>
				</div>
			</div>
		`;

		this.$wrapper.html(html);

		if(this.own_item) {
			this.bind_edit_buttons();
		}

		this.make_review_area();

		this.get_reviews()
			.then(reviews => {
				this.reviews = reviews;
				this.render_reviews(reviews);
			});
	}

	bind_edit_buttons() {
		this.edit_dialog = new frappe.ui.Dialog({
			title: "Edit Your Product",
			fields: []
		});

		this.$wrapper.find('.edit-item').on('click', this.on_edit.bind(this));
		this.$wrapper.find('.unpublish').on('click', this.on_unpublish.bind(this));
	}

	on_edit() {
		this.edit_dialog.show();
	}

	on_unpublish() {
		if(!this.unpublish_dialog) {
			this.unpublish_dialog = new frappe.ui.Dialog({
				title: "Edit Your Product",
				fields: []
			});
		}

		this.unpublish_dialog.show();
	}

	make_review_area() {
		this.comment_area = new frappe.ui.ReviewArea({
			parent: this.$wrapper.find('.timeline-head').empty(),
			mentions: [],
			on_submit: (values) => {
				values.user = frappe.session.user;
				values.username = frappe.session.user_fullname;

				hub.call('add_item_review', {
					hub_item_code: this.hub_item_code,
					review: JSON.stringify(values)
				})
				.then(review => {
					this.reviews = this.reviews || [];
					this.reviews.push(review);
					this.render_reviews(this.reviews);

					this.comment_area.reset();
				});
			}
		});
	}

	get_reviews() {
		return hub.call('get_item_reviews', { hub_item_code: this.hub_item_code }).catch(() => {});
	}

	render_reviews(reviews=[]) {
		this.$wrapper.find('.timeline-items').empty();

		reviews.sort((a, b) => {
			if (a.modified > b.modified) {
				return -1;
			}

			if (a.modified < b.modified) {
				return 1;
			}

			return 0;
		});

		reviews.forEach(review => this.render_review(review));
	}

	render_review(review) {
		let username = review.username || review.user || __("Anonymous");

		let image_html = review.user_image
			? `<div class="avatar-frame" style="background-image: url(${review.user_image})"></div>`
			: `<div class="standard-image" style="background-color: #fafbfc">${frappe.get_abbr(username)}</div>`

		let edit_html = review.own
			? `<div class="pull-right hidden-xs close-btn-container">
				<span class="small text-muted">
					${'data.delete'}
				</span>
			</div>
			<div class="pull-right edit-btn-container">
				<span class="small text-muted">
					${'data.edit'}
				</span>
			</div>`
			: '';

		let rating_html = get_rating_html(review.rating);

		const $timeline_items = this.$wrapper.find('.timeline-items');

		$(this.get_timeline_item(review, image_html, edit_html, rating_html))
			.appendTo($timeline_items);
	}

	get_timeline_item(data, image_html, edit_html, rating_html) {
		return `<div class="media timeline-item user-content" data-doctype="${''}" data-name="${''}">
			<span class="pull-left avatar avatar-medium hidden-xs" style="margin-top: 1px">
				${image_html}
			</span>
			<div class="pull-left media-body">
				<div class="media-content-wrapper">
					<div class="action-btns">${edit_html}</div>

					<div class="comment-header clearfix">
						<span class="pull-left avatar avatar-small visible-xs">
							${image_html}
						</span>

						<div class="asset-details">
							<span class="author-wrap">
								<i class="octicon octicon-quote hidden-xs fa-fw"></i>
								<span>${data.username}</span>
							</span>
							<a class="text-muted">
								<span class="text-muted hidden-xs">&ndash;</span>
								<span class="hidden-xs">${comment_when(data.modified)}</span>
							</a>
						</div>
					</div>
					<div class="reply timeline-content-show">
						<div class="timeline-item-content">
							<p class="text-muted">
								${rating_html}
							</p>
							<h6 class="bold">${data.subject}</h6>
							<p class="text-muted">
								${data.content}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>`;
	}
}
erpnext.hub.Register = class Register extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.$register_container = $(`<div class="row register-container">`)
			.appendTo(this.$wrapper);
		this.$form_container = $('<div class="col-md-8 col-md-offset-1 form-container">')
			.appendTo(this.$wrapper);
	}

	refresh() {
		this.$register_container.empty();
		this.$form_container.empty();
		this.render();
	}

	render() {
		this.make_field_group();
	}

	make_field_group() {
		const fields = [
			{
				fieldtype: 'Link',
				fieldname: 'company',
				label: __('Company'),
				options: 'Company',
				onchange: () => {
					const value = this.field_group.get_value('company');

					if (value) {
						frappe.db.get_doc('Company', value)
							.then(company => {
								this.field_group.set_values({
									country: company.country,
									company_email: company.email,
									currency: company.default_currency
								});
							});
					}
				}
			},
			{
				fieldname: 'company_email',
				label: __('Email'),
				fieldtype: 'Data'
			},
			{
				fieldname: 'country',
				label: __('Country'),
				fieldtype: 'Read Only'
			},
			{
				fieldname: 'currency',
				label: __('Currency'),
				fieldtype: 'Read Only'
			},
			{
				fieldtype: 'Text',
				label: __('About your Company'),
				fieldname: 'company_description'
			}
		];

		this.field_group = new frappe.ui.FieldGroup({
			parent: this.$form_container,
			fields
		});

		this.field_group.make();

		const default_company = frappe.defaults.get_default('company');
		this.field_group.set_value('company', default_company);

		this.$form_container.find('.form-column').append(`
			<div class="text-right">
				<button type="submit" class="btn btn-primary btn-register btn-sm">${__('Submit')}</button>
			</div>
		`);

		this.$form_container.find('.form-message').removeClass('hidden small').addClass('h4').text(__('Become a Seller'))

		this.$form_container.on('click', '.btn-register', (e) => {
			const form_values = this.field_group.get_values();

			let values_filled = true;
			const mandatory_fields = ['company', 'company_email', 'company_description'];
			mandatory_fields.forEach(field => {
				const value = form_values[field];
				if (!value) {
					this.field_group.set_df_property(field, 'reqd', 1);
					values_filled = false;
				}
			});
			if (!values_filled) return;

			frappe.call({
				method: 'erpnext.hub_node.doctype.hub_settings.hub_settings.register_seller',
				args: form_values,
				btn: $(e.currentTarget)
			}).then(() => {
				frappe.set_route('marketplace', 'publish');

				// custom jquery event
				this.$wrapper.trigger('seller-registered');
			});
		});
	}
}

erpnext.hub.Profile = class Profile extends SubPage {
	make_wrapper() {
		super.make_wrapper();
	}

	refresh() {
		this.get_hub_seller_profile(this.keyword)
			.then(profile => this.render(profile));
	}

	get_hub_seller_profile() {
		return hub.call('get_hub_seller_profile', { hub_seller: hub.settings.company_email });
	}

	render(profile) {
		const p = profile;
		const content_by_log_type = this.get_content_by_log_type();

		let activity_logs = (p.hub_seller_activity || []).sort((a, b) => {
			return new Date(b.creation) - new Date(a.creation);
		});

		const timeline_items_html = activity_logs
			.map(log => {
				const stats = JSON.parse(log.stats);
				const no_of_items = stats && stats.push_update || '';

				const content = content_by_log_type[log.type];
				const message = content.get_message(no_of_items);
				const icon = content.icon;
				return this.get_timeline_log_item(log.pretty_date, message, icon);
			})
			.join('');

		const profile_html = `<div class="hub-item-container">
			<div class="row visible-xs">
				<div class="col-xs-12 margin-bottom">
					<button class="btn btn-xs btn-default" data-route="marketplace/home">Back to home</button>
				</div>
			</div>
			<div class="row">
				<div class="col-md-3">
					<div class="hub-item-image">
						<img src="${p.logo}">
					</div>
				</div>
				<div class="col-md-6">
					<h2>${p.company}</h2>
					<div class="text-muted">
						<p>${p.country}</p>
						<p>${p.site_name}</p>
					</div>
					<hr>
					<div class="hub-item-description">
					${'description'
						? `<p>${p.company_description}</p>`
						: `<p>__('No description')</p`
					}
					</div>
				</div>
			</div>

			<div class="timeline">
				<div class="timeline-items">
					${timeline_items_html}
				</div>
			</div>

		</div>`;

		this.$wrapper.html(profile_html);
	}

	get_timeline_log_item(pretty_date, message, icon) {
		return `<div class="media timeline-item  notification-content">
			<div class="small">
				<i class="octicon ${icon} fa-fw"></i>
				<span title="Administrator"><b>${pretty_date}</b> ${message}</span>
			</div>
		</div>`;
	}

	get_content_by_log_type() {
		return {
			"Created": {
				icon: 'octicon-heart',
				get_message: () => 'Joined Marketplace'
			},
			"Items Publish": {
				icon: 'octicon-bookmark',
				get_message: (no_of_items) =>
					`Published ${no_of_items} product${no_of_items > 1 ? 's' : ''} to Marketplace`
			}
		}
	}
}

erpnext.hub.Publish = class Publish extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.items_to_publish = [];
		this.unpublished_items = [];
		this.fetched_items = [];
	}

	refresh() {
		if(!hub.settings.sync_in_progress) {
			this.make_publish_ready_state();
		} else {
			this.make_publish_in_progress_state();
		}
	}

	make_publish_ready_state() {
		this.$wrapper.empty();
		this.$wrapper.append(this.get_publishing_header());

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				this.search_value = keyword;
				this.get_items_and_render();
			},
			placeholder: __('Search Items')
		});

		this.setup_publishing_events();

		if(hub.settings.last_sync) {
			this.show_message(`Last sync was <a href="#marketplace/profile">${hub.settings.last_sync}</a>.
				<a href="#marketplace/my-products">See your Published Products</a>.`);
		}

		this.get_items_and_render();
	}

	get_publishing_header() {
		const title_html = `<b>${__('Select Products to Publish')}</b>`;

		const subtitle_html = `<p class="text-muted">
			${__(`Only products with an image, description and category can be published.
			Please update them if an item in your inventory does not appear.`)}
		</p>`;

		const publish_button_html = `<button class="btn btn-primary btn-sm publish-items">
			<i class="visible-xs octicon octicon-check"></i>
			<span class="hidden-xs">${__('Publish')}</span>
		</button>`;

		return $(`
			<div class='subpage-title flex'>
				<div>
					${title_html}
					${subtitle_html}
				</div>
				${publish_button_html}
			</div>
		`);
	}

	setup_publishing_events() {
		this.$wrapper.find('.publish-items').on('click', () => {
			this.publish_selected_items()
				.then(this.refresh.bind(this))
		});

		this.$wrapper.on('click', '.hub-card', (e) => {
			const $target = $(e.currentTarget);
			$target.toggleClass('active');

			// Get total items
			const total_items = this.$wrapper.find('.hub-card.active').length;

			let button_label;
			if (total_items > 0) {
				const more_than_one = total_items > 1;
				button_label = __('Publish {0} item{1}', [total_items, more_than_one ? 's' : '']);
			} else {
				button_label = __('Publish');
			}

			this.$wrapper.find('.publish-items')
				.text(button_label)
				.prop('disabled', total_items === 0);
		});
	}

	show_message(message) {
		const $message = $(`<div class="subpage-message">
			<p class="text-muted flex">
				<span>
					${message}
				</span>
				<i class="octicon octicon-x text-extra-muted"></i>
			</p>
		</div>`);

		$message.find('.octicon-x').on('click', () => {
			$message.remove();
		});

		this.$wrapper.prepend($message);
	}

	make_publish_in_progress_state() {
		this.$wrapper.empty();

		this.$wrapper.append(this.show_publish_progress());

		const subtitle_html = `<p class="text-muted">
			${__(`Only products with an image, description and category can be published.
			Please update them if an item in your inventory does not appear.`)}
		</p>`;

		this.$wrapper.append(subtitle_html);

		// Show search list with only desctiption, and don't set any events
		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				this.search_value = keyword;
				this.get_items_and_render();
			},
			placeholder: __('Search Items')
		});

		this.get_items_and_render();
	}

	show_publish_progress() {
		const items_to_publish = this.items_to_publish.length
			? this.items_to_publish
			: JSON.parse(hub.settings.custom_data);

		const $publish_progress = $(`<div class="sync-progress">
			<p><b>${__(`Syncing ${items_to_publish.length} Products`)}</b></p>
			<div class="progress">
				<div class="progress-bar" style="width: 12.875%"></div>
			</div>

		</div>`);

		const items_to_publish_container = $(get_item_card_container_html(
			items_to_publish, '', get_local_item_card_html));

		items_to_publish_container.find('.hub-card').addClass('active');

		$publish_progress.append(items_to_publish_container);

		return $publish_progress;
	}

	get_items_and_render(wrapper = this.$wrapper) {
		wrapper.find('.results').remove();
		const items = this.get_valid_items();

		if(!items.then) {
			this.render(items, wrapper);
		} else {
			items.then(r => {
				this.fetched_items = r.message;
				this.render(r.message, wrapper);
			});
		}
	}

	render(items, wrapper) {
		const items_container = $(get_item_card_container_html(items, '', get_local_item_card_html));
		items_container.addClass('results');
		wrapper.append(items_container);
	}

	get_valid_items() {
		if(this.unpublished_items.length) {
			return this.unpublished_items;
		}
		return frappe.call(
			'erpnext.hub_node.get_valid_items',
			{
				search_value: this.search_value
			}
		);
	}

	publish_selected_items() {
		const item_codes_to_publish = [];
		this.$wrapper.find('.hub-card.active').map(function () {
			item_codes_to_publish.push($(this).attr("data-id"));
		});

		this.unpublished_items = this.fetched_items.filter(item => {
			return !item_codes_to_publish.includes(item.item_code);
		});

		const items_to_publish = this.fetched_items.filter(item => {
			return item_codes_to_publish.includes(item.item_code);
		});
		this.items_to_publish = items_to_publish;

		return frappe.db.set_value("Hub Settings", "Hub Settings", {
			custom_data: JSON.stringify(items_to_publish),
			// sync_in_progress: 1
		}).then(() => {
			hub.settings.sync_in_progress = 1;
		})
		// .then(frappe.call(
		// 	'erpnext.hub_node.publish_selected_items',
		// 	{
		// 		items_to_publish: item_codes_to_publish
		// 	}
		// ));
	}
}

erpnext.hub.PublishedProducts = class PublishedProducts extends SubPage {
	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_published_products()
			.then(items => this.render(items));
	}

	refresh() {
		this.get_items_and_render();
	}

	render(items) {
		const items_container = $(get_item_card_container_html(items, __('Your Published Products')));
		this.$wrapper.append(items_container);
	}

	get_published_products() {
		return hub.call('get_items_by_seller', { hub_seller: hub.settings.company_email });
	}
}

erpnext.hub.NotFound = class NotFound extends SubPage {
	refresh() {
		this.$wrapper.html(get_empty_state(
			__('Sorry! I could not find what you were looking for.'),
			`<button class="btn btn-default btn-xs" data-route="marketplace/home">${__('Back to home')}</button>`
		));
	}
}

function get_empty_state(message, action) {
	return `<div class="empty-state flex align-center flex-column justify-center">
		<p class="text-muted">${message}</p>
		${action ? `<p>${action}</p>`: ''}
	</div>`;
}

function get_item_card_container_html(items, title='', get_item_html = get_item_card_html) {
	const items_html = (items || []).map(item => get_item_html(item)).join('');
	const title_html = title
		? `<div class="col-sm-12 margin-bottom">
				<b>${title}</b>
			</div>`
		: '';

	const html = `<div class="row hub-card-container">
		${title_html}
		${items_html}
	</div>`;

	return html;
}

function get_item_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);
	const img_url = item.image;
	const company_name = item.company;

	// Subtitle
	let subtitle = [comment_when(item.creation)];
	const rating = item.average_rating;
	if (rating > 0) {
		subtitle.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
	}
	subtitle.push(company_name);

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6">
			<div class="hub-card" data-route="marketplace/item/${item.hub_item_code}">
				<div class="hub-card-header">
					<div class="hub-card-title ellipsis bold">${title}</div>
					<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
				</div>
				<div class="hub-card-body">
					<img class="hub-card-image" src="${img_url}" />
					<div class="overlay hub-card-overlay"></div>
				</div>
			</div>
		</div>
	`;

	return item_html;
}

function get_local_item_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);
	const img_url = item.image;
	const company_name = item.company;

	const is_active = item.publish_in_hub;
	const id = item.hub_item_code || item.item_code;

	// Subtitle
	let subtitle = [comment_when(item.creation)];
	const rating = item.average_rating;
	if (rating > 0) {
		subtitle.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
	}
	subtitle.push(company_name);

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	const edit_item_button = `<div class="hub-card-overlay-button" style="right: 15px; bottom: 15px;" data-route="Form/Item/${item.item_name}">
		<button class="btn btn-default zoom-view">
			<i class="octicon octicon-pencil text-muted"></i>
		</button>
	</div>`;

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6">
			<div class="hub-card is-local ${is_active ? 'active' : ''}" data-id="${id}">
				<div class="hub-card-header">
					<div class="hub-card-title ellipsis bold">${title}</div>
					<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					<i class="octicon octicon-check text-success"></i>
				</div>
				<div class="hub-card-body">
					<img class="hub-card-image" src="${img_url}" />
					<div class="hub-card-overlay">
						<div class="hub-card-overlay-body">
							${edit_item_button}
						</div>
					</div>
				</div>
			</div>
		</div>
	`;

	return item_html;
}


function get_rating_html(rating) {
	let rating_html = ``;
	for (var i = 0; i < 5; i++) {
		let star_class = 'fa-star';
		if (i >= rating) star_class = 'fa-star-o';
		rating_html += `<i class='fa fa-fw ${star_class} star-icon' data-index=${i}></i>`;
	}
	return rating_html;
}

function make_search_bar({wrapper, on_search, placeholder = __('Search for anything')}) {
	const $search = $(`
		<div class="hub-search-container">
			<input type="text" class="form-control" placeholder="${placeholder}">
		</div>`
	);
	wrapper.append($search);
	const $search_input = $search.find('input');

	$search_input.on('keydown', frappe.utils.debounce((e) => {
		if (e.which === frappe.ui.keyCode.ENTER) {
			const search_value = $search_input.val();
			on_search(search_value);
		}
	}, 300));
}

// caching

erpnext.hub.cache = {};
hub.call = function call_hub_method(method, args={}) {
	return new Promise((resolve, reject) => {

		// cache
		const key = method + JSON.stringify(args);
		if (erpnext.hub.cache[key]) {
			resolve(erpnext.hub.cache[key]);
		}

		// cache invalidation after 5 minutes
		const timeout = 5 * 60 * 1000;

		setTimeout(() => {
			delete erpnext.hub.cache[key];
		}, timeout);

		frappe.call({
			method: 'erpnext.hub_node.call_hub_method',
			args: {
				method,
				params: args
			}
		})
		.then(r => {
			if (r.message) {
				if (r.message.error) {
					frappe.throw({
						title: __('Marketplace Error'),
						message: r.message.error
					});
				}

				erpnext.hub.cache[key] = r.message;
				resolve(r.message)
			}
			reject(r)
		})
		.fail(reject)
	});
}
