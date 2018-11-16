<template>
	<div v-if="seen" class="col-md-3 col-sm-4 col-xs-6 hub-card-container">
		<div class="hub-card"
			@click="on_click(item_id)"
		>
			<div class="hub-card-header flex justify-between">
				<div class="ellipsis" :style="{ width: '85%' }">
					<div class="hub-card-title ellipsis bold">{{ title }}</div>
					<div class="hub-card-subtitle ellipsis text-muted" v-html='subtitle'></div>
				</div>
				<i v-if="allow_clear"
					class="octicon octicon-x text-extra-muted"
					@click.stop="$emit('remove-item', item_id)"
				>
				</i>
			</div>
			<div class="hub-card-body">
				<base-image class="hub-card-image" :src="item.image" :alt="title" />
				<div class="hub-card-overlay">
					<div v-if="is_local" class="hub-card-overlay-body">
						<div class="hub-card-overlay-button">
							<button class="btn btn-default zoom-view">
								<i class="octicon octicon-pencil text-muted"></i>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>

export default {
	name: 'item-card',
	props: ['item', 'item_id_fieldname', 'is_local', 'on_click', 'allow_clear', 'seen'],
	computed: {
		title() {
			const item_name = this.item.item_name || this.item.name;
			return strip_html(item_name);
		},
		subtitle() {
			const dot_spacer = '<span aria-hidden="true"> · </span>';
			if(this.is_local){
				return comment_when(this.item.creation);
			} else {
				let subtitle_items = [comment_when(this.item.creation)];
				const rating = this.item.average_rating;

				if (rating > 0) {
					subtitle_items.push(rating + `<i class='fa fa-fw fa-star-o'></i>`)
				}

				subtitle_items.push(this.item.company);

				return subtitle_items.join(dot_spacer);
			}
		},
		item_id() {
			return this.item[this.item_id_fieldname];
		}
	}
}
</script>

<style lang="less" scoped>
	@import "../../../../../../frappe/frappe/public/less/variables.less";

	.hub-card {
		margin-bottom: 25px;
		position: relative;
		border: 1px solid @border-color;
		border-radius: 4px;
		overflow: hidden;
		cursor: pointer;

		&:hover .hub-card-overlay {
			display: block;
		}

		.octicon-x {
			display: block;
			font-size: 20px;
			margin-left: 10px;
			cursor: pointer;
		}
	}

	.hub-card.closable {
		.octicon-x {
			display: block;
		}
	}

	.hub-card.is-local {
		&.active {
			.hub-card-header {
				background-color: #f4ffe5;
			}
		}
	}

	.hub-card-header {
		position: relative;
		padding: 12px 15px;
		height: 60px;
		border-bottom: 1px solid @border-color;
	}

	.hub-card-body {
		position: relative;
		height: 200px;
	}

	.hub-card-overlay {
		display: none;
		position: absolute;
		top: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.05);
	}

	.hub-card-overlay-body {
		position: relative;
		height: 100%;
	}

	.hub-card-overlay-button {
		position: absolute;
		right: 15px;
		bottom: 15px;
	}

	.hub-card-image {
		width: 100%;
		height: 100%;
		object-fit: contain;
	}

</style>
