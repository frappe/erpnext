<script setup>
import { ref, reactive, nextTick, computed, onMounted, onUnmounted } from 'vue';

// TODO: Make this dynamic based on the user's role.
const jobCardNumber = ref(null);
const updateKey = ref(0);
const ovenData = ref(null);
// const incomingSlabs = ref([])
// { name: ..., serial_number: ..., template: ..., line: ... }
const currentSlab = ref(null); 
const loadingSlab = ref(false);

const work_context = reactive({
    assigned_line: "",
    assigned_station: "Oven 1",
    assigned_shift: ""
});

const fetchWorkContext = async () => {
    const settings = await frappe.db.get_doc('Demo Settings');
    if (settings) {
        work_context.assigned_line = settings.default_line;
        work_context.assigned_shift = settings.default_shift;
    }
};

const refreshOvenData = async () => {
    if (!work_context?.assigned_line) {
        return
    }

    try {
        const r = await frappe.call({
            method: 'erpnext.manufacturing.doctype.oven.api.get_oven_from_line',
            args: {
                line: work_context.assigned_line,
            }
        });

        if (r.message) {
            ovenData.value = r.message;
        }
    } catch (e) {
        console.error("Failed to fetch oven data", e);
    }
};


const fetch_slab_for_job_card = async () => {
    if (!jobCardNumber.value) return;

    loadingSlab.value = true;
    try {
        const r = await frappe.call({
            method: 'erpnext.manufacturing.doctype.slab.api.get_slab_for_job_card',
            args: {
                job_card: jobCardNumber.value
            }
		});

        if (r.message) {
            selectedSlab.value = r.message;
        } else {
            // Fallback: Check previous stage
            const r2 = await frappe.call({
                method: 'erpnext.manufacturing.doctype.slab.api.get_slab_from_previous_stage',
                args: {
                    job_card_name: jobCardNumber.value
                }
            });
            if (r2.message) {
                selectedSlab.value = r2.message;
            }
        }
    } catch (e) {
        console.error("Failed to fetch slab for job card", e);
    } finally {
        loadingSlab.value = false;
    }
};

const get_slabs_ready_for_heating = async () => {
    // If we have a specific Job Card, just fetch its slab
    if (jobCardNumber.value) {
        await fetch_slab_for_job_card();
        return;
    }

    // Otherwise, fetch the general queue (Fallback/Original behavior)
    const r = await frappe.call({
        method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_for',
        args: {
            line: work_context.assigned_line,
            next_stage: "Heating"
        }
    });

    if (r.message) {
        currentSlab.value = r.message;
        updateKey.value++;
        if (currentSlab.value.length > 0) {
            selectSlab(currentSlab.value[0], 0);
        }
    }
};

const currentTime = ref(new Date());
let timerInterval = null;

onMounted(async () => {
    const route = frappe.get_route();
    jobCardNumber.value = route[2] || null;
    timerInterval = setInterval(() => {
        currentTime.value = new Date();
    }, 1000);
    await fetchWorkContext();
    refreshOvenData();
    get_slabs_ready_for_heating();
});

onUnmounted(() => {
    if (timerInterval) clearInterval(timerInterval);
});

const formattedDate = computed(() => {
    const d = currentTime.value;
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
});

const formattedTime = computed(() => {
    const d = currentTime.value;
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
});

const overheat_minutes = 90; // TODO: This should be replaced by a setting in Mahi Granites Settings.

const racks = computed(() => {
    if (!ovenData.value || !ovenData.value.racks) return [];

    return ovenData.value.racks.map(r => {
        // Calculate time_text if curing
        let time_text = '';
        if ((r.status === 'Heating' || r.status === 'Overheat') && r.start_time) {
            const start = new Date(r.start_time);
            const now = currentTime.value;
            const diffMs = now - start;

            if (diffMs > 0) {
                const diffSec = Math.floor(diffMs / 1000);
                const mm = Math.floor(diffSec / 60).toString().padStart(2, '0');
                const ss = (diffSec % 60).toString().padStart(2, '0');
                time_text = `${mm}:${ss}`;
            } else {
                time_text = "00:00";
            }

            // If the total time elapsed is greater than overheat_minutes, set status to Overheat
            if (diffMs > overheat_minutes * 60 * 1000) {
                r.status = 'Overheat';
            }
        }

        return {
            name: r.name,
            slot: r.rack_number,
            state: r.status,
            slab: r.current_slab,
            color: r.current_slab_template || "KY1005-J-20",
            is_operational: r.is_operational,
            time_text: time_text,
        };
    });
});

