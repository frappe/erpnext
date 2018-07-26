frappe.provide('erpnext.hub');

erpnext.hub.Marketplace = class Marketplace {
	constructor({ parent }) {
		this.$parent = $(parent);
		this.page = parent.page;

		frappe.db.get_doc('Hub Settings')
			.then(doc => {
				this.hub_settings = doc;
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

			e.stopPropagation();
		});
	}

	make_sidebar() {
		this.$sidebar = this.$parent.find('.layout-side-section').addClass('hidden-xs');

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

		this.$sidebar.append(`
			<ul class="list-unstyled hub-sidebar-group">
				<li class="hub-sidebar-item" data-route="marketplace/home">
					${__('Browse')}
				</li>
				<li class="hub-sidebar-item" data-route="marketplace/favourites">
					${__('Favorites')}
				</li>
				${user_specific_items_html}
			</ul>
		`);

		this.make_sidebar_categories();
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

		if (route[1] === 'category' && route[2] && !this.subpages.category) {
			this.subpages.category = new erpnext.hub.Category(this.$body);
		}

		if (route[1] === 'item' && route[2] && !this.subpages.item) {
			this.subpages.item = new erpnext.hub.Item(this.$body);
		}

		if (route[1] === 'register' && !this.subpages.register) {
			this.subpages.register = new erpnext.hub.Register(this.$body);
		}

		if (route[1] === 'publish' && !this.subpages.publish) {
			this.subpages.publish = new erpnext.hub.Publish(this.$body);
		}


		if (!Object.keys(this.subpages).includes(route[1])) {
			frappe.show_not_found();
			return;
		}

		this.update_sidebar();
		frappe.utils.scroll_to(0);
		this.subpages[route[1]].show();
	}
}

class SubPage {
	constructor(parent) {
		this.$parent = $(parent);
		this.make_wrapper();
	}

	make_wrapper() {
		const page_name = frappe.get_route()[1];
		this.$wrapper = $(`<div class="marketplace-page" data-page-name="${page_name}">`).appendTo(this.$parent);
		this.hide();
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
		this.make_search_bar();
	}

