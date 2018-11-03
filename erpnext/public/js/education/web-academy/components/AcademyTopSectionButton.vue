<template>
    <button v-if="isLoggedIn" class='btn btn-primary btn-lg' @click="$router.push(getUrl())">{{ buttonName }}</button>
	<a v-else class='btn btn-primary btn-lg' href="/login#signup">{{ buttonName }}</a>
</template>
<script>
export default {
    name: "AcademyTopSectionButton",
    data() {
        return {
            buttonName: '',
            isLoggedIn: this.$root.$data.checkLogin(),
            nextContent: '',
            nextContentType: '',
            nextCourse: '',
            link: '',
        }
    },
    mounted() {
        if(this.isLoggedIn && this.$route.name == 'program'){
            frappe.call({
                method: "erpnext.www.academy.get_continue_data",
                args: {
                    program_name: this.$route.params.code
                }
            }).then( r => {
                this.nextContent = r.message.content,
                this.nextContentType = r.message.content_type,
                this.nextCourse = r.message.course
            })
        }

        if(this.isLoggedIn){
        	if(this.$route.name == 'home'){
                this.buttonName = 'Explore Courses'
        	}
            else if(this.$route.name == 'program'){
                this.buttonName = 'Start Course'
            }
        }
        else{
            this.buttonName = 'Sign Up'
        }
    },
    methods: {
        getUrl() {
            if(this.$route.name == 'home'){
                return ''
            }
            else if(this.$route.name == 'program'){
                this.link = this.$route.params.code + '/' + this.nextCourse + '/' + this.nextContentType + '/' + this.nextContent
                return this.link
            }
        }
    }
};
</script>