<script setup>
import { ref, computed, onMounted, reactive, onUnmounted } from 'vue';

const incomingSlabs = ref([]);
const selectedSlabId = ref(null);
const currentIncomingSlab = computed(() => {
    if (incomingSlabs.value.length === 0) return null;
    if (selectedSlabId.value) {
        const found = incomingSlabs.value.find(s => s.name === selectedSlabId.value);
        if (found) return found;
    }
    return incomingSlabs.value[0];
});

const slabQueue = ref([]);
const processTimerHandles = reactive({});
const error = ref(null);
const isProcessing = ref(false);
const current_station_title = window.station_name || "Cooling";
const current_station = current_station_title.toLowerCase();

const icon_class = computed(() => {
    switch (current_station) {
        case 'cooling':
            return 'fa-snowflake-o';
        case 'calibration':
            return 'fa-superpowers';
        case 'polishing':
            return 'fa-cube';
        default:
            return 'fa-question';
    }
});

const work_context = reactive({
    role: `${current_station_title} Operator`,
    assigned_line: "",
    assigned_station: `${current_station_title} Station`,
    assigned_shift: ""
});

const fetchWorkContext = async () => {
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.shift;
    }
};

const loadData = async (play_ding = false) => {
    try {
        const oldLength = incomingSlabs.value.length;
        const res = await frappe.call({
            method: 'erpnext.manufacturing.page.queue_station.queue_station.get_queue_data',
            args: {
				line: work_context.assigned_line || '1',
                station_name: current_station_title,
            }
        });

        if (res.message) {
            const fetched = res.message.incoming_slabs || [];
            incomingSlabs.value = fetched;

            if (play_ding && oldLength === 0 && fetched.length > 0) {
                erpnext.utils.play_ding("new_slab");
            }

            slabQueue.value = res.message.slabs_queue || [];

            // Initialize timers for the current process queue
            slabQueue.value.forEach(job => {
                if (job.status === 'Work In Progress') {
                    startTimer(job);
                }
            });
        }
    } catch (e) {
        console.error(e);
        error.value = "Failed to load data";
    }
};

const skipSlab = () => {
    if (incomingSlabs.value.length > 0) {
        const indexToShift = currentIncomingSlab.value
            ? incomingSlabs.value.findIndex(s => s.name === currentIncomingSlab.value.name)
            : 0;

        if (indexToShift !== -1) {
            incomingSlabs.value.splice(indexToShift, 1);
        } else {
            incomingSlabs.value.shift();
        }
        selectedSlabId.value = null;
    }
};

const startProcess = async (slab) => {
    frappe.confirm(
        __(`Are you sure you want to start the ${current_station} process for this slab?`),
        async () => {
            isProcessing.value = true;
            try {
                const res = await frappe.call({
                    method: 'erpnext.manufacturing.page.queue_station.queue_station.start_queue_process',
                    args: {
                        slab_number: slab.name,
						line: work_context.assigned_line,
                        station_name: current_station_title,
                    }
                });

                if (res.message) {
                    frappe.show_alert({ message: __(`${current_station_title} Started`), indicator: 'green' });
                    erpnext.utils.play_ding("submit");
                    await loadData();
                }
            } catch (e) {
                frappe.msgprint(__(`Failed to start ${current_station}!`));
            } finally {
                isProcessing.value = false;
            }
        }
    );
};

const finishProcess = async (job) => {
    frappe.confirm(
        __(`Are you sure you want to finish the ${current_station} process and unload this slab?`),
        async () => {
            isProcessing.value = true;
            try {
                const res = await frappe.call({
                    method: 'erpnext.manufacturing.page.operator_station.operator_station.finish_process',
                    args: {
                        job_card: job.name,
                        process_name: current_station_title,
                        transfer_materials: current_station !== 'cooling'
                    }
                });

                if (res.message) {
                    stopTimer(job.name);
                    frappe.show_alert({ message: __(`${current_station_title} Finished`), indicator: 'green' });
                    erpnext.utils.play_ding("submit");
                    await loadData();
                }
            } catch (e) {
                frappe.msgprint(__(`Failed to finish ${current_station}`));
            } finally {
                isProcessing.value = false;
            }
        }
    );
};