	refresh() {
		this.get_items_and_render();
	}

	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_items()
			.then(r => {
				erpnext.hub.hub_item_cache = r.message;
				this.render(r.message);
			});
	}

	get_items() {
		return frappe.call('erpnext.hub_node.get_list', {
			doctype: 'Hub Item',
			filters: {
				image: ['like', 'http%']
			}
		});
	}

	make_search_bar() {
		const $search = $(`
			<div class="hub-search-container">
				<input type="text" class="form-control" placeholder="Search for anything">
			</div>`
		);
		this.$wrapper.append($search);
		const $search_input = $search.find('input');

		$search_input.on('keydown', frappe.utils.debounce((e) => {
			if (e.which === frappe.ui.keyCode.ENTER) {
				this.search_value = $search_input.val();
				this.get_items_and_render();
			}
		}, 300));
	}

	render(items) {
		const html = get_item_card_container_html(items, __('Recently Published'));
		this.$wrapper.append(html)
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

erpnext.hub.Item = class Item extends SubPage {
	refresh() {
		this.hub_item_code = frappe.get_route()[2];

		this.get_item(this.hub_item_code)
			.then(item => {
				this.render(item);
			});
	}

	get_item(hub_item_code) {
		return new Promise(resolve => {
			const item = (erpnext.hub.hub_item_cache || []).find(item => item.name === hub_item_code)

			if (item) {
				resolve(item);
			} else {
				frappe.call('erpnext.hub_node.get_list', {
					doctype: 'Hub Item',
					filters: {
						name: hub_item_code
					}
				})
				.then(r => {
					resolve(r.message[0]);
				});
			}
		});
	}

	render(item) {
		const title = item.item_name || item.name;
		const company = item.company_name;

		const who = __('Posted By {0}', [company]);
		const when = comment_when(item.creation);

		const city = item.seller_city ? item.seller_city + ', ' : '';
		const country = item.country ? item.country : '';
		const where = `${city}${country}`;

		const dot_spacer = '<span aria-hidden="true"> · </span>';

		const description = item.description || '';

		const rating_html = get_rating_html(item);
		const rating_count = item.reviews.length > 0 ? `(${item.reviews.length} reviews)` : '';

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
					<div class="col-md-6">
						<h2>${title}</h2>
						<div class="text-muted">
							<p>${where}${dot_spacer}${when}</p>
							<p>${rating_html}${rating_count}</p>
						</div>
						<hr>
						<div class="hub-item-description">
						${description ?
							`<b>${__('Description')}</b>
							<p>${description}</p>
							` : __('No description')
						}
						</div>
					</div>
				</div>
				<div class="row hub-item-seller">
					<div class="col-md-12 margin-top margin-bottom">
						<b class="text-muted">Seller Information</b>
					</div>
					<div class="col-md-1">
						<img src="https://picsum.photos/200">
					</div>
					<div class="col-md-6">
						<a href="#marketplace/seller/${company}" class="bold">${company}</a>
						<p class="text-muted">
							Contact Seller
						</p>
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

		this.make_review_area();
		this.render_reviews(item);
	}

	make_review_area() {
		this.comment_area = new frappe.ui.ReviewArea({
			parent: this.$wrapper.find('.timeline-head').empty(),
			mentions: [],
			on_submit: (val) => {
				val.user = frappe.session.user;
				val.username = frappe.session.user_fullname;

				frappe.call({
					method: 'erpnext.hub_node.send_review',
					args: {
						hub_item_code: this.hub_item_code,
						review: val
					},
					callback: (r) => {
						console.log(r);
						this.render_reviews(r.message);
						this.comment_area.reset();
					},
					freeze: true
				});
			}
		});
	}

	render_reviews(item) {
		this.$wrapper.find('.timeline-items').empty();
		item.reviews.forEach(review => this.render_review(review, item));
	}

	render_review(review, item) {
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

		let rating_html = get_rating_html(item);

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

		this.$form_container.find('.form-column').append(`
			<div class="text-right">
				<button type="submit" class="btn btn-primary btn-register btn-sm">${__('Submit')}</button>
			</div>
		`);

		this.$form_container.find('.form-message').removeClass('hidden small').addClass('h4').text(__('Become a Seller'))

		this.$form_container.on('click', '.btn-register', () => {
			const form_values = this.field_group.get_values();
			frappe.call('erpnext.hub_node.doctype.hub_settings.hub_settings.register_seller', form_values)
				.then(() => {
					// Reload page and things ... but for now
					frappe.msgprint('Registered successfully.');
				});
		});
	}
}

erpnext.hub.Publish = class Publish extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		const title_html = `<b>${__('Select Products to Publish')}</b>`;
		const info = `<p class="text-muted">${__("Status decided by the 'Publish in Hub' field in Item.")}</p>`;
		const subtitle_html = `
		<p class="text-muted">
			${__(`Only products with an image, description and category can be published.
			Please update them if an item in your inventory does not appear.`)}
		</p>`;
		const publish_button_html = `<button class="btn btn-primary btn-sm publish-items">
			<i class="visible-xs octicon octicon-check"></i>
			<span class="hidden-xs">Publish</span>
		</button>`;

		const select_all_button = `<button class="btn btn-secondary btn-default btn-xs margin-right select-all">Select All</button>`;
		const deselect_all_button = `<button class="btn btn-secondary btn-default btn-xs deselect-all">Deselect All</button>`;

		const search_html = `<div class="hub-search-container">
			<input type="text" class="form-control" placeholder="Search Items">
		</div>`;

		const subpage_header = $(`
			<div class='subpage-title flex'>
				<div>
					${title_html}
					${subtitle_html}
				</div>
				${publish_button_html}
			</div>

			${search_html}

			${select_all_button}
			${deselect_all_button}
		`);

		this.$wrapper.append(subpage_header);

		this.setup_events();
	}

	setup_events() {
		this.$wrapper.find('.select-all').on('click', () => {
			this.$wrapper.find('.hub-card').addClass('active');
		});

		this.$wrapper.find('.deselect-all').on('click', () => {
			this.$wrapper.find('.hub-card').removeClass('active');
		});

		this.$wrapper.find('.publish-items').on('click', () => {
			this.publish_selected_items()
				.then(r => {
					frappe.msgprint('check');
				});
		});

		const $search_input = this.$wrapper.find('.hub-search-container input');
		this.search_value = '';

		$search_input.on('keydown', frappe.utils.debounce((e) => {
			if (e.which === frappe.ui.keyCode.ENTER) {
				this.search_value = $search_input.val();
				this.get_items_and_render();
			}
		}, 300));
	}

	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_valid_items()
			.then(r => {
				this.render(r.message);
			});
	}

	refresh() {
		this.get_items_and_render();
	}

	render(items) {
		const items_container = $(get_item_card_container_html(items));
		items_container.addClass('static').on('click', '.hub-card', (e) => {
			const $target = $(e.currentTarget);
			$target.toggleClass('active');
		});

		this.$wrapper.append(items_container);
	}

	get_valid_items() {
		return frappe.call(
			'erpnext.hub_node.get_valid_items',
			{
				search_value: this.search_value
			}
		);
	}

	publish_selected_items() {
		const items_to_publish = [];
		const items_to_unpublish = [];
		this.$wrapper.find('.hub-card').map(function () {
			const active = $(this).hasClass('active');

			if(active) {
				items_to_publish.push($(this).attr("data-id"));
			} else {
				items_to_unpublish.push($(this).attr("data-id"));
			}
		});

		return frappe.call(
			'erpnext.hub_node.publish_selected_items',
			{
				items_to_publish: items_to_publish,
				items_to_unpublish: items_to_unpublish
			}
		);
	}
}