const oven = computed(() => {
    return ovenData.value;
});


const selectedSlab = ref(null);

const ovenTemps = computed(() => {
    if (!ovenData.value) return { upper: 0, lower: 0 };
    return {
        upper: ovenData.value.slab_top_temp,
        lower: ovenData.value.slab_bottom_temp
    };
});

const showMeasureModal = ref(false);
const targetRack = ref(null);
const measurements = ref({
    tl: 0, tr: 0, bl: 0, br: 0,
    tm: 0, bm: 0, lm: 0, rm: 0
});

const showUnloadModal = ref(false);
const unloadValues = ref({
    slab_top_temp: 0,
    slab_bottom_temp: 0,
    remarks: ''
});

function selectSlab(slab, index) {
    if (index) {
        return;
    }

    selectedSlab.value = slab;
}

function loadIntoRack(rack) {
    if (rack.state !== 'Idle' || !rack.is_operational) return;

    if (!selectedSlab.value) {
        frappe.msgprint(__('Please select an incoming slab or ensure Job Card is active.'));
        return;
    }

    // Prepare for modal
    targetRack.value = rack;
    // Reset measurements
    measurements.value = {
        tl: 0, tr: 0, bl: 0, br: 0,
        tm: 0, bm: 0, lm: 0, rm: 0
    };

    showMeasureModal.value = true;

    nextTick(() => {
        const el = document.getElementById('pos-tl');
        if (el) el.select();
    });
}

async function unload_slab_from_rack(rack) {
    if (rack.state !== 'Heating' && rack.state !== 'Overheat' || !rack.is_operational) return;

    targetRack.value = rack;
    unloadValues.value = {
        slab_top_temp: undefined,
        slab_bottom_temp: undefined,
        remarks: ''
    };
    showUnloadModal.value = true;
}

async function transfer_to_next_process(workOrder, qty) {
    if (!workOrder) return;

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.doctype.operation.api.transfer_to_next_process',
            args: {
                current_work_order: workOrder,
                qty: qty
            }
        });

        if (res.message) {
            frappe.show_alert({message: __('Slab transferred to next process'), indicator: 'green'});
        }
    } catch (e) {
        console.error("Transfer failed", e);
    }
}
async function confirmUnload() {
    if (!targetRack.value) return;

    if (unloadValues.value.slab_top_temp === undefined || unloadValues.value.slab_top_temp === '' || unloadValues.value.slab_top_temp === null) {
        frappe.msgprint(__('Please enter Slab Top Temperature'));
        return;
    }
    if (unloadValues.value.slab_bottom_temp === undefined || unloadValues.value.slab_bottom_temp === '' || unloadValues.value.slab_bottom_temp === null) {
        frappe.msgprint(__('Please enter Slab Bottom Temperature'));
        return;
    }

    try {
        const res = await frappe.call({
            method: 'erpnext.manufacturing.doctype.oven.api.unload_slab_from_oven',
            args: {
                rack_name: targetRack.value.name,
                slab_name: targetRack.value.slab,
                slab_template: targetRack.value.color,
                values: unloadValues.value
            }
        });

        if (res.message) {
            const data = res.message;
            refreshOvenData();
            frappe.msgprint(__('Slab unloaded successfully'));
            if (data.finish_results && data.finish_results.work_order) {
                await transfer_to_next_process(data.finish_results.work_order, data.finish_results.job_card_qty);
            }
        }
    } catch (e) {
        console.error(e);
    }

    showUnloadModal.value = false;
    targetRack.value = null;
}


