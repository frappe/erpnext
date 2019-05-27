
<template>
    <div class="py-3 col-md-4 col-sm-12">
        <div class="card h-100">
            <div class="card-hero-img" v-if="topic.hero_image" v-bind:style="{ 'background-image': 'url(' + image + ')' }"></div>
            <div v-else class="card-image-wrapper">
                <div class="image-body">{{ topic.topic_name }}</div>
            </div>
            <div class='card-body'>
                <h5 class="card-title">{{ topic.topic_name }}</h5>
                <span class="course-list text-muted" id="getting-started">
                    Content
                    <ul class="mb-0 mt-1" style="padding-left: 1.5em;">
                        <li v-for="content in topic.topic_content" :key="content.name">
                            <router-link v-if="isLogin" tag="a" :class="'text-muted'" :to="{name: 'content', params:{program_name: program_name, topic:topic.name, course_name: course_name, type:content.content_type, content: content.content} }">
                                {{ content.content }}
                            </router-link>
                            <div v-else><span style="padding-right: 0.4em"></span>{{ content.content }}</div>
                        </li>
                    </ul>
                </span>
            </div>
            <div v-if="isLogin" class='p-3' style="display: flex; justify-content: space-between;">
                <div>
                    <span v-if="complete"><i class="mr-2 text-success fa fa-check-circle" aria-hidden="true"></i>Course Complete</span>
                </div>
                <div class='text-right'>
                    <a-button
                    :type="'primary'"
                    size="sm"
                    :route="firstContentRoute"
                >
                    {{ buttonName }}
                </a-button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import AButton from './Button.vue';

export default {
    props: ['topic', 'course_name', 'program_name'],
    name: "TopicCard",
    data() {
        return {
            topicDetails: {}
        }
    },
    mounted() {
        if(lms.store.checkLogin()) this.gettopicDetails().then(data => this.topicDetails = data)
    },
    components: {
        AButton
    },
    computed: {
        firstContentRoute() {
            if(lms.store.checkLogin()){
                return `/Program/${this.program_name}/${this.course_name}/${this.topic.name}/${this.topicDetails.content_type}/${this.topicDetails.content}`
            }
            else {
                return {}
            }
        },
        complete() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                if (this.topicDetails.flag === "Completed" ) {
                    return true
                }
                else {
                    return false
                }
            }
            else {
                return false
            }
        },
        isLogin() {
            // return lms.store.checkProgramEnrollment(this.program_name)
            return lms.store.checkLogin()
        },
        buttonName() {
            if(lms.store.checkProgramEnrollment(this.program_name)){
                if (this.topicDetails.flag == 'Continue'){
                    return 'Continue'
                }
                else {
                    return 'Start Topic'
                }
            }
            else {
                return "Explore"
            }
        }
    },
    methods: {
        iconClass(content_type) {
            if(content_type == 'Video') return 'fa fa-play'
            if(content_type == 'Article') return 'fa fa-file-text-o'
            if(content_type == 'Quiz') return 'fa fa-question-circle-o'
        },
        gettopicDetails() {
			return lms.call('get_student_topic_details', {
                    topic_name: this.topic.name,
                    course_name: this.course_name,
				})
        },
    }
};
</script>