<template>
	<div>
		<span v-for="(route, index) in routeData">
			<a href="route.route">{{ route.label }}</a><span> / </span>
		</span>
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