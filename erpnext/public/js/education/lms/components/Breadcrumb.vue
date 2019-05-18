<template>
	<div>
		<nav aria-label="breadcrumb">
			<ol class="breadcrumb">
				<li v-for="(route, index) in routeData" class="breadcrumb-item active" aria-current="page">
					<router-link v-if="index != routeData.length - 1" :to="route.route">
						{{ route.label }}
					</router-link>
					<span v-else>{{ route.label }}</span>
				</li>
			</ol>
		</nav>
	</div>
</template>
<script type="text/javascript">
	export default {
		name: "Breadcrumb",
		data() {
			return {
				routeName: this.$route.name,
				routeParams: this.$route.params,
				routeData: [{
					label: "All Programs",
					route: "/List/Program"
				}]
			}
		},
		mounted() {
			this.buildBreadcrumb()
		},
		methods: {
			buildBreadcrumb() {
				if(this.routeName == 'program') {
					return
				}
				if(this.routeName == 'course') {
					let routeObject = {
						label: this.routeParams.program_name,
						route: `/Program/${this.routeParams.program_name}`
					}
					this.routeData.push(routeObject)
				}
				if(this.routeName == 'content') {
					this.routeData.push({
						label: this.routeParams.program_name,
						route: `/Program/${this.routeParams.program_name}`
					})
					this.routeData.push({
						label: this.routeParams.course_name,
						route: `/Program/${this.routeParams.program_name}/${this.routeParams.course_name}`
					})
				}
			}
		}
	};
</script>