function get_item_card_container_html(items, title='') {
	const items_html = (items || []).map(item => get_item_card_html(item)).join('');

	const html = `<div class="row hub-card-container">
		<div class="col-sm-12 margin-bottom">
			<b>${title}</b>
		</div>
		${items_html}
	</div>`;

	return html;
}

function get_item_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);
	const img_url = item.image;

	const company_name = item.company_name;

	const active = item.publish_in_hub;

	const id = item.hub_item_code || item.item_code;

	// Subtitle
	let subtitle = [comment_when(item.creation)];
	const rating = get_rating(item);
	if (rating > 0) {
		subtitle.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
	}
	subtitle.push(company_name);

	let dot_spacer = '<span aria-hidden="true"> · </span>';
	subtitle = subtitle.join(dot_spacer);

	// Decide item link
	const isLocal = item.source_type === "local";
	const route = !isLocal
		? `marketplace/item/${item.hub_item_code}`
		: `Form/Item/${item.item_name}`;

	const card_route = isLocal ? '' : `data-route='${route}'`;

	const show_local_item_button = isLocal
		? `<div class="overlay button-overlay" data-route='${route}' onclick="event.preventDefault();">
				<button class="btn btn-default zoom-view">
					<i class="octicon octicon-eye"></i>
				</button>
			</div>`
		: '';

	const item_html = `
		<div class="col-md-3 col-sm-4 col-xs-6">
			<div class="hub-card ${active ? 'active' : ''}" ${card_route} data-id="${id}">
				<div class="hub-card-header">
					<div class="title">
						<div class="hub-card-title ellipsis bold">${title}</div>
						<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					</div>
					<i class="octicon octicon-check text-success"></i>
				</div>
				<div class="hub-card-body">
					<img class="hub-card-image ${item.image ? '' : 'no-image'}" src="${img_url}" />
					<div class="overlay hub-card-overlay"></div>
					${show_local_item_button}
				</div>
			</div>
		</div>
	`;

	return item_html;
}

