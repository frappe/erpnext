erpnext.ProductSearch = class {
	constructor() {
		this.MAX_RECENT_SEARCHES = 4;
		this.searchBox = $("#search-box");

		this.setupSearchDropDown();
		this.bindSearchAction();
	}

	setupSearchDropDown() {
		this.search_area = $("#dropdownMenuSearch");
		this.setupSearchResultContainer();
		this.populateRecentSearches();
	}

	bindSearchAction() {
		let me = this;

		// Show Search dropdown
		this.searchBox.on("focus", () => {
			this.search_dropdown.removeClass("hidden");
		});

		// If click occurs outside search input/results, hide results.
		// Click can happen anywhere on the page
		$("body").on("click", (e) => {
			let searchEvent = $(e.target).closest('#search-box').length;
			let resultsEvent = $(e.target).closest('#search-results-container').length;
			let isResultHidden = this.search_dropdown.hasClass("hidden");

			if (!searchEvent && !resultsEvent && !isResultHidden) {
				this.search_dropdown.addClass("hidden");
			}
		});

		// Process search input
		this.searchBox.on("input", (e) => {
			let query = e.target.value;

			if (query.length == 0) {
				me.populateResults([]);
				me.populateCategoriesList([]);
			}

			if (query.length < 3 || !query.length) return;

			// Populate recent search chips
			me.setRecentSearches(query);

			// Fetch and populate product results
			frappe.call({
				method: "erpnext.templates.pages.product_search.search",
				args: {
					query: query
				},
				callback: (data) => {
					me.populateResults(data);
				}
			});

			// Populate categories
			if (me.category_container) {
				frappe.call({
					method: "erpnext.templates.pages.product_search.get_category_suggestions",
					args: {
						query: query
					},
					callback: (data) => {
						me.populateCategoriesList(data);
					}
				});
			}

			this.search_dropdown.removeClass("hidden");
		});
	}

	setupSearchResultContainer() {
		this.search_dropdown = this.search_area.append(`
			<div class="overflow-hidden shadow dropdown-menu w-100 hidden"
				id="search-results-container"
				aria-labelledby="dropdownMenuSearch"
				style="display: flex; flex-direction: column;">
			</div>
		`).find("#search-results-container");

		this.setupCategoryContainer()
		this.setupProductsContainer();
		this.setupRecentsContainer();
	}

	setupProductsContainer() {
		this.products_container = this.search_dropdown.append(`
			<div id="product-results mt-2">
				<div id="product-scroll" style="overflow: scroll; max-height: 300px">
				</div>
			</div>
		`).find("#product-scroll");
	}

	setupCategoryContainer() {
		this.category_container = this.search_dropdown.append(`
			<div class="category-container mt-2 mb-1">
				<div class="category-chips">
				</div>
			</div>
		`).find(".category-chips");
	}

	setupRecentsContainer() {
		let $recents_section = this.search_dropdown.append(`
			<div class="mb-2 mt-2 recent-searches">
				<div>
					<b>${ __("Recent") }</b>
				</div>
			</div>
		`).find(".recent-searches");

		this.recents_container = $recents_section.append(`
			<div id="recents" style="padding: .25rem 0 1rem 0;">
			</div>
		`).find("#recents");
	}

	getRecentSearches() {
		return JSON.parse(localStorage.getItem("recent_searches") || "[]");
	}

	attachEventListenersToChips() {
		let me  = this;
		const chips = $(".recent-search");
		window.chips = chips;

		for (let chip of chips) {
			chip.addEventListener("click", () => {
				me.searchBox[0].value = chip.innerText.trim();

				// Start search with `recent query`
				me.searchBox.trigger("input");
				me.searchBox.focus();
			});
		}
	}

	setRecentSearches(query) {
		let recents = this.getRecentSearches();
		if (recents.length >= this.MAX_RECENT_SEARCHES) {
			// Remove the `first` query
			recents.splice(0, 1);
		}

		if (recents.indexOf(query) >= 0) {
			return;
		}

		recents.push(query);
		localStorage.setItem("recent_searches", JSON.stringify(recents));

		this.populateRecentSearches();
	}

	populateRecentSearches() {
		let recents = this.getRecentSearches();

		if (!recents.length) {
			this.recents_container.html(`<span class=""text-muted">No searches yet.</span>`);
			return;
		}

		let html = "";
		recents.forEach((key) => {
			html += `
				<div class="recent-search mr-1" style="font-size: 13px">
					<span class="mr-2">
						<svg width="20" height="20" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M8 14C11.3137 14 14 11.3137 14 8C14 4.68629 11.3137 2 8 2C4.68629 2 2 4.68629 2 8C2 11.3137 4.68629 14 8 14Z" stroke="var(--gray-500)"" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
							<path d="M8.00027 5.20947V8.00017L10 10" stroke="var(--gray-500)" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					</span>
					${ key }
				</div>
			`;
		});

		this.recents_container.html(html);
		this.attachEventListenersToChips();
	}

	populateResults(data) {
		if (data.length === 0 || data.message.results.length === 0) {
			let empty_html = ``;
			this.products_container.html(empty_html);
			return;
		}

		let html = "";
		let search_results = data.message.results;

		search_results.forEach((res) => {
			let thumbnail = res.thumbnail || '/assets/erpnext/images/ui-states/cart-empty-state.png';
			html += `
				<div class="dropdown-item" style="display: flex;">
					<img class="item-thumb col-2" src=${thumbnail} />
					<div class="col-9" style="white-space: normal;">
						<a href="/${res.route}">${res.web_item_name}</a><br>
						<span class="brand-line">${res.brand ? "by " + res.brand : ""}</span>
					</div>
				</div>
			`;
		});

		this.products_container.html(html);
	}

	populateCategoriesList(data) {
		if (data.length === 0 || data.message.results.length === 0) {
			let empty_html = `
				<div class="category-container mt-2">
					<div class="category-chips">
					</div>
				</div>
			`;
			this.category_container.html(empty_html);
			return;
		}

		let html = `
			<div class="mb-2">
				<b>${ __("Categories") }</b>
			</div>
		`;
		let search_results = data.message.results;
		search_results.forEach((category) => {
			html += `
				<a href="/${category.route}" class="btn btn-sm category-chip mr-2 mb-2"
					style="font-size: 13px" role="button">
				${ category.name }
				</button>
			`;
		});

		this.category_container.html(html);
	}
};