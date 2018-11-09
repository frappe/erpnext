<template>
<div>
	<AcademyTopSection v-bind:title="program.program_name" v-bind:description="program.description">
        <!-- <AcademyTopSectionButton/> -->
		<a-button @click="startCourse">Start Course</a-button>
		<a-button @click="continueCourse">Continue Course</a-button>
    </AcademyTopSection>
	<AcademyList :title="'Courses'" :description="''">
        <AcademyCourseCard v-for="course in course_list" :course="course" :key="course.name"/>
    </AcademyList>
</div>
</template>
<script>
import Button from '../components/Button.vue';
import AcademyTopSection from "../components/AcademyTopSection.vue"
import AcademyList from "../components/AcademyList.vue"
import AcademyCourseCard from "../components/AcademyCourseCard.vue"
import AcademyTopSectionButton from "../components/AcademyTopSectionButton.vue";


export default {
	props: ['program_name'],
    name: "AcademyProgramPage",
    components: {
        AButton: Button,
		AcademyTopSection,
		AcademyList,
		AcademyCourseCard,
        AcademyTopSectionButton
	},
	data() {
		return {
			program: {},
			course_list: []
		}
	},
    beforeMount() {
        if(this.$root.$data.isLogin) this.$root.$data.updateCompletedCourses()
    },
	mounted() {
		this.getProgramDetails().then(data => this.program = data);
		this.getCourses().then(data => this.course_list = data);
		
		academy.on(`course-completed`, (course_name) => {
			const course = this.course_list.findIndex(c => c.name === course_name);
			this.course_list[course].completed = true;
		});
	},
	methods: {
		startCourse() {
			this.getContentForNextCourse()
				.then((data) => 
					this.$router.push(`/Program/${this.program_name}/${data.course}/${data.content_type}/${data.content}`)
				)
		},
		getContentForNextCourse() {
			return academy.call('get_continue_data', {
				program_name: this.program_name
			});
		},
		getProgramDetails() {
			return academy.call('get_program_details', {
				program_name: this.program_name
			});
		},
		getCourses() {
			return academy.call('get_courses', {
				program_name: this.program_name
			})
		}
	}
};
</script>