function get_rating(item) {
	const review_length = (item.reviews || []).length;
	return review_length
		? item.reviews
			.map(r => r.rating)
			.reduce((a, b) => a + b, 0) / review_length
		: 0;
}

function get_rating_html(item) {
	const rating = get_rating(item);
	let rating_html = ``;
	for (var i = 0; i < 5; i++) {
		let star_class = 'fa-star';
		if (i >= rating) star_class = 'fa-star-o';
		rating_html += `<i class='fa fa-fw ${star_class} star-icon' data-index=${i}></i>`;
	}
	return rating_html;
}

erpnext.hub.HubListing = class HubListing extends frappe.views.BaseList {
	setup_defaults() {
		super.setup_defaults();
		this.page_title = __('');
		this.method = 'erpnext.hub_node.get_list';

		this.cache = {};

		const route = frappe.get_route();
		this.page_name = route[1];

		this.menu_items = this.menu_items.concat(this.get_menu_items());

		this.imageFieldName = 'image';

		this.show_filters = 0;
	}

	set_title() {
		const title = this.page_title;
		let iconHtml = `<img class="hub-icon" src="assets/erpnext/images/hub_logo.svg">`;
		let titleHtml = `<span class="hub-page-title">${title}</span>`;
		this.page.set_title(titleHtml, '', false, title);
	}

	setup_fields() {
		return this.get_meta()
			.then(r => {
				this.meta = r.message.meta || this.meta;
				frappe.model.sync(this.meta);
				this.bootstrap_data(r.message);

				this.prepareFormFields();
			});
	}

	setup_filter_area() { }

	get_meta() {
		return new Promise(resolve =>
			frappe.call('erpnext.hub_node.get_meta', { doctype: this.doctype }, resolve));
	}

	set_breadcrumbs() { }

	prepareFormFields() { }

	bootstrap_data() { }

	get_menu_items() {
		const items = [
			{
				label: __('Hub Settings'),
				action: () => frappe.set_route('Form', 'Hub Settings'),
				standard: true
			},
			{
				label: __('Favourites'),
				action: () => frappe.set_route('Hub', 'Favourites'),
				standard: true
			}
		];

		return items;
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});
	}

	setup_sort_selector() {
		// this.sort_selector = new frappe.ui.SortSelector({
		// 	parent: this.filter_area.$filter_list_wrapper,
		// 	doctype: this.doctype,
		// 	args: this.order_by,
		// 	onchange: () => this.refresh(true)
		// });
	}

	setup_view() {
		if (frappe.route_options) {
			const filters = [];
			for (let field in frappe.route_options) {
				var value = frappe.route_options[field];
				this.page.fields_dict[field].set_value(value);
			}
		}

		const $hub_search = $(`
			<div class="hub-search-container">
				<input type="text" class="form-control" placeholder="Search for anything">
			</div>`
		);
		this.$frappe_list.prepend($hub_search);
		const $search_input = $hub_search.find('input');

		$search_input.on('keydown', frappe.utils.debounce((e) => {
			if (e.which === frappe.ui.keyCode.ENTER) {
				this.search_value = $search_input.val();
				this.refresh();
			}
		}, 300));
	}

	get_args() {
		return {
			doctype: this.doctype,
			start: this.start,
			limit: this.page_length,
			order_by: this.order_by,
			// fields: this.fields,
			filters: this.get_filters_for_args()
		};
	}

	update_data(r) {
		const data = r.message;

		if (this.start === 0) {
			this.data = data;
		} else {
			this.data = this.data.concat(data);
		}

		this.data_dict = {};
	}

	freeze(toggle) { }

	render() {
		this.data_dict = {};
		this.render_image_view();

		this.setup_quick_view();
		this.setup_like();
	}

	render_offline_card() {
		let html = `<div class='page-card'>
			<div class='page-card-head'>
				<span class='indicator red'>
					{{ _("Payment Cancelled") }}</span>
			</div>
			<p>${ __("Your payment is cancelled.")}</p>
			<div><a href='' class='btn btn-primary btn-sm'>
				${ __("Continue")}</a></div>
		</div>`;

		let page = this.page.wrapper.find('.layout-side-section')
		page.append(html);

		return;
	}

	render_image_view() {
		var html = this.data.map(this.item_html.bind(this)).join("");

		if (this.start === 0) {
			// ${this.getHeaderHtml()}
			this.$result.html(`
				<div class="row hub-card-container">
					<div class="col-md-12 margin-bottom">
						<b>Recently Published</b>
					</div>
					${html}
				</div>
			`);
		}

		if (this.data.length) {
			this.doc = this.data[0];
		}

		this.data.map(this.loadImage.bind(this));

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}

	getHeaderHtml(title, image, content) {
		// let company_html =
		return `
			<header class="list-row-head text-muted small">
				<div style="display: flex;">
					<div class="list-header-icon">
						<img title="${title}" alt="${title}" src="${image}">
					</div>
					<div class="list-header-info">
						<h5>
							${title}
						</h5>
						<span class="margin-vertical-10 level-item">
							${content}
						</span>
					</div>
				</div>
			</header>
		`;
	}

	renderHeader() {
		return ``;
	}

	get_image_html(encoded_name, src, alt_text) {
		return `<img data-name="${encoded_name}" src="${src}" alt="${alt_text}">`;
	}

	get_image_placeholder(title) {
		return `<span class="placeholder-text">${frappe.get_abbr(title)}</span>`;
	}

	loadImage(item) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);

		let placeholder = this.get_image_placeholder(title);
		let $container = this.$result.find(`.image-field[data-name="${encoded_name}"]`);

		if (!item[this.imageFieldName]) {
			$container.prepend(placeholder);
			$container.addClass('no-image');
		}

		frappe.load_image(item[this.imageFieldName],
			(imageObj) => {
				$container.prepend(imageObj)
			},
			() => {
				$container.prepend(placeholder);
				$container.addClass('no-image');
			},
			(imageObj) => {
				imageObj.title = encoded_name;
				imageObj.alt = title;
			}
		)
	}

	setup_quick_view() {
		if (this.quick_view) return;

		this.quick_view = new frappe.ui.Dialog({
			title: 'Quick View',
			fields: this.formFields
		});
		this.quick_view.set_primary_action(__('Request a Quote'), () => {
			this.show_rfq_modal()
				.then(values => {
					item.item_code = values.item_code;
					delete values.item_code;

					const supplier = values;
					return [item, supplier];
				})
				.then(([item, supplier]) => {
					return this.make_rfq(item, supplier, this.page.btn_primary);
				})
				.then(r => {
					console.log(r);
					if (r.message && r.message.rfq) {
						this.page.btn_primary.addClass('disabled').html(`<span><i class='fa fa-check'></i> ${__('Quote Requested')}</span>`);
					} else {
						throw r;
					}
				})
				.catch((e) => {
					console.log(e); //eslint-disable-line
				});
		}, 'octicon octicon-plus');

		this.$result.on('click', '.btn.zoom-view', (e) => {
			e.preventDefault();
			e.stopPropagation();
			var name = $(e.target).attr('data-name');
			name = decodeURIComponent(name);

			this.quick_view.set_title(name);
			let values = this.data_dict[name];
			this.quick_view.set_values(values);

			let fields = [];

			this.quick_view.show();

			return false;
		});
	}

	setup_like() {
		if (this.setup_like_done) return;
		this.setup_like_done = 1;
		this.$result.on('click', '.btn.like-button', (e) => {
			if ($(e.target).hasClass('changing')) return;
			$(e.target).addClass('changing');

			e.preventDefault();
			e.stopPropagation();

			var name = $(e.target).attr('data-name');
			name = decodeURIComponent(name);
			let values = this.data_dict[name];

			let heart = $(e.target);
			if (heart.hasClass('like-button')) {
				heart = $(e.target).find('.octicon');
			}

			let remove = 1;

			if (heart.hasClass('liked')) {
				// unlike
				heart.removeClass('liked');
			} else {
				// like
				remove = 0;
				heart.addClass('liked');
			}

			frappe.call({
				method: 'erpnext.hub_node.update_wishlist_item',
				args: {
					item_name: values.hub_item_code,
					remove: remove
				},
				callback: (r) => {
					let message = __("Added to Favourites");
					if (remove) {
						message = __("Removed from Favourites");
					}
					frappe.show_alert(message);
				},
				freeze: true
			});

			$(e.target).removeClass('changing');
			return false;
		});
	}
}