const updateJobElapsed = (job) => {
    if (job && job.started_time) {
        const start = frappe.datetime.str_to_obj(job.started_time);
        const now = new Date();
        job.elapsed = Math.floor((now - start) / 1000);
    }
};

const startTimer = (job) => {
    // Ensure we also update the elapsed time immediately
    updateJobElapsed(job);

    if (processTimerHandles[job.name]) return;

    processTimerHandles[job.name] = setInterval(() => {
        const currentJob = slabQueue.value.find(j => j.name === job.name);
        if (currentJob) {
            updateJobElapsed(currentJob);
        } else {
            stopTimer(job.name);
        }
    }, 1000);
};

const stopTimer = (jobName) => {
    if (processTimerHandles[jobName]) {
        clearInterval(processTimerHandles[jobName]);
        delete processTimerHandles[jobName];
    }
};

const formatDuration = (seconds) => {
    if (!seconds) return '00:00:00';
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
    const s = String(Math.floor(seconds % 60)).padStart(2, '0');
    return `${h}:${m}:${s}`;
};

onMounted(async () => {
    await fetchWorkContext();
    await loadData();

    document.addEventListener("refresh-queue-station", () => {
        loadData();
    });
});

onUnmounted(() => {
    Object.keys(processTimerHandles).forEach(stopTimer);
});

frappe.realtime.on('slab_checkout', (slab) => {
    if (slab.line !== work_context.assigned_line || (slab.status !== 'Heating' && slab.status !== 'Trimming' && slab.status !== 'Calibration')) {
        return;
    }

    loadData(true);
});
</script>

