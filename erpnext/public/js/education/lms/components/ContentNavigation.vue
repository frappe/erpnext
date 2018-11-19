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
		addActivity() {
			if(this.$route.params.type != "Quiz"){
				lms.call({
					method: "add_activity",
					args: {
						enrollment: lms.store.enrolledCourses[this.$route.params.course],
						content_type: this.$route.params.type,
						content: this.$route.params.content
					}
				})
			}
		},
		goNext() {
			this.addActivity()
			this.$router.push({ name: 'content', params: { course: this.$route.params.course, type:this.nextContentType, content:this.nextContent }})
		},
		finish() {
			this.addActivity()
			this.$router.push({ name: 'program', params: { program_name: this.$route.params.program_name}})
			//
			lms.trigger('course-completed', course_name);
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
