<template>
    <button v-if="isLoggedIn" class='btn btn-primary btn-lg' @click="getUrl()">{{ buttonName }}</button>
	<a v-else class='btn btn-primary btn-lg' href="/login#signup">{{ buttonName }}</a>
</template>
<script>
export default {
    name: "AcademyTopSectionButton",
    data() {
        return {
            buttonName: '',
            isLoggedIn: this.$root.$data.checkLogin()
        }
    },
    mounted() {
        if(this.$root.$data.checkLogin()){
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
            console.log('method getUrl() called')
            if(this.$route.name == 'home'){
                return ''
            }
            else if(this.$route.name == 'program'){
                return 'Program/' + this.$route.params.code + this.$route.params.course
            }
        }
    }
};
</script>