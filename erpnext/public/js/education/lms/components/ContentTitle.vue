<template>
    <section class='article-top-section video-section-bg'>
        <div>
            <div class="row">
                <div class="col-md-8">
                    <h2>{{ title }}</h2>
                    <span v-if="typeof author !== 'undefined' || author !== null" class="text-muted">
                        <span v-if="publishDate">Published on {{ publishDate }}</span>
                        <span v-if="author">— {{ author }}</span>
                    </span>
                </div>
                <div class="col-md-4 text-right">
                    <slot></slot>
                </div>
            </div>
            <hr>
        </div>
    </section>
</template>

<script>
export default {
    props: ['title', 'publishDate', 'author'],
    name: 'ContentTitle',
};
</script>

<style lang="css" scoped>
</style>