erpnext.hub.ItemListing = class ItemListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.page_title = __('Marketplace');
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name', 'description', 'country'];
		this.filters = [];
	}

	render() {
		this.data_dict = {};
		this.render_image_view();

		this.setup_quick_view();
		this.setup_like();
	}

	bootstrap_data(response) {
		// let companies = response.companies.map(d => d.name);
		// this.custom_filter_configs = [
		// 	{
		// 		fieldtype: 'Autocomplete',
		// 		label: __('Select Company'),
		// 		condition: 'like',
		// 		fieldname: 'company_name',
		// 		options: companies
		// 	},
		// 	{
		// 		fieldtype: 'Link',
		// 		label: __('Select Country'),
		// 		options: 'Country',
		// 		condition: 'like',
		// 		fieldname: 'country'
		// 	}
		// ];
	}

	prepareFormFields() {
		let fieldnames = ['item_name', 'description', 'company_name', 'country'];
		this.formFields = this.meta.fields
			.filter(field => fieldnames.includes(field.fieldname))
			.map(field => {
				let {
					label,
					fieldname,
					fieldtype,
				} = field;
				let read_only = 1;
				return {
					label,
					fieldname,
					fieldtype,
					read_only,
				};
			});

		this.formFields.unshift({
			label: 'image',
			fieldname: 'image',
			fieldtype: 'Attach Image'
		});
	}

	setup_side_bar() {
		super.setup_side_bar();

		this.setup_new_sidebar();

		return;

		let $pitch = $(`<div class="border" style="
				margin-top: 10px;
				padding: 0px 10px;
				border-radius: 3px;
			">
			<h5>Sell on HubMarket</h5>
			<p>Over 2000 products listed. Register your company to start selling.</p>
		</div>`);

		this.sidebar.$sidebar.append($pitch);

		this.category_tree = new frappe.ui.Tree({
			parent: this.sidebar.$sidebar,
			label: 'All Categories',
			expandable: true,

			args: { parent: this.current_category },
			method: 'erpnext.hub_node.get_categories',
			on_click: (node) => {
				this.update_category(node.label);
			}
		});

		this.sidebar.add_item({
			label: __('Companies'),
			on_click: () => frappe.set_route('Hub', 'Company')
		}, undefined, true);

		this.sidebar.add_item({
			label: this.hub_settings.company,
			on_click: () => frappe.set_route('Form', 'Company', this.hub_settings.company)
		}, __("Account"));

		this.sidebar.add_item({
			label: __("Favourites"),
			on_click: () => frappe.set_route('Hub', 'Favourites')
		}, __("Account"));

		this.sidebar.add_item({
			label: __("Settings"),
			on_click: () => frappe.set_route('Form', 'Hub Settings')
		}, __("Account"));
	}

	setup_new_sidebar() {
		this.sidebar.$sidebar.append(`
			<ul class="list-unstyled hub-sidebar-group">
				<li class="hub-sidebar-item bold active">
					Browse
				</li>
				<li class="hub-sidebar-item text-muted">
					Favorites
				</li>
				<li class="hub-sidebar-item text-muted">
					Become a seller
				</li>
			</ul>
		`);

		frappe.call('erpnext.hub_node.get_categories')
			.then(r => {
				const categories = r.message.map(d => d.value).sort();
				const sidebar_items = [
					`<li class="hub-sidebar-item bold text-muted is-title">
						${__('Category')}
					</li>`,
					`<li class="hub-sidebar-item active">
						All
					</li>`,
					...categories.map(category => `
						<li class="hub-sidebar-item text-muted">
							${category}
						</li>
					`)
				];

				this.sidebar.$sidebar.append(`
					<ul class="list-unstyled">
						${sidebar_items.join('')}
					</ul>
				`);
			});
	}

	update_category(label) {
		this.current_category = (label == 'All Categories') ? undefined : label;
		this.refresh();
	}

	get_filters_for_args() {
		const filter = {};

		if (this.search_value) {
			filter.item_name = ['like', `%${this.search_value}%`];
		}

		filter.image = ['like', 'http%'];
		return filter;

		// if(!this.filter_area) return;
		// let filters = {};
		// this.filter_area.get().forEach(f => {
		// 	let field = f[1] !== 'name' ? f[1] : 'item_name';
		// 	filters[field] = [f[2], f[3]];
		// });
		// if(this.current_category) {
		// 	filters['hub_category'] = this.current_category;
		// }
		// return filters;
	}

	update_data(r) {
		super.update_data(r);

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}

	item_html(item, index) {
		item._name = encodeURI(item.name);
		const encoded_name = item._name;
		const title = strip_html(item[this.meta.title_field || 'name']);

		const img_url = item[this.imageFieldName];
		const no_image = !img_url;
		const _class = no_image ? 'no-image' : '';
		const route = `#Hub/Item/${item.hub_item_code}`;
		const company_name = item['company_name'];

		const reviewLength = (item.reviews || []).length;
		const ratingAverage = reviewLength
			? item.reviews
				.map(r => r.rating)
				.reduce((a, b) => a + b, 0) / reviewLength
			: -1;

		let ratingHtml = ``;

		for (var i = 0; i < 5; i++) {
			let starClass = 'fa-star';
			if (i >= ratingAverage) starClass = 'fa-star-o';
			ratingHtml += `<i class='fa fa-fw ${starClass} star-icon' data-index=${i}></i>`;
		}
		let dot_spacer = '<span aria-hidden="true"> · </span>';
		let subtitle = '';
		subtitle += comment_when(item.creation);
		subtitle += dot_spacer;

		if (ratingAverage > 0) {
			subtitle += ratingAverage + `<i class='fa fa-fw fa-star-o'></i>`;
			subtitle += dot_spacer;
		}
		subtitle += company_name;

		let item_html = `
			<div class="col-sm-3 col-xs-2">
				<div class="hub-card">
					<div class="hub-card-header">
						<div class="list-row-col list-subject ellipsis level">
							<span class="level-item bold ellipsis" title="McGuffin">
								<a href="${route}">${title}</a>
							</span>
						</div>
						<div class="text-muted small" style="margin: 5px 0px;">
							${ratingHtml}
							(${reviewLength})
						</div>
						<div class="list-row-col">
							<a href="${'#Hub/Company/' + company_name + '/Items'}"><p>${company_name}</p></a>
						</div>
					</div>
					<div class="hub-card-body">
						<a  data-name="${encoded_name}"
							title="${encoded_name}"
							href="${route}"
						>
							<div class="image-field ${_class}"
								data-name="${encoded_name}"
							>
								<button class="btn btn-default zoom-view" data-name="${encoded_name}">
									<i class="octicon octicon-eye" data-name="${encoded_name}"></i>
								</button>
								<button class="btn btn-default like-button" data-name="${encoded_name}">
									<i class="octicon octicon-heart" data-name="${encoded_name}"></i>
								</button>
							</div>
						</a>
					</div>
				</div>
			</div>
		`;

		item_html = `
			<div class="col-md-3 col-sm-4 col-xs-6">
				<div class="hub-card">
					<div class="hub-card-header">
						<div class="hub-card-title ellipsis bold">${title}</div>
						<div class="hub-card-subtitle ellipsis text-muted">${subtitle}</div>
					</div>
					<div class="hub-card-body">
						<img class="hub-card-image ${no_image ? 'no-image' : ''}" src="${img_url}" />
					</div>
				</div>
			</div>
		`;

		return item_html;
	}

};

