<template>
	<div class="nav-buttons">
		<button class='btn btn-outline-secondary' @click="$router.go(-1)">Back</button>
		<button v-if="nextContent" class='btn btn-primary' @click="goNext()">Next</button>
		<button v-else class='btn btn-primary' @click="finish()">Finish Course</button>
	</div>
</template>

<script>
export default {
	props: ['nextContent', 'nextContentType'],
	name: 'ContentNavigation',
	methods: {
		goNext() {
			if(this.$route.params.type != "Quiz"){
				frappe.call({
					method: "erpnext.www.academy.add_activity",
					args: {
						enrollment: this.$root.$data.enrolledCourses[this.$route.params.course],
						content_type: this.$route.params.type,
						content: this.$route.params.content
					}
				})
			}
			this.$router.push({ name: 'content', params: { course: this.$route.params.course, type:this.nextContentType, content:this.nextContent }})
		},
		finish() {
			if(this.$route.params.type != "Quiz"){
				frappe.call({
					method: "erpnext.www.academy.add_activity",
					args: {
						enrollment: this.$root.$data.enrolledCourses[this.$route.params.course],
						content_type: this.$route.params.type,
						content: this.$route.params.content
					}
				})
			}
			frappe.call({
					method: "erpnext.www.academy.mark_course_complete",
					args: {
						enrollment: this.$root.$data.enrolledCourses[this.$route.params.course]
					}
				})
			this.$root.$data.addCompletedCourses(this.$route.params.course)
			this.$root.$data.updateCompletedCourses()
			this.$router.push({ name: 'program', params: { code: this.$route.params.code}})
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
