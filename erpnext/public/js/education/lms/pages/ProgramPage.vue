<template>
<div>
	<TopSection v-bind:title="program.program_name" v-bind:description="program.description">
    </TopSection>
	<CardList :title="'Courses'" :description="''">
        <CourseCard slot="card-list-slot" v-for="course in course_data" :course="course.course" :program_name="program_name" :courseMeta="course.meta" :key="course.course.name + course.meta.flag"/>
    </CardList>
</div>
</template>
<script>
import TopSection from "../components/TopSection.vue"
import CardList from "../components/CardList.vue"
import CourseCard from "../components/CourseCard.vue"


export default {
	props: ['program_name'],
    name: "ProgramPage",
    components: {
		TopSection,
		CardList,
		CourseCard
	},
	data() {
		return {
			program: {},
			course_data: []
		}
	},
    beforeMount() {
        // if(lms.store.isLogin) lms.store.updateCompletedCourses()
    },
	mounted() {
		this.getProgramDetails().then(data => this.program = data);
		this.getCourses().then(data => this.course_data = data);
		
		// lms.on(`course-completed`, (course_name) => {
		// 	const course = this.course_data.findIndex(c => c.name === course_name);
		// 	this.course_data[course].completed = true;
		// });
	},
	methods: {
		// startCourse() {
		// 	this.getContentForNextCourse()
		// 		.then((data) => 
		// 			this.$router.push(`/Program/${this.program_name}/${data.course}/${data.content_type}/${data.content}`)
		// 		)
		// },
		// getContentForNextCourse() {
		// 	return lms.call('get_continue_data', {
		// 		program_name: this.program_name
		// 	});
		// },
		getProgramDetails() {
			return lms.call('get_program_details', {
				program_name: this.program_name
			});
		},
		getCourses() {
			return lms.call('get_courses', {
				program_name: this.program_name
			})
		}
	}
};
</script>