async function confirmLoad() {
    if (!targetRack.value || !ovenData.value) {
        return;
	}

    prepareOvenOperation();

    const res = await frappe.call({
        method: 'erpnext.manufacturing.doctype.oven.api.load_slab_into_oven',
        args: {
            oven_op: ovenOperation.value,
            job_card: jobCardNumber.value
        }
    })

    if (res && res.message) {
        frappe.show_alert({message: __('Slab loaded and heating started'), indicator: 'green'});
        refreshOvenData();
        get_slabs_ready_for_heating();
    }

    // remove slab from incoming list or clear selected if single Job Card
    if (Array.isArray(currentSlab.value)) {
        const idx = currentSlab.value.findIndex(s => s.name === selectedSlab.value.name);
        if (idx !== -1) currentSlab.value.splice(idx, 1);
    }
    selectedSlab.value = null;

    closeModal();
}

function closeModal() {
    showMeasureModal.value = false;
    targetRack.value = null;
}

function editTemperatures() {
    const fields = [
        { label: 'Upper Shelf (°C)', fieldname: 'upper', fieldtype: 'Int', default: ovenTemps.value.upper },
        { label: 'Lower Shelf (°C)', fieldname: 'lower', fieldtype: 'Int', default: ovenTemps.value.lower }
    ];

    frappe.prompt(fields, (values) => {
        if (!ovenData.value) return;

        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'Oven',
                name: ovenData.value.name,
                fieldname: {
                    slab_top_temp: values.upper,
                    slab_bottom_temp: values.lower
                }
            }
        }).then(() => refreshOvenData());

    }, __('Update Oven Temperatures'), __('Update'));
}

function rackClasses(rack) {
    if (rack.state === 'Heating') return 'rack-card curing';
    if (rack.state === 'Overheat') return 'rack-card overheat';
    if (!rack.is_operational) return 'rack-card maintenance';
    return 'rack-card empty';
}

// const oven = get_oven_details(work_context.assigned_station);
const ovenOperation = ref({});

function prepareOvenOperation() {
    if (!ovenData.value || !selectedSlab.value || !targetRack.value) return;

    ovenOperation.value = {
        doctype: 'Oven Operation',
        oven: ovenData.value.name,
        date: frappe.datetime.now_datetime(),
        shift: work_context.assigned_shift,
        slab: selectedSlab.value.name,
        slab_color: selectedSlab.value.template,
        oven_rack: targetRack.value.name,
        upper_shelf_temp: ovenTemps.value.upper,
        lower_shelf_temp: ovenTemps.value.lower,
        top_left_vertex: measurements.value.tl,
        top_edge_center: measurements.value.tm,
        top_right_vertex: measurements.value.tr,
        right_edge_centre: measurements.value.rm,
        bottom_right_vertex: measurements.value.br,
        bottom_edge_centre: measurements.value.bm,
        bottom_left_vertex: measurements.value.bl,
        left_edge_centre: measurements.value.lm,
        remarks: ''
    };
}



frappe.realtime.on('slab_checkout', (slab) => {
    get_slabs_ready_for_heating();
});

</script>

