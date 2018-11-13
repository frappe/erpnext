<template>
    <div class='card-deck mt-5'>
    <div class="card">
        <img :src="program.hero_image" style='height: 150px; width: auto'>
        <div class='card-body'>
            <router-link :to="'/Program/' + program.name">
                <h5 class='card-title'>{{ program.program_name }}</h5>
            </router-link>
            <div v-html="program.description"></div>
        </div>
        <div class='card-footer text-right'>
            <!-- <a class='video-btn btn btn-secondary btn-sm' data-toggle="modal" data-src=" insert jinja stuff here " data-target="#myModal">Watch Intro</a>&nbsp;&nbsp; -->
            <a-button
                    v-if="enrolled"
                    type="primary"
                    size="sm"
                    :route="programPageRoute"
                >
                    {{ buttonName }}
            </a-button>
            <a v-else-if="isLogin" class='btn btn-secondary btn-sm' @click="enroll()">Enroll</a>
            <a v-else class='btn btn-secondary btn-sm' href="/login#signup">Sign Up</a>
        </div>
    </div>
</div>
</template>
<script>
import AButton from './Button.vue';
export default {
    props: ['program', 'enrolled'],
    name: "ProgramCard",
    data() {
    	return {
            isLogin: lms.store.isLogin
    	};
    },
    created() {
    },
    methods: {
        enroll() {
            lms.call('enroll_in_program', {
                program_name: this.program.name,
            }).then(
                lms.store.enrolledPrograms.add(this.program.name),
                lms.store.updateEnrolledPrograms(),
                this.router.push('Program/' + this.program.name)
            )
        }
    },
    computed: {
        buttonName() {
                if(this.enrolled){
                    return "Start Course"
                }
                else {
                    return "Enroll"
                }
        },
        programPageRoute() {
            return `Program/${this.program.name}`
        },
        isEnrolled() {
            return lms.store.enrolledPrograms.has(this.program.name)
        }
    },
    components: {
        AButton
    }
};
</script>

<style lang="css" scoped>
    a {
    text-decoration: none;
}
</style>