erpnext.hub.Favourites2 = class Favourites extends erpnext.hub.ItemListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Item';
		this.page_title = __('Favourites');
		this.fields = ['name', 'hub_item_code', 'image', 'item_name', 'item_code', 'company_name', 'description', 'country'];
		this.filters = [];
		this.method = 'erpnext.hub_node.get_item_favourites';
	}

	setup_filter_area() { }

	setup_sort_selector() { }

	// setupHe

	getHeaderHtml() {
		return '';
	}

	get_args() {
		return {
			start: this.start,
			limit: this.page_length,
			order_by: this.order_by,
			fields: this.fields
		};
	}

	bootstrap_data(response) { }

	prepareFormFields() { }

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});

		this.sidebar.add_item({
			label: __('Back to Products'),
			on_click: () => frappe.set_route('Hub', 'Item')
		});
	}

	update_category(label) {
		this.current_category = (label == 'All Categories') ? undefined : label;
		this.refresh();
	}

	get_filters_for_args() {
		if (!this.filter_area) return;
		let filters = {};
		this.filter_area.get().forEach(f => {
			let field = f[1] !== 'name' ? f[1] : 'item_name';
			filters[field] = [f[2], f[3]];
		});
		if (this.current_category) {
			filters['hub_category'] = this.current_category;
		}
		return filters;
	}

	update_data(r) {
		super.update_data(r);

		this.data_dict = {};
		this.data.map(d => {
			this.data_dict[d.hub_item_code] = d;
		});
	}
};

