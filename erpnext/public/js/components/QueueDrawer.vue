<template>
    <div>
        <button v-if="queueSlabs.length && !isQAStarted" class="fixed-queue-btn btn btn-primary shadow" @click="showQueue">
            <span class="fa fa-list mr-2"></span>
            <span class="small font-weight-bold text-uppercase">{{ __('Queue') }}</span>
        </button>

        <!-- Queue Drawer -->
        <div class="drawer-container queue-drawer">
            <Transition name="fade">
                <div v-if="show" class="drawer-backdrop" @click="$emit('update:show', false)"></div>
            </Transition>
            <Transition name="slide-left">
                <div v-if="show" class="drawer-panel left p-4 shadow-lg" style="background-color: var(--card-bg);">
                    <div class="d-flex justify-content-between align-items-center mb-4 border-bottom pb-2">
                        <h4 class="mb-0">{{ __('Job Queue') }}</h4>
                        <button class="btn btn-light btn-sm" @click="$emit('update:show', false)">
                            <span class="fa fa-times"></span>
                        </button>
                    </div>

                    <div class="queue-list">
                        <div v-for="slab in queueSlabs" :key="slab.name" class="card mb-3 shadow-sm border" style="background-color: var(--fg-color);">
                            <div class="card-body p-3 pl-5 d-flex flex-column justify-content-center cursor-pointer" @click="$emit('select', slab)">
                                <!-- <div class="slab-thumbnail-large mr-4"></div> -->
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div class="h5 font-weight-bold mb-0">{{ slab.name }}</div>
                                    <!-- <div class="badge border text-muted" style="background-color: var(--control-bg);">{{ job.name }}</div> -->
                                </div>
                                <div class="text-muted small mb-3">{{ slab.template }}</div>

                                <div v-if="slab.is_recovered || slab.is_repolished || slab.is_recalibrated"
                                    class="alert alert-danger p-2 mb-0 mt-2 small font-weight-bold">
                                    <span v-if="slab.is_recovered">{{ __('Recovered') }} </span>
                                    <span v-if="slab.is_repolished">{{ __('Repolished') }} </span>
                                    <span v-if="slab.is_recalibrated">{{ __('Recalibrated') }}</span>
                                </div>
                            </div>
                        </div>
                        <div v-if="!queueSlabs.length" class="text-center py-5 text-muted">
                            {{ __('No slabs in queue.') }}
                        </div>
                    </div>
                </div>
            </Transition>
        </div>
    </div>
</template>

<script setup>
const props = defineProps({
    show: {
        type: Boolean,
        required: true
    },
    queueSlabs: {
        type: Array,
        required: true
    },
    isQAStarted: {
        type: Boolean,
        default: false
    }
});

const emit = defineEmits(['update:show', 'select', 'fetch-queue']);

const showQueue = () => {
    emit('update:show', true);
    emit('fetch-queue');
};
</script>

<style scoped>
.fixed-queue-btn {
    position: fixed;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    border-radius: 0 8px 8px 0;
    z-index: 1040;
    padding: 12px 16px;
    transition: all 0.2s;
}

.fixed-queue-btn:hover {
    opacity: 0.9;
    transform: translateY(-50%) scale(1.05);
}

.drawer-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1050;
}

.drawer-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 800px;
    height: 100%;
    z-index: 1060;
    overflow-y: auto;
    background-color: var(--card-bg);
}

.drawer-panel.left {
    left: 0;
    right: auto;
    width: 400px;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.slide-left-enter-active,
.slide-left-leave-active {
    transition: transform 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
    transform: translateX(-100%);
}

.cursor-pointer {
    cursor: pointer;
}
</style>
