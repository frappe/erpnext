<template>
    <div>
        <button v-if="slabQAReport?.repair_history?.length" class="fixed-repair-btn btn btn-primary shadow" @click="$emit('update:show', true)">
            <span class="fa fa-wrench mr-2"></span>
            <span class="small font-weight-bold text-uppercase">{{ __('History') }}</span>
        </button>

        <!-- Repair History Drawer -->
        <div class="drawer-container">
            <Transition name="fade">
                <div v-if="show" class="drawer-backdrop" @click="$emit('update:show', false)"></div>
            </Transition>
            <Transition name="slide-right">
                <div v-if="show" class="drawer-panel p-4 shadow-lg">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h4 class="mb-0">{{ __('Repair History') }}</h4>
                        <button class="btn btn-light btn-sm" @click="$emit('update:show', false)">
                            <span class="fa fa-times"></span>
                        </button>
                    </div>
                    <table class="table table-bordered table-sm small">
                        <thead class="text-muted text-uppercase">
                            <tr>
                                <th style="width: 40px;"></th>
                                <th>{{ __('Repair Type') }}</th>
                                <th>{{ __('Reasons') }}</th>
                                <th style="width: 170px;">{{ __('Repair Date') }}</th>
                                <th>{{ __('Remarks') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(item, idx) in slabQAReport?.repair_history" :key="idx">
                                <td class="text-center" style="vertical-align: middle;">
                                    <div :style="{
                                        width: '12px',
                                        height: '12px',
                                        borderRadius: '50%',
                                        backgroundColor: item.colour,
                                        border: '1px solid var(--border-color)',
                                        margin: '0 auto'
                                    }"></div>
                                </td>
                                <td style="vertical-align: middle;" class="font-weight-bold">{{ item.repair }}</td>
                                <td style="vertical-align: middle;">{{ item.repair_reason }}</td>
                                <td style="vertical-align: middle;">{{ $filters.formatDateTime(item.repair_date) }}</td>
                                <td>{{ item.remarks }}</td>
                            </tr>
                            <tr v-if="!slabQAReport?.repair_history?.length">
                                <td colspan="5" class="text-center text-muted p-4">
                                    {{ __('No repair history available.') }}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </Transition>
        </div>
    </div>
</template>

<script setup>
defineProps({
    show: {
        type: Boolean,
        required: true
    },
    slabQAReport: {
        type: Object,
        default: () => ({})
    }
});

defineEmits(['update:show']);
</script>

<style scoped>
.fixed-repair-btn {
    position: fixed;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    border-radius: 8px 0 0 8px;
    z-index: 1040;
    padding: 12px 16px;
    transition: all 0.2s;
}

.fixed-repair-btn:hover {
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

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
    transition: transform 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
    transform: translateX(100%);
}
</style>