erpnext.hub.CompanyListing = class CompanyListing extends erpnext.hub.HubListing {
	constructor(opts) {
		super(opts);
		this.show();
	}

	render() {
		this.data_dict = {};
		this.render_image_view();
	}

	setup_defaults() {
		super.setup_defaults();
		this.doctype = 'Hub Company';
		this.page_title = __('Companies');
		this.fields = ['company_logo', 'name', 'site_name', 'seller_city', 'seller_description', 'seller', 'country', 'company_name'];
		this.filters = [];
		this.custom_filter_configs = [
			{
				fieldtype: 'Link',
				label: 'Country',
				options: 'Country',
				condition: 'like',
				fieldname: 'country'
			}
		];
		this.imageFieldName = 'company_logo';
	}

	setup_side_bar() {
		this.sidebar = new frappe.ui.Sidebar({
			wrapper: this.page.wrapper.find('.layout-side-section'),
			css_class: 'hub-sidebar'
		});

		this.sidebar.add_item({
			label: __('Back to Products'),
			on_click: () => frappe.set_route('Hub', 'Item')
		});
	}

	get_filters_for_args() {
		let filters = {};
		// this.filter_area.get().forEach(f => {
		// 	let field = f[1] !== 'name' ? f[1] : 'company_name';
		// 	filters[field] = [f[2], f[3]];
		// });
		return filters;
	}

	item_html(company) {
		company._name = encodeURI(company.company_name);
		const encoded_name = company._name;
		const title = strip_html(company.company_name);
		const _class = !company[this.imageFieldName] ? 'no-image' : '';
		const company_name = company['company_name'];
		const route = `#Hub/Company/${company_name}`;

		let image_html = company.company_logo ?
			`<img src="${company.company_logo}"><span class="helper"></span>` :
			`<div class="standard-image">${frappe.get_abbr(company.company_name)}</div>`;

		let item_html = `
			<div class="image-view-item">
				<div class="image-view-header">
					<div class="list-row-col list-subject ellipsis level">
						<span class="level-item bold ellipsis" title="McGuffin">
							<a href="${route}">${title}</a>
						</span>
					</div>
				</div>
				<div class="image-view-body">
					<a  data-name="${encoded_name}"
						title="${encoded_name}"
						href="${route}">
						<div class="image-field ${_class}"
							data-name="${encoded_name}">
						</div>
					</a>
				</div>

			</div>
		`;

		return item_html;
	}

};
