<template>
<div class='margin'>
    <div class="card">
        <img v-if="program.hero_image" :src="program.hero_image" style='height: 150px; width: auto'>
        <div class='card-body'>
            <router-link :to="'/Program/' + program.name">
                <h5 class='card-title'>{{ program.program_name }}</h5>
            </router-link>
            <div v-html="program.description"></div>
        </div>
        <div class='text-right p-3'>
            <button class='btn btn-secondary btn-sm text-white' data-toggle="modal" data-target="#videoModal">Watch Intro</button>
            <a-button v-if="enrolled" type="dark" size="sm" :route="programPageRoute">
                {{ buttonName }}
            </a-button>
            <a v-else-if="isLogin" class='btn btn-secondary btn-sm' @click="enroll()">{{ enrollButton }}</a>
            <a v-else class='btn btn-secondary btn-sm' href="/login#signup">Sign Up</a>
        </div>
        <VideoModal :title="program.program_name" :video="program.intro_video"/>
    </div>
</div>
</template>
<script>
import AButton from './Button.vue';
import VideoModal from './VideoModal.vue';
export default {
    props: ['program', 'enrolled'],
    name: "ProgramCard",
    data() {
    	return {
            isLogin: frappe.is_user_logged_in(),
            enrollButton: 'Enroll Now',
            programRoute: { name: 'program', params: { program_name: this.program.name }}
    	};
    },
    created() {
    },
    methods: {
        enroll() {
            this.enrollButton = 'Enrolling...'
            lms.call('enroll_in_program', {
                program_name: this.program.name,
            }).then(data => {
                lms.store.updateEnrolledPrograms()
                this.$router.push(this.programRoute)
            })
        }
    },
    computed: {
        buttonName() {
            if(this.enrolled){
                return "Explore Program"
            }
            else {
                return "Enroll"
            }
        },
        programPageRoute() {
            return this.programRoute
        },
        isEnrolled() {
            return lms.store.enrolledPrograms.includes(this.program.name)
        }
    },
    components: {
        AButton,
        VideoModal
    }
};
</script>

<style lang="css" scoped>
    a {
        text-decoration: none;
        color: black;
    }
    a.btn-secondary {
        color: white !important;
    }
</style>