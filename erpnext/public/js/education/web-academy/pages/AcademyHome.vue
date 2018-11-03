<template>
<div>
	<AcademyTopSection :title="title" :description="description">
        <AcademyTopSectionButton/>
    </AcademyTopSection>
	<AcademyList :title="'Featured Programs'" :description="'Master ERPNext'">
        <AcademyProgramCard v-for="program in featured_programs" :key="program.name" :program_code="program"/>
    </AcademyList>
</div>
</template>
<script>
import AcademyTopSection from "../components/AcademyTopSection.vue"
import AcademyList from "../components/AcademyList.vue"
import AcademyProgramCard from "../components/AcademyProgramCard.vue"
import AcademyTopSectionButton from "../components/AcademyTopSectionButton.vue"

export default {
    name: "AcademyHome",
    data() {
    	return{
    		title: '',
    		description: '',
            featured_programs: []
    	}
    },
    components: {
		AcademyTopSection,
        AcademyList,
        AcademyProgramCard,
        AcademyTopSectionButton
	},
	mounted() {
    	frappe.call("erpnext.www.academy.get_portal_details").then(r => {
    		this.title = r.message.title,
    		this.description = r.message.description
    	});
        frappe.call("erpnext.www.academy.get_featured_programs").then(r => {
            this.featured_programs = r.message
        });
    },
};
</script>