<template>
    <div class="page-card d-flex">
        <!-- Left: Incoming Slabs -->
        <div style="width:540px;" class="pr-4 border-right">
            <h5 class="mb-3 d-flex align-items-center">
                {{ __('Incoming Slabs') }}
            </h5>
            <div class="text-muted small mb-3" v-if="currentSlab && currentSlab.length">
                {{ __('Select a slab to load into an empty rack.') }}
            </div>

            <div class="incoming-list">
                <div v-if="loadingSlab" class="text-center p-4">
                    <div class="spinner-border spinner-border-sm text-muted" role="status"></div>
                </div>
                <div v-else-if="jobCardNumber && !selectedSlab" class="text-muted small text-center p-4 border rounded bg-light">
                    {{ __('No slab found for Job Card') }} {{ jobCardNumber }}
                </div>
                <div v-else-if="!jobCardNumber && (!currentSlab || !currentSlab.length)" class="text-muted small text-center p-4 border rounded bg-light">
                    {{ __('No slabs are ready for heating right now.') }}
                </div>
                <TransitionGroup name="list" tag="div" v-else>
                    <div v-for="(slab, index) in (jobCardNumber ? [selectedSlab] : currentSlab)" :key="slab?.name"
                        class="incoming-item mb-2 p-3 d-flex align-items-center border rounded"
                        :class="{ 'selected': selectedSlab && selectedSlab.name === slab?.name, 'cursor-pointer': jobCardNumber || !index }"
                        @click="selectSlab(slab, index)">
                        <div v-if="slab" class="slab-container" :key="updateKey">
                            <div class="slab-thumbnail mr-3"></div>
                            <div class="flex-fill">
                                <div class="font-weight-bold small">{{ slab.name }}</div>
                                <div class="text-muted small">
                                    {{ slab.template }}
                                </div>
                            </div>
                            <div class="text-muted">
                                <span class="fa fa-arrow-right"></span>
                            </div>
                        </div>
                    </div>
                </TransitionGroup>
            </div>
        </div>

        <!-- Center: Oven Monitor -->
        <div class="flex-fill pl-4">
            <div class="border-bottom d-flex justify-content-between pb-2">
                <div>
                    <h4 class="mb-1">{{ __('Oven') }}: {{ oven?.name }} <span class="text-muted mr-2 ml-2">|</span> {{
                        __('Line') }}: {{ oven?.line }} <span class="text-muted mr-2 ml-2">|</span> {{ formattedDate }} <span
                        class="text-muted mr-2 ml-2">|</span> {{ formattedTime }}</h4>
                    <div class="text-muted small mb-4">
                        {{ __('Manage curing process and rack assignments.') }}
                    </div>
                </div>

                <div class="ml-4 mb-3 d-flex align-items-center cursor-pointer" @click="editTemperatures"
                    title="Click to update">
                    <div class="temp-badge mr-3">
                        <span class="text-muted small mr-1">{{ __('Upper') }}:</span>
                        <span class="font-weight-bold temp-text">{{ ovenTemps.upper }}°C</span>
                    </div>
                    <div class="temp-badge">
                        <span class="text-muted small mr-1">{{ __('Lower') }}:</span>
                        <span class="font-weight-bold temp-text">{{ ovenTemps.lower }}°C</span>
                    </div>
                </div>

                <!-- <div class="d-flex mb-4 justify-content-end align-items-center">
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#b0b8bf; width:1rem; height:1rem;"></span>{{ __('Empty') }}
                    </span>
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#2bc63b; width:1rem; height:1rem;"></span>{{ __('Curing') }}
                    </span>
                    <span class="small mr-4 d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#ef1e3f; width:1rem; height:1rem;"></span>{{ __('Overheating') }}
                    </span>
                    <span class="small d-flex align-items-center">
                        <span class="mr-2 border rounded d-flex"
                            style="background:#77afe6; width:1rem; height:1rem;"></span>{{ __('Maintenance') }}
                    </span>
                </div> -->
            </div>

            <div class="rack-grid d-flex flex-wrap pt-5">
                <div v-for="rack in racks" :key="rack.slot" :class="rackClasses(rack)" class="mb-3 mr-3 p-3 rounded"
                    style="position: relative;"
                    @click="rack.state === 'Heating' || rack.state === 'Overheat' ? unload_slab_from_rack(rack) : loadIntoRack(rack)">
                    <div v-if="rack.state === 'Overheat'" class="warning-icon pulse-icon">
                        <span class="fa fa-exclamation-circle text-danger"></span>
                    </div>
                    <div class="strong mb-1" style="position: absolute;">{{ rack.slot }}</div>
                    <div class="d-flex align-items-center justify-content-center flex-fill">
                        <!-- empty -->
                        <div v-if="rack.state === 'Idle' && rack.is_operational" class="text-center text-muted">
                            <div class="mb-3"><span class="fa fa-inbox" style="font-size:1.5rem;"></span></div>
                            <div class="font-weight-bold">{{ __('LOAD HERE') }}</div>
                        </div>
                        <!-- curing -->
                        <div v-else-if="(rack.state === 'Heating' || rack.state === 'Overheat') && rack.is_operational"
                            class="text-center">
                            <div class="font-weight-bold mb-1">{{ rack.slab }}</div>
                            <div class="text-muted small mb-1">{{ rack.color }}</div>
                            <div class="text-muted small" v-if="rack.state === 'Heating'">
                                <span class="fa fa-clock-o mr-1"></span>{{ rack.time_text }}
                            </div>
                            <div class="text-danger strong" v-if="rack.state === 'Overheat'">
                                <span class="fa fa-thermometer-full mr-1 pulse-icon"></span>{{ rack.time_text }}
                            </div>
                        </div>
                        <!-- overheat -->
                        <!-- <div v-else-if="rack.state === 'Overheat' && rack.is_operational" class="text-center">
                            <div class="font-weight-bold mb-1">{{ rack.slab }}</div>
                            <div class="text-muted small mb-1">{{ rack.color }}</div>
                            <div class="text-danger small">
                                <span class="fa fa-thermometer-full mr-1"></span>{{ rack.time_text }}
                            </div>
                        </div> -->
                        <!-- maintenance -->
                        <div v-else-if="!rack.is_operational" class="text-center text-muted">
                            <div class="mb-2">
                                <span class="fa fa-exclamation-triangle mr-1" style="font-size:1.4rem;"></span>
                            </div>
                            <div class="font-weight-bold">{{ __('MAINTENANCE') }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Slab Measure Modal Overlay -->
    <div v-if="showMeasureModal" class="modal-backdrop-custom d-flex align-items-center justify-content-center">
        <div class="modal-card shadow-lg rounded p-4" style="width: 600px;">
            <h5 class="mb-3">{{ __('Verify Dimensions') }}</h5>
            <p class="text-muted small mb-5">
                {{ __('Measure 8 points on the slab before loading.') }}
                <br>
                <!-- {{ selectedSlab }} &rarr; {{ targetRack?.slot }} -->
            </p>

            <div class="measure-container d-flex justify-content-center align-items-center mb-4">
                <!-- The geometric representation -->
                <div class="slab-rect position-relative border">
                    <!-- Top Left -->
                    <input id="pos-tl" type="number" v-model.number="measurements.tl"
                        class="meas-input pos-tl form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Top -->
                    <input id="pos-tm" type="number" v-model.number="measurements.tm"
                        class="meas-input pos-tm form-control input-sm" @click="$event.target.select()">
                    <!-- Top Right -->
                    <input id="pos-tr" type="number" v-model.number="measurements.tr"
                        class="meas-input pos-tr form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Right -->
                    <input id="pos-rm" type="number" v-model.number="measurements.rm"
                        class="meas-input pos-rm form-control input-sm" @click="$event.target.select()">
                    <!-- Bottom Right -->
                    <input id="pos-br" type="number" v-model.number="measurements.br"
                        class="meas-input pos-br form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Bottom -->
                    <input id="pos-bm" type="number" v-model.number="measurements.bm"
                        class="meas-input pos-bm form-control input-sm" @click="$event.target.select()">
                    <!-- Bottom Left -->
                    <input id="pos-bl" type="number" v-model.number="measurements.bl"
                        class="meas-input pos-bl form-control input-sm" @click="$event.target.select()">
                    <!-- Mid Left -->
                    <input id="pos-lm" type="number" v-model.number="measurements.lm"
                        class="meas-input pos-lm form-control input-sm" @click="$event.target.select()">

                    <div class="text-center strong mt-5 pt-5">{{ selectedSlab.name }}</div>
                </div>
            </div>

            <div class="d-flex justify-content-end pt-4">
                <button class="btn btn-secondary mr-2" @click="closeModal">{{ __('Cancel') }}</button>
                <button class="btn btn-primary" @click="confirmLoad">{{ __('Load Slab') }}</button>
            </div>
        </div>
    </div>

    <!-- Slab Unload Modal Overlay -->
    <div v-if="showUnloadModal" class="modal-backdrop-custom d-flex align-items-center justify-content-center">
        <div class="modal-card shadow-lg rounded p-4" style="width: 500px;">
            <h5 class="mb-3">{{ __('Unload Slab') }}</h5>
            <div class="text-muted small mb-4">
                {{ targetRack?.slab }} &bull; {{ targetRack?.color }}
            </div>

            <div class="form-group mb-3">
                <label class="small text-muted">{{ __('Slab Top Temperature') }} <span
                        class="text-danger">*</span></label>
                <input type="number" v-model.number="unloadValues.slab_top_temp" class="form-control">
            </div>
            <div class="form-group mb-3">
                <label class="small text-muted">{{ __('Slab Bottom Temperature') }} <span
                        class="text-danger">*</span></label>
                <input type="number" v-model.number="unloadValues.slab_bottom_temp" class="form-control">
            </div>
            <div class="form-group mb-4">
                <label class="small text-muted">{{ __('Remarks') }}</label>
                <textarea v-model="unloadValues.remarks" class="form-control" rows="3"></textarea>
            </div>

            <div class="d-flex justify-content-end">
                <button class="btn btn-secondary mr-2" @click="showUnloadModal = false">{{ __('Cancel') }}</button>
                <button class="btn btn-primary" @click="confirmUnload">{{ __('Confirm Unload') }}</button>
            </div>
        </div>
    </div>

</template>

<style scoped>
.page-card {
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.incoming-item {
    background-color: var(--fg-color, #f8f9fa);
    border-color: var(--border-color) !important;
    transition: all 0.2s ease;
}

.incoming-item:hover {
    border-color: var(--primary-color) !important;
}

.incoming-item.selected {
    background-color: var(--control-bg-on-gray, #e2edff);
    border-color: var(--primary-color) !important;
}

.rack-card {
    border: 2px dashed var(--border-color, #ced4da);
    background: var(--control-bg, #f8f9fa);
    width: 225px;
    height: 120px;
    display: flex;
    flex-direction: column;
    transition: all 0.2s ease;
}

.rack-card:hover {
    cursor: pointer;
    border-color: var(--primary-color, #74c0fc) !important;
    box-shadow: 0 0 0 3px rgba(116, 192, 252, 0.4);
}

.rack-card.empty {
    border-style: dashed;
    border-color: var(--border-color, #ced4da);
    background: var(--control-bg, #f8f9fa);
}

.rack-card.curing {
    border-style: solid;
    border-color: #28a745;
    background: var(--success-50, #d4f8d4);
}

.rack-card.overheat {
    border-style: solid;
    border-color: #dc3545;
    background: var(--error-50, #f8d7da);
}

.rack-card.maintenance {
    border-style: dashed;
    border-color: #6c757d;
    background: var(--blue-50, #e2edff);
}

.temp-badge {
    background: var(--bg-color, #fff);
    border: 1px solid var(--border-color, #dee2e6);
    padding: 4px 10px;
    border-radius: 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    cursor: pointer;
}

.modal-backdrop-custom {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1050;
}

.modal-card {
    background: var(--card-bg, #fff);
    color: var(--text-color);
}

.slab-rect {
    width: 300px;
    height: 180px;
    /* background: #f1f3f5; */
    border: 3px solid var(--text-color, #333) !important;
}

.meas-input {
    position: absolute;
    width: 60px;
    text-align: center;
    padding: 2px;
    font-size: 12px;
}

.temp-text {
    color: var(--text-success, green);
}

.incoming-list {
    width: 250px;
}

.slab-container {
    display: flex;
    width: 100%;
    align-items: center;
}

.slab-thumbnail {
    width: 32px;
    height: 32px;
    border-radius: 4px;
    background: var(--gray-800, #1f2937);
}

/* Positions for inputs */
/* Corners */
.pos-tl {
    top: -15px;
    left: -30px;
}

.pos-tr {
    top: -15px;
    right: -30px;
}

.pos-bl {
    bottom: -15px;
    left: -30px;
}

.pos-br {
    bottom: -15px;
    right: -30px;
}

/* Mids - centered on edges */
/* Horizontal mids: left: 50% - half width (30px) */
.pos-tm {
    top: -15px;
    left: calc(50% - 30px);
}

.pos-bm {
    bottom: -15px;
    left: calc(50% - 30px);
}

/* Vertical mids: top: 50% - half height (~15px for input height approx) */
/* Actually input height is maybe 30px? let's center vertically */
.pos-lm {
    top: calc(50% - 15px);
    left: -30px;
}

.pos-rm {
    top: calc(50% - 15px);
    right: -30px;
}

.list-enter-active,
.list-leave-active {
    transition: all 0.2s ease-out;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateY(30px);
}

@keyframes pulse {
    0% {
        transform: scale(1);
    }

    50% {
        transform: scale(1.2);
    }

    100% {
        transform: scale(1);
    }
}

.pulse-icon {
    animation: pulse 1s infinite;
    display: inline-block;
}

.warning-icon {
    position: absolute;
    top: -10px;
    right: -10px;
    background: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    border: 2px solid #e03636 !important
}
</style>
