<template>
<div class='mt-3 col-md-4 col-sm-12'>
    <div class="card h-100">
        <router-link :to="'/Program/' + program.name">
            <div class="card-hero-img" v-if="program.hero_image" v-bind:style="{ 'background-image': 'url(' + image + ')' }"></div>
            <div v-else class="card-image-wrapper">
                <div class="image-body">{{ program.program_name }}</div>
            </div>
            <div class='card-body'>
                <h5 class='card-title'>{{ program.program_name }}</h5>
                <div>{{ program.description.substring(0,200) }}...</div>
            </div>
        </router-link>
        <div class='text-right p-3'>
            <button v-if="program.intro_video" class='btn btn-secondary btn-sm text-white' data-toggle="modal" data-target="#videoModal">Watch Intro</button>
            <a-button v-if="enrolled" type="dark" size="sm" :route="programPageRoute">
                {{ buttonName }}
            </a-button>
            <a v-else-if="isLogin" class='btn btn-secondary btn-sm' @click="enroll()">{{ enrollButton }}</a>
            <a v-else class='btn btn-secondary btn-sm' href="/login#signup">Sign Up</a>
        </div>
        <VideoModal v-if="program.intro_video" :title="program.program_name" :video="program.intro_video"/>
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
            programRoute: { name: 'program', params: { program_name: this.program.name }},
            image: "'" + this.program.hero_image + "'"
    	};
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
                return "Start Program"
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

    div.card-hero-img {
        height: 220px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-color: rgb(250, 251, 252);
    }

    .card-image-wrapper {
        display: flex;
        overflow: hidden;
        height: 220px;
        background-color: rgb(250, 251, 252);
    }

    .image-body {
        align-self: center;
        color: #d1d8dd;
        font-size: 24px;
        font-weight: 600;
        line-height: 1;
        padding: 20px;
    }
</style>