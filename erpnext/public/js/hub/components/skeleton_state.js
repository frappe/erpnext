function get_detail_skeleton_html() {
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

	return skeleton;
}

export {
	get_detail_skeleton_html
}
