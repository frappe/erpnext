<template>
	<div class="nav-buttons">
		<button class='btn btn-outline-secondary' @click="$router.go(-1)">Back</button>
		<button v-if="nextContent" class='btn btn-primary' @click="goNext()">Next</button>
		<button v-else class='btn btn-primary' @click="$router.push({ name: 'program', params: { code: $route.params.code}})">Finish Course</button>
	</div>
</template>

<script>
export default {
	props: ['nextContent', 'nextContentType'],
	name: 'ContentNavigation',
	methods: {
		goNext() {
			frappe.call({
				method: "erpnext.www.academy.add_activity",
				args: {
					enrollment: this.$root.$data.enrolledCourses[this.$route.params.course],
					content_type: this.$route.params.type,
					content: this.$route.params.content
				}
			})
			this.$router.push({ name: 'content', params: { course: this.$route.params.course, type:this.nextContentType, content:this.nextContent }})
		}
	}
};
</script>

<style lang="css" scoped>
	.nav-buttons {
		position: absolute;
  		bottom: 0;
  		right: 0;
	}
</style>