<template>
    <div class="queue-station-container p-4">
        <div class="d-flex w-100">
            <!-- Sidebar -->
            <div v-if="incomingSlabs.length > 1" class="queue-sidebar border-right flex-shrink-0 p-3 mr-4" style="width: 300px; max-height: calc(100vh - 100px); overflow-y: auto;">
                <h5 class="mb-3 font-weight-bold text-center border-bottom pb-2">
                    {{ __('Incoming Slabs') }}
                </h5>
                <div>
                    <div v-for="item in incomingSlabs" :key="item.name"
                        @click="!isProcessing && (selectedSlabId = item.name)" :class="[
                            'card pointer mb-2 shadow-sm slab-card border-0',
                            currentIncomingSlab && currentIncomingSlab.name === item.name ? 'active-card' : '',
                            isProcessing && currentIncomingSlab && currentIncomingSlab.name === item.name ? 'btn-disabled-pointer' : ''
                        ]">
                        <div class="card-body p-3 d-flex justify-content-between align-items-start"
                            style="height: 5rem">
                            <div>
                                <h6 class="card-title mb-1 font-weight-bold">{{ item.name }}</h6>
                                <div class="small text-muted mb-1">
                                    <span class="fa fa-cube mr-1"></span>{{ item.template }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Main Content -->
            <div class="flex-grow-1">
                <!-- Incoming Slab Section -->
                <div class="row mb-5 justify-content-center">
                    <div class="col-12">
                        <h4 class="mb-4 text-muted font-weight-bold">{{ __('Incoming Slab') }}</h4>
                        <Transition name="pop-switch" mode="out-in">
                            <div v-if="!currentIncomingSlab" key="empty" class="empty-state p-2 text-center border rounded">
                                <div class="mb-2 text-muted" style="opacity: 0.5;">
                                    <i class="fa fa-inbox" style="font-size: 3rem;"></i>
                                </div>
                                <p class="text-muted mb-0">{{ __('No incoming slabs') }}</p>
                            </div>

                            <div v-else key="strip"
                                class="incoming-slab-strip d-flex align-items-center justify-content-between rounded p-3 shadow-sm mb-4">
                                <div class="d-flex align-items-center">
                                    <span class="text-muted mr-3 font-weight-bold">{{ __('Incoming Slab') }}:</span>
                                    <div class="slab-thumbnail mr-3"></div>
                                    <div class="d-flex flex-column">
                                        <span class="font-weight-bold h5 mb-0">{{ currentIncomingSlab.name }}</span>
                                        <span class="text-muted small">{{ currentIncomingSlab.template }}</span>
                                    </div>
                                </div>
                                <div class="actions">
                                    <!-- <button class="btn btn-outline-secondary btn-sm mr-2 px-3" @click="skipSlab">
                                        <i class="fa fa-step-forward mr-1"></i> {{ __('Skip') }}
                                    </button> -->
                                    <button class="btn btn-primary btn-sm px-4" :disabled="isProcessing" @click="startProcess(currentIncomingSlab)">
                                        <i v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></i>
                                        <i v-else class="fa fa-play mr-1"></i> {{ __('Accept & Start') }}
                                    </button>
                                </div>
                            </div>
                        </Transition>
                    </div>
                </div>

                <hr class="my-4">

                <!-- Process Queue Section -->
                <div class="row">
                    <div class="col-12">
                        <h4 class="mb-4 text-muted font-weight-bold">{{ __(`${current_station_title} Queue`) }}</h4>
                        <div v-if="slabQueue.length === 0" class="empty-state p-5 text-center border rounded">
                            <div class="mb-3 text-muted" style="opacity: 0.5;">
                                <i class="fa" :class="icon_class" style="font-size: 3rem;"></i>
                            </div>
                            <p class="text-muted">{{ __(`No slabs in ${current_station}`) }}</p>
                        </div>

                        <TransitionGroup v-else name="list" tag="div" class="card-columns">
                            <div v-for="(job, index) in slabQueue" :key="job.name" class="card mb-3 shadow-sm queue-card">
                                <div class="card-body">
                                    <div class="d-flex justify-content-between mb-2">
                                        <h5 class="card-title font-weight-bold mb-0">{{ job.slab }}</h5>
                                        <span class="badge badge-info">{{ current_station_title }}</span>
                                    </div>
                                    <p class="card-text text-muted small mb-2">{{ job.slab_template }}</p>
                                    <p class="card-text text-muted x-small mb-3">{{ job.name }}</p>

                                    <div class="d-flex justify-content-between align-items-center">
                                        <div class="text-muted small">
                                            <i class="fa fa-clock-o mr-1"></i> {{ formatDuration(job.elapsed) }}
                                        </div>
                                        <button v-if="index === 0" class="btn btn-success btn-sm px-3"
                                            :disabled="isProcessing"
                                            @click="finishProcess(job)">
                                            <i v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></i>
                                            <i v-else class="fa fa-check mr-1"></i> {{ __('Unload Slab') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </TransitionGroup>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.queue-station-container {
    min-height: 80vh;
    padding-top: 30px;
}

.empty-state {
    background-color: var(--fg-color);
    border-style: dashed !important;
    border-width: 2px !important;
}

.incoming-slab-strip {
    transition: all 0.2s;
    background-color: var(--control-bg, #e2edff) !important;
    border: 1px solid var(--primary-color) !important;
}

[data-theme="dark"] .incoming-slab-strip {
    background-color: #1a202c !important;
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: #1f2937;
    flex-shrink: 0;
}

.queue-card {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
    border-left: 4px solid #17a2b8 !important;
}

.slab-card {
    transition: all 0.2s ease;
    border-radius: 8px;
    background-color: var(--fg-color) !important;
    border: 1px solid var(--border-color) !important;
}

.slab-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    background-color: var(--fg-hover-color) !important;
}

[data-theme="dark"] .slab-card {
    background-color: var(--card-bg) !important;
}

[data-theme="dark"] .slab-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    background-color: var(--disabled-control-bg, #1f2226) !important;
}

.active-card {
    border-left: 4px solid var(--primary-color) !important;
    background-color: var(--control-bg, #e2edff) !important;
}

[data-theme="dark"] .active-card {
    background-color: #1a202c !important;
}

.btn-disabled-pointer {
    cursor: not-allowed !important;
    opacity: 0.6;
}

/* Animations */
.pop-switch-enter-active {
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pop-switch-leave-active {
    transition: all 0.2s ease-in;
}

.pop-switch-enter-from,
.pop-switch-leave-to {
    opacity: 0;
    transform: scale(0.9);
}

.list-enter-active,
.list-leave-active {
    transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateY(20px);
}

.list-move {
    transition: transform 0.3s ease;
}
</style>
