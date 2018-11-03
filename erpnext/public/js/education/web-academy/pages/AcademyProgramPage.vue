<template>
<div>
	<AcademyTopSection v-bind:title="program.program_name" v-bind:description="program.description">
        <AcademyTopSectionButton/>
    </AcademyTopSection>
	<AcademyList :title="'Courses'" :description="''">
        <AcademyCourseCard v-for="course in course_list" :course="course" :key="course.name"/>
    </AcademyList>
</div>
</template>
<script>
import AcademyTopSection from "../components/AcademyTopSection.vue"
import AcademyList from "../components/AcademyList.vue"
import AcademyCourseCard from "../components/AcademyCourseCard.vue"
import AcademyTopSectionButton from "../components/AcademyTopSectionButton.vue"

export default {
	props: ['code'],
    name: "AcademyProgramPage",
    components: {
		AcademyTopSection,
		AcademyList,
		AcademyCourseCard,
        AcademyTopSectionButton
	},
	data() {
		return {
			program: '',
			course_list: []
		}
	},
	mounted() {
        this.$root.$data.updateCompletedCourses()
		frappe.call({
            method: "erpnext.www.academy.get_program_details",
            args: {
                program_name: this.code
            }
        }).then(r => {
    		this.program = r.message
    	});
    	frappe.call({
    		method: "erpnext.www.academy.get_courses",
    		args: {
    			program_name: this.code
    		}
    	}).then(r => {
    		this.course_list = r.message
    	})
	},
};
</script>