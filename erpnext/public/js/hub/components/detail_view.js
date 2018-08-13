function get_detail_view_html(item, allow_edit) {
	const title = item.item_name || item.name;
	const seller = item.company;

	const who = __('Posted By {0}', [seller]);
	const when = comment_when(item.creation);

	const city = item.city ? item.city + ', ' : '';
	const country = item.country ? item.country : '';
	const where = `${city}${country}`;

	const dot_spacer = '<span aria-hidden="true"> · </span>';

	const description = item.description || '';

	let stats = __('No views yet');
	if(item.view_count) {
		const views_message = __(`${item.view_count} Views`);

		const rating_html = get_rating_html(item.average_rating);
		const rating_count = item.no_of_ratings > 0 ? `${item.no_of_ratings} reviews` : __('No reviews yet');

		stats = `${views_message}${dot_spacer}${rating_html} (${rating_count})`;
	}


	let menu_items = '';

	if(allow_edit) {
		menu_items = `
			<li><a data-action="edit_details">${__('Edit Details')}</a></li>
			<li><a data-action="unpublish_item">${__('Unpublish')}</a></li>`;
	} else {
		menu_items = `
			<li><a data-action="report_item">${__('Report this item')}</a></li>
		`;
	}

	const html = `
		<div class="hub-item-container">
			<div class="row visible-xs">
				<div class="col-xs-12 margin-bottom">
					<button class="btn btn-xs btn-default" data-route="marketplace/home">${__('Back to home')}</button>
				</div>
			</div>
			<div class="row detail-page-section margin-bottom">
				<div class="col-md-3">
					<div class="hub-item-image">
						<img src="${item.image}">
					</div>
				</div>
				<div class="col-md-8 flex flex-column">
					<div class="detail-page-header">
						<h2>${title}</h2>
						<div class="text-muted">
							<p>${where}${dot_spacer}${when}</p>
							<p>${stats}</p>
						</div>
					</div>

					<div class="page-actions detail-page-actions">
						<button class="btn btn-default text-muted favourite-button" data-action="add_to_favourites">
							${__('Add to Favourites')} <i class="octicon octicon-heart text-extra-muted"></i>
						</button>
						<button class="btn btn-primary" data-action="contact_seller">
							${__('Contact Seller')}
						</button>
					</div>
				</div>
				<div class="col-md-1">
					<div class="dropdown pull-right hub-item-dropdown">
						<a class="dropdown-toggle btn btn-xs btn-default" data-toggle="dropdown">
							<span class="caret"></span>
						</a>
						<ul class="dropdown-menu dropdown-right" role="menu">
							${menu_items}
						</ul>
					</div>
				</div>
			</div>
			<div class="row hub-item-description">
				<h6 class="col-md-12 margin-top">
					<b class="text-muted">Product Description</b>
				</h6>
				<p class="col-md-12">
					${description ? description : __('No details')}
				</p>
			</div>
			<div class="row hub-item-seller">

				<h6 class="col-md-12 margin-top margin-bottom">
					<b class="text-muted">Seller Information</b>
				</h6>
				<div class="col-md-1">
					<img src="https://picsum.photos/200">
				</div>
				<div class="col-md-8">
					<div class="margin-bottom"><a href="#marketplace/seller/${seller}" class="bold">${seller}</a></div>
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

	return html;
}

function get_profile_html(profile) {
	const p = profile;
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
					<p>${__(`Joined ${comment_when(p.creation)}`)}</p>
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

	</div>`;

	return profile_html;
}

export {
	get_detail_view_html,
	get_profile_html
}
