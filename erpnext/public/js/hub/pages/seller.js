import SubPage from './subpage';

erpnext.hub.Seller = class Seller extends SubPage {
	make_wrapper() {
		super.make_wrapper();
	}

	refresh() {
		this.show_skeleton();
		this.company = frappe.get_route()[2];
		this.get_hub_seller_profile()
			.then(this.render.bind(this));
	}

	get_hub_seller_profile() {
		return hub.call('get_hub_seller_profile', { company: this.company });
	}

	// get_hub_seller_items(profile) {
	// 	this.profile = profile;
	// 	console.log(profile);
	// 	return hub.call('get_items', { hub_seller: profile.user });
	// }

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

	render(profile) {
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

		this.$wrapper.html(profile_html);
	}
}
