<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue';

const jobCard = ref(null);
const batchNo = ref('');
const colour = ref('');
const phase = ref('Preparation Phase');
const ingredients = ref([]);
const loadingIngredients = ref(true);
const error = ref(null);
const additionalIngredients = ['silane', 'catalyst', 'hardener'];
const jobCardSubmitted = ref(false);
const preparedQty = ref(0);
const stockEntryName = ref('');
const transferredQty = ref(0);
const transferSuccess = ref(false);
const nextWorkOrder = ref('');
const bomQty = ref(0);
const bomUOM = ref('');
const selectedMixer = ref('');
const mixersList = ref([]);
const jobcardsQueue = ref([]);
const productionLine = ref(null);
const currentLine = ref(null);
const pollingInterval = ref(null);
const isDistributionBusy = ref(false);
const displayQty = ref(0);
const isProcessing = ref(false);
const showJobCardQueue = ref(false);

// downstream alerts (dummy)
const alerts = ref([
    {
        type: 'QUALITY ISSUE',
        title: 'Uneven pressure distribution detected',
        source: 'Presser',
        batch: 'SLB-2024-8830',
        time: '02:46 PM',
        tone: 'danger'
    },
    {
        type: 'MACHINE PROBLEM',
        title: 'Temperature variance > 5%',
        source: 'Cooler',
        batch: null,
        time: '02:19 PM',
        tone: 'warning'
    }
]);

const work_context = reactive({
    role: "Mixer Operator",
    assigned_line: "",
    assigned_shift: ""
});

const mixingStarted = ref(false);
const mixingStartTime = ref(null);
const mixingElapsed = ref(0);
const mixingTimerHandle = ref(null);
const mixingReady = ref(false);
const inputsReadonly = computed(() => mixingReady.value || mixingStarted.value);

const formattedMixingTime = computed(() => {
    const h = String(Math.floor(mixingElapsed.value / 3600)).padStart(2, '0');
    const m = String(Math.floor((mixingElapsed.value % 3600) / 60)).padStart(2, '0');
    const s = String(mixingElapsed.value % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
});

const formatDateTime = (dateStr) => {
    if (!dateStr) return '';
    const userDate = frappe.datetime.str_to_user(dateStr);
    return userDate;
}

const startedAtLabel = computed(() =>
    mixingStartTime.value
        ? frappe.datetime.str_to_user(mixingStartTime.value)
        : ''
);

const allAdditionalIngredientsAdded = computed(() => {
    return ingredients.value
        .filter(ing => isAdditionalIngredient(ing.name))
        .every(ing => ing.is_added);
});

const isMixerSelected = computed(() => !!selectedMixer.value);

const fetchWorkContext = async () => {
    const mixerContext = await frappe.call({
        method: "erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_station_context",
    });

    if (mixerContext.message) {
        work_context.role = mixerContext.message.current_user.designation;
        work_context.assigned_line = mixerContext.message.current_user.production_line;
        work_context.assigned_shift = mixerContext.message.current_user.attendance_shift;
        showJobCardQueue.value = !!mixerContext.message.show_job_card_queue;
    }
}

async function getMixerState() {
    const stateRes = await frappe.call({
        method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_state',
        args: { job_card: jobCard.value },
    });

    return stateRes;
};

// actions
onMounted(async () => {
    jobCard.value = null;
    await fetchWorkContext();

    currentLine.value = work_context.assigned_line;

    await loadData();

    document.addEventListener("refresh-mixer-station", async () => {
        await loadData();
    });

    frappe.realtime.on('refresh_mixer_station', () => {
        fetchPollingData();
    });

    frappe.realtime.on('slab_checkout', (slab) => {
        if (slab.child_line !== currentLine.value || slab.status !== 'Distribution') {
            return;
        }

        fetchPollingData();
    });
});

async function loadData() {
    loadingIngredients.value = true;
    error.value = null;

    try {
        await fetchPollingData(fetch_queue=1, fetch_status=1, fetch_mixers=1)

        let activeJob = null;
        if (selectedMixer.value) {
            const selectedMixerObj = mixersList.value.find(m => m.name === selectedMixer.value);
            if (selectedMixerObj && selectedMixerObj.active_job_card) {
                activeJob = selectedMixerObj.active_job_card;
            }
        }

        if (activeJob) {
            jobCard.value = activeJob;
        } else if (jobcardsQueue.value.length > 0) {
            const queueForMixer = jobcardsQueue.value.filter(jc => !jc.mixer_number || jc.mixer_number === selectedMixer.value);
            if (queueForMixer.length > 0) {
                jobCard.value = queueForMixer[0].name;
            } else {
                jobCard.value = jobcardsQueue.value[0].name;
            }
        } else {
            jobCard.value = null;
        }

        if (!jobCard.value) {
            mixingReady.value = false;
            mixingStarted.value = false;
            mixingStartTime.value = null;
            displayQty.value = 0;
            jobCardSubmitted.value = false;
            ingredients.value = [];
            batchNo.value = '';
            loadingIngredients.value = false;
            return;
        }

        const stateRes = await getMixerState();

        const s = stateRes.message || {};
        mixingReady.value = !!s.mixer_materials_confirmed;
        mixingStarted.value = !!s.mixer_started;
        mixingStartTime.value = s.mixer_start_time;
        selectedMixer.value = selectedMixer.value || s.mixer_number || '';
        displayQty.value = s.display_qty;

        jobCardSubmitted.value = !!s.job_card_submitted;
        if (jobCardSubmitted.value) {
            preparedQty.value = s.prepared_qty || 0;
            stockEntryName.value = s.stock_entry_name || '';
            transferredQty.value = s.transferred_qty_to_next || 0;
            transferSuccess.value = s.transfer_complete || false;
        }

        if (mixingStarted.value && mixingStartTime.value) {
            const start = frappe.datetime.str_to_obj(mixingStartTime.value);
            const now = frappe.datetime.now_datetime();
            const diffSeconds = (new Date(now) - new Date(start)) / 1000;
            mixingElapsed.value = Math.max(0, Math.floor(diffSeconds));

            if (mixingTimerHandle.value) clearInterval(mixingTimerHandle.value);
            mixingTimerHandle.value = setInterval(() => {
                mixingElapsed.value += 1;
            }, 1000);
        } else {
            mixingElapsed.value = 0;
            if (mixingTimerHandle.value) {
                clearInterval(mixingTimerHandle.value);
                mixingTimerHandle.value = null;
            }
        }

        if (jobCard.value) {
            const jc = await frappe.db.get_doc('Job Card', jobCard.value);
            // productionLine.value = jc.production_line;
            productionLine.value = currentLine.value;
            if (jc.bom_no) {
                const bom_elements = jc.bom_no.split("-");
                batchNo.value = `${bom_elements[1]}-${bom_elements[2]}`.trim();
            }
        }

        const r = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_ingredients',
            args: {
                job_card: jobCard.value
            }
        });

        if (r.message) {
            bomUOM.value = r.message[0].jc_bom_uom;
        }

        ingredients.value = (r.message || []).map(item => {
            const name = item.item_name || '';
            const lower = name.toLowerCase();
            const is_additional = additionalIngredients.some(s => lower.includes(s));

            return {
                name,
                standard: `${item.stock_uom_qty} ${item.stock_uom}`,
                unit: item.stock_uom,
                qty: item.stock_uom_qty,
                item_code: item.item_code,
                is_added: !!item.additional_ingredients_added,
            };
        });

        if (jobCardSubmitted.value) {
            const jc = await frappe.db.get_doc('Job Card', jobCard.value);
            preparedQty.value = jc.total_completed_qty || jc.for_quantity || s.prepared_qty || 0;
            stockEntryName.value = s.stock_entry_name || '';
            transferredQty.value = s.transferred_qty_to_next || 0;
            // transferSuccess.value = (preparedQty.value - transferredQty.value) <= 0.001;
            transferSuccess.value = displayQty.value <= 0.001;
            await loadBomQty();
        }
    }
    catch (e) {
        error.value = e.message || e;
        frappe.msgprint(__('Failed to load BOM ingredients'));
    }
    finally {
        loadingIngredients.value = false;
    }
}

async function confirmAndStartMixing() {
    if (!allAdditionalIngredientsAdded.value) {
        frappe.msgprint(__('Mark all additional ingredients as Added first.'));
        return;
    }
    frappe.confirm(
        __('Do you want to confirm the materials and start mixing?'),
        async () => {
            isProcessing.value = true;
            try {
                const payload = ingredients.value.map(ing => ({
                    item_code: ing.item_code,
                    qty: ing.qty,
                    unit: ing.unit,
                    is_added: ing.is_added,
                }));

                const r = await frappe.call({
                    method: 'erpnext.manufacturing.page.mixer_station.mixer_station.confirm_and_start_mixing',
                    args: {
                        job_card: jobCard.value,
                        ingredients: JSON.stringify(payload),
                        bom_uom: bomUOM.value,
                    }
                });

                await loadData();

                mixingReady.value = true;
                mixingStarted.value = true;
                mixingStartTime.value = frappe.datetime.now_datetime();

                mixingElapsed.value = 0;
                if (mixingTimerHandle.value) {
                    clearInterval(mixingTimerHandle.value);
                }
                mixingTimerHandle.value = setInterval(() => {
                    mixingElapsed.value += 1;
                }, 1000);
            } catch (e) {
                frappe.show_alert({
                    message: __('Failed to confirm materials'),
                    indicator: 'red'
                });
            } finally {
                isProcessing.value = false;
            }
        },
    );
}

// async function toggleReady() {
//     if (mixingStarted.value) {
//         return;
//     }
//     if (!allAdditionalIngredientsAdded.value) {
//         frappe.msgprint(__('Mark all additional ingredients as Added first.'));
//         return;
//     }
//     frappe.confirm(
//         __('Do you want to confirm the materials?'),
//         async () => {
//             try {
//                 const payload = ingredients.value.map(ing => ({
//                     item_code: ing.item_code,
//                     qty: ing.qty,
//                     unit: ing.unit,
//                     is_added: ing.is_added,
//                 }));

//                 const r = await frappe.call({
//                     method: 'erpnext.manufacturing.page.mixer_station.mixer_station.confirm_materials',
//                     args: {
//                         job_card: jobCard.value,
//                         ingredients: JSON.stringify(payload),
//                         bom_uom: bomUOM.value,
//                     }
//                 });

//                 mixingReady.value = true;
//                 frappe.msgprint(
//                     __('Materials confirmed. Stock Entry {0} created.', [r.message.stock_entry])
//                 );
//             } catch (e) {
//                 frappe.msgprint(
//                     __('Failed to confirm materials')
//                 );
//             }
//         },
//     );
// }

async function selectMixerTab(mixerName) {
    if (selectedMixer.value !== mixerName) {
        selectedMixer.value = mixerName;

        // Find selected mixer to read its production line and active job card
        const selectedMixerObj = mixersList.value.find(m => m.name === mixerName);
        if (selectedMixerObj) {
            currentLine.value = selectedMixerObj.production_line;
            jobCard.value = null;
        }

        await loadData();
    }
}

// async function startMixing() {
//     if (!mixingReady.value) {
//         frappe.msgprint(__('Confirm materials before starting mixing.'));
//         return;
//     }
//     frappe.confirm(
//         __('Start mixing now?'),
//         async () => {
//             isProcessing.value = true;
//             try {
//                 await frappe.call({
//                     method: 'erpnext.manufacturing.page.mixer_station.mixer_station.start_mixing',
//                     args: { job_card: jobCard.value }
//                 });
//                 mixingStarted.value = true;
//                 mixingStartTime.value = frappe.datetime.now_datetime();

//                 mixingElapsed.value = 0;
//                 if (mixingTimerHandle.value) {
//                     clearInterval(mixingTimerHandle.value);
//                 }
//                 mixingTimerHandle.value = setInterval(() => {
//                     mixingElapsed.value += 1;
//                 }, 1000);
//             }
//             catch (e) {
//                 frappe.show_alert({
//                     message: __('Failed to start Job Card for mixing'),
//                     indicator: 'red'
//                 });
//             } finally {
//                 isProcessing.value = false;
//             }
//         },
//         () => {
//             frappe.show_alert({
//                 message: __('Mixing was not started.'),
//                 indicator: 'red'
//             });
//         }
//     );
// }

async function finishAndDischarge() {
    if (mixingTimerHandle.value) {
        clearInterval(mixingTimerHandle.value);
        mixingTimerHandle.value = null;
    }
    try {
        isProcessing.value = true;
        const jc = await frappe.db.get_doc('Job Card', jobCard.value);
        const completed_qty = jc.for_quantity || 0;
        const result = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.finish_mixing',
            args: {
                job_card: jobCard.value,
                completed_qty,
            },
            freeze: true,
            freeze_message: __('Completing Job Card...')
        });
        mixingStarted.value = false;
        mixingStartTime.value = null;
        mixingElapsed.value = 0;
        mixingReady.value = false;

        jobCardSubmitted.value = true;
        preparedQty.value = result.message.job_card_qty;
        stockEntryName.value = result.message.stock_entry;
        bomQty.value = result.message.bom_qty || 0;
        nextWorkOrder.value = result.message.next_work_order || '';
        // transferredQty.value = 0;
        displayQty.value = result.message.display_qty;
        transferSuccess.value = result.message.transfer_complete;

        await loadData();
    }
    catch (error) {
        const errorMsg = error.message ||
            (error._server_messages?.[0]?.message) ||
            JSON.stringify(error);

        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: `Failed to complete Job Card:<br><pre>${errorMsg}</pre>`
        });
    } finally {
        isProcessing.value = false;
    }
}

function haltFromAlert(alert) {
    frappe.msgprint(__('Production halted due to alert: {0}', [alert.title]));
}

function ignoreAlert(index) {
    const alert = alerts.value[index];
    frappe.msgprint(__('Alert ignored: {0}', [alert.title]));
    alerts.value.splice(index, 1);
}

function isAdditionalIngredient(name) {
    if (!name) return false;
    const ing = name.toString().toLowerCase();
    return additionalIngredients.some(s => ing.includes(s));
}

function openAddMaterials() {
    const d = new frappe.ui.Dialog({
        title: __('Add Raw Materials'),
        size: 'small',
        fields: [
            {
                fieldtype: 'Link',
                label: __('Job Card'),
                fieldname: 'job_card',
                options: 'Job Card',
                default: jobCard.value,
                read_only: 1,
                reqd: 1
            },
            {
                fieldtype: 'Link',
                label: __('Raw Material'),
                fieldname: 'raw_material',
                options: 'Item',
                reqd: 1,
                get_query() {
                    return {
                        filters: {
                            "item_group": "Raw Material",
                            "item_name": "Resin"
                        }
                    };
                }
            },
            {
                fieldtype: 'Float',
                label: __('Quantity'),
                fieldname: 'qty',
                reqd: 1,
                precision: 2
            }
        ],
        primary_action_label: __('Add'),
        primary_action(values) {
            frappe.call({
                method: 'erpnext.manufacturing.page.mixer_station.mixer_station.quick_add_raw_materials',
                args: values,
                callback(r) {
                    if (r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            message: `
                                <div class="d-flex justify-content-between" style="text-align: center;">
                                    <b>${values.raw_material}
                                    <span style="color: #28a745;">(+${values.qty} kg)</span><br></b>
                                    <a href="/app/stock-entry/${r.message.stock_entry}">${r.message.stock_entry}</a><br>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        if (cur_frm && cur_frm.doc.name === values.job_card) {
                            cur_frm.reload_doc();
                        }
                        d.hide();
                    }
                },
                error(e) {
                    frappe.show_alert({
                        message: __('Failed to add raw materials'),
                        indicator: 'red'
                    });
                }
            });

            d.hide();
        },
        primary_action_condition(values) {
            return values.job_card && values.raw_material && values.qty > 0;
        }
    });
    d.set_secondary_action_label(__('Cancel'));
    d.set_secondary_action(() => d.hide());
    d.show();
}

async function transferToFGWarehouse() {
    if (!getCanTransfer.value) {
        frappe.msgprint(__('Insufficient qty ({0}) for BOM requirement ({1})',
            [getDisplayQty.value.toLocaleString(), bomQty.value.toLocaleString()]));
        return;
    }

    try {
        isProcessing.value = true;
        const jc = await frappe.db.get_doc('Job Card', jobCard.value);
        const workOrder = jc.work_order;
        const qty = bomQty.value

        if (!workOrder) {
            frappe.msgprint(__('Work Order required from Job Card'));
            return;
        }

        const result = await frappe.call({
            method: 'erpnext.manufacturing.doctype.operation.api.transfer_to_next_process',
            args: {
                current_work_order: workOrder,
                qty: bomQty.value,
                process: 'Mixing',
                mixer_number: selectedMixer.value
            },
            freeze: true,
            freeze_message: __('Transferring to Distribution')
        });

        transferredQty.value += result.message.qty_transferred_updated || 0;
        transferSuccess.value = result.message.transfer_complete || false;

        // Refresh full state
        const refreshedState = await getMixerState();

        // Reset the local storage with data from the server
        localStorage.removeItem(`mixer_status_${selectedMixer.value}`);

        preparedQty.value = refreshedState.message.prepared_qty;
        transferredQty.value = refreshedState.message.transferred_qty_to_next;
        displayQty.value = refreshedState.message.display_qty;
        transferSuccess.value = refreshedState.message.transfer_complete;

        await loadData();

        // if (getDisplayQty.value <= 0) {
        //     transferSuccess.value = true;
        // }
    } catch (error) {
        frappe.show_alert({
            message: __('Transfer failed'),
            indicator: 'red'
        });
    } finally {
        isProcessing.value = false;
    }
}

const getDisplayQty = computed(() => {
    // return parseFloat((preparedQty.value - transferredQty.value).toFixed(3));
    return Number(displayQty.value || 0);
});

const getCanTransfer = computed(() => {
    const display = getDisplayQty.value;
    const bom = parseFloat(bomQty.value.toFixed(2));
    return display >= bom && !isDistributionBusy.value;
});

async function loadBomQty() {
    try {
        const jc = await frappe.db.get_doc('Job Card', jobCard.value);
        const result = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_next_process_bom_qty',
            args: { mixing_work_order: jc.work_order }
        });

        bomQty.value = result.message.bom_qty;
        nextWorkOrder.value = result.message.next_work_order;
    }
    catch (error) {
        console.error('BOM qty load failed:', error);
        bomQty.value = 0;
    }
}

async function fetchPollingData(fetch_queue=1, fetch_status=1, fetch_mixers=1) {
    try {
        const r = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_polling_data',
            args: {
                production_line: currentLine.value,
                fetch_queue: fetch_queue,
                fetch_status: fetch_status,
                fetch_mixers: fetch_mixers
            }
        });

        if (r.message) {
            if (r.message.queue) {
                jobcardsQueue.value = r.message.queue;
            }
            if (r.message.distribution_status) {
                isDistributionBusy.value = r.message.distribution_status.busy || false;
            }
            if (r.message.mixers) {
                updateMixersList(r.message.mixers);
            }
        }
    } catch (e) {
        console.error('Failed to fetch polling data:', e);
    }
}

function updateMixersList(newMixers) {
    if (!newMixers) return;
    
    for (const nm of newMixers) {
        if (nm.status === 'Finished') {
            localStorage.setItem(`mixer_status_${nm.name}`, 'Finished');
        } else {
            const savedStatus = localStorage.getItem(`mixer_status_${nm.name}`);
            if (savedStatus === 'Finished') {
                nm.status = 'Finished';
            }
        }
    }

    if (!mixersList.value?.length) {
        mixersList.value = newMixers;
    } else {
        for (const nm of newMixers) {
            const existing = mixersList.value.find(m => m.name === nm.name);
            if (existing) {
                existing.status = nm.status;
                existing.active_job_card = nm.active_job_card;
            } else {
                mixersList.value.push(nm);
            }
        }
    }

    if (!selectedMixer.value && mixersList.value.length > 0) {
        const firstMixerInLine = mixersList.value.find(m => m.production_line === currentLine.value) || mixersList.value[0];
        if (firstMixerInLine) {
            selectedMixer.value = firstMixerInLine.name;
            currentLine.value = firstMixerInLine.production_line;
        }
    }
}

function selectJobCard(name) {
    if (name === jobCard.value) return;
    frappe.set_route('mixer-station', 'Mixing', name);
    // Reload the page to refresh all data for the new Job Card
    window.location.reload();
}
</script>

<template>
    <div class="page-card p-0 d-flex h-100 w-100">
        <!-- Sidebar: Queue -->
        <div class="queue-sidebar border-right p-3" style="width: 320px; overflow-y: auto;" v-if="showJobCardQueue">
            <h5 class="mb-3 font-weight-bold text-center border-bottom pb-2">
                {{ __('Mixing Queue') }}
            </h5>

            <div v-if="jobcardsQueue.length === 0" class="text-muted text-center py-4 rounded border empty-queue-state">
                <span class="fa fa-inbox fa-2x mb-2 d-block text-muted-light"></span>
                {{ __('No Job cards in queue') }}
            </div>

            <div v-else>
                <div v-for="item in jobcardsQueue" :key="item.name" @click="selectJobCard(item.name)"
                    class="card mb-2 shadow-sm slab-card border-0" :class="{ 'active-card': item.name === jobCard }"
                    style="cursor: pointer;">
                    <div class="card-body p-3 d-flex flex-column justify-content-center align-items-start"
                        style="height: 5.5rem">
                        <div class="d-flex justify-content-between w-100 mb-1">
                            <h6 class="card-title mb-0 font-weight-bold">{{ item.name }}</h6>
                            <span class="badge border item-time-badge small">{{ item.status }}</span>
                        </div>
                        <div class="small text-muted mb-1 w-100">
                            <span class="fa fa-cubes mr-1"></span>{{ item.production_item }}
                        </div>
                        <div class="small text-muted">
                            <span class="fa fa-calendar mr-1"></span>
                            {{ formatDateTime(item.creation) }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content Wrapper -->
        <div class="d-flex flex-grow-1" style="overflow-x: auto;">
            <!-- Left + middle columns wrapper -->
            <div class="p-4" style="min-width: 600px; padding-top: 0 !important; flex: 1;">
                <!-- Top header -->
                <div class="mb-4">
                    <a href="javascript:history.back()" class="small text-muted">
                        &larr; {{ __('Back to Queue') }}
                    </a>
                </div>

                <!-- Tabs for Mixers -->
                <div v-show="mixersList.length > 1" class="mb-4 d-flex p-2 bg-light w-100" style="border-radius: 16px; gap: 0.5rem; overflow-x: auto;">
                    <div v-for="mixer in mixersList" :key="mixer.name"
                        class="text-center p-3 d-flex flex-column align-items-center justify-content-center border-0 flex-fill"
                        :class="[
                            selectedMixer === mixer.name ? 'bg-primary shadow text-white' :
                                (mixer.status === 'Finished' ? 'bg-success shadow text-white' : 'text-secondary'),
                            (mixingReady || mixingStarted) ? 'opacity-50' : ''
                        ]"
                        style="min-width: 120px; border-radius: 12px; transition: all 0.2s; cursor: pointer;"
                        @click="selectMixerTab(mixer.name)">

                        <div class="mb-2">
                            <i v-if="mixer.status === 'In Progress'" class="fa fa-spinner fa-pulse fa-2x" title="In Progress"></i>
                            <i v-else-if="mixer.status === 'Finished'" class="fa fa-check-circle fa-2x" title="Finished"></i>
                            <i v-else class="fa fa-cube fa-2x" title="Idle"></i>
                        </div>
                        <div class="font-weight-bold" style="font-size: 0.95rem;">{{ mixer.name }}</div>
                    </div>
                </div>

                <div class="d-flex align-items-center mb-4" v-if="jobCard">
                    <div>
                        <h2 class="mb-3">{{ batchNo }}</h2>
                        <div class="text-danger font-weight-bold">{{ jobCard }}</div>
                    </div>

                    <div class="ml-4">
                        <span class="badge badge-pill badge-light border px-3 py-2" style="font-size:1rem">
                            {{ phase }}
                        </span>
                    </div>
                </div> <!-- /header -->

                <div class="d-flex" v-if="jobCard">
                    <!-- Left: Raw Material Inputs -->
                    <div class="flex-fill mr-4" style="font-size: medium;">
                        <div class="mb-3">
                            <h3 class="mb-1">{{ __('Raw Material Inputs') }}</h3>
                            <div class="text-muted small">
                                {{ __('Review and adjust calculated quantities before mixing.') }}
                            </div>
                        </div>



                        <div v-if="loadingIngredients" class="text-center py-4">
                            <div class="spinner-border spinner-border-sm mr-2" role="status"></div>
                            {{ __('Loading BOM ingredients...') }}
                        </div>

                        <!-- Error -->
                        <!--<div v-else-if="error" class="alert alert-danger">
                        {{ error }}
                    </div>-->

                        <div v-else>
                            <div v-for="(ing, idx) in ingredients" :key="idx" class="mb-3 pb-2 border-bottom">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <div class="font-weight-bold">{{ ing.name }}</div>
                                        <div class="text-muted small">
                                            {{ __('Standard: {0}', [ing.standard]) }}
                                        </div>
                                    </div>
                                    <template v-if="isAdditionalIngredient(ing.name)">
                                        <div class="d-flex flex-column align-items-end">
                                            <label class="added-checkbox mb-1">
                                                <input type="checkbox" v-model="ing.is_added">
                                                <span class="added-text" :class="ing.is_added ? 'added' : 'not-added'">
                                                    {{ ing.is_added ? 'Added' : 'Not Added' }}
                                                </span>
                                            </label>
                                            <div v-if="ing.is_added" class="d-flex align-items-center">
                                                <input type="number" class="form-control text-right"
                                                    :readonly="inputsReadonly" :class="inputsReadonly ? 'bg-light' : ''"
                                                    style="width:120px;" v-model.number="ing.qty" />
                                                <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                            </div>
                                        </div>
                                    </template>
                                    <template v-else>
                                        <div class="d-flex align-items-center">
                                            <input type="number" class="form-control text-right"
                                                :readonly="inputsReadonly" :class="inputsReadonly ? 'bg-light' : ''"
                                                style="width:120px;" v-model.number="ing.qty" />
                                            <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                        </div>
                                    </template>
                                </div>
                            </div>

                        </div>
                    </div> <!-- /left column -->

                    <!-- Middle: Mixing card -->
                    <div style="width:300px;" class="pl-4 pt-4">
                        <!-- Ready to Mix state -->
                        <div v-if="!mixingStarted && !jobCardSubmitted" class="border rounded p-4 mb-3 text-center">
                            <div class="mb-2 text-success font-weight-bold">
                                {{ __('Ready to Mix?') }}
                            </div>
                            <div class="text-muted small mb-3">
                                {{ __('Confirm all materials are loaded and weighed correctly.') }}
                            </div>

                            <div class="mb-3">
                                <button
                                    :disabled="!isMixerSelected || !allAdditionalIngredientsAdded || mixingStarted || isProcessing"
                                    :class="!isMixerSelected || !allAdditionalIngredientsAdded || mixingStarted || isProcessing ? 'btn-disabled-pointer' : ''"
                                    class="btn btn-success btn-block py-3" @click="confirmAndStartMixing">
                                    <span v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></span>
                                    <span v-else :class="mixingReady ? 'fa fa-play mr-1' : 'fa fa-check mr-1'"></span>
                                    {{ __('Confirm Materials and Start Mixing') }}
                                </button>
                            </div>
                        </div>

                        <!-- Mixing in Progress state -->
                        <div v-else-if="mixingStarted && !jobCardSubmitted" class="border rounded p-4 mb-3 text-center"
                            style="background:#e8f8ec;">
                            <div
                                class="mb-2 text-success font-weight-bold d-flex justify-content-center align-items-center">
                                <span class="fa fa-spinner fa-spin mr-2"></span>
                                {{ __('Mixing in Progress') }}
                            </div>
                            <div class="display-4 font-weight-bold mb-3" style="font-size:2.5rem;">
                                {{ formattedMixingTime }}
                            </div>
                            <div class="d-flex flex-column gap-2 justify-content-center mb-3">
                                <button class="btn btn-success flex-fill" :disabled="isProcessing"
                                    @click="finishAndDischarge">
                                    <span v-if="isProcessing" class="fa fa-spinner fa-spin mr-1"></span>
                                    <span v-else class="fa fa-check mr-1"></span>
                                    {{ __('Finish & Discharge') }}
                                </button>
                                <button class="btn btn-outline-primary flex-fill mt-2 border border-dark"
                                    @click="openAddMaterials">
                                    <span class="fa fa-plus mr-1"></span>
                                    {{ __('Add Materials') }}
                                </button>
                            </div>

                            <div class="text-muted small mt-2">
                                {{ __('Started at {0}', [startedAtLabel]) }}
                            </div>
                        </div>

                        <div v-else-if="jobCardSubmitted" class="border rounded p-4 mb-3 text-center"
                            style="background:#fff3cd;">
                            <div
                                class="mb-3 text-warning font-weight-bold d-flex justify-content-center align-items-center">
                                <span class="fa fa-cube mr-2"></span>
                                {{ transferSuccess ? 'Transfer Completed!' : 'Ready for Transfer' }}
                            </div>
                            <div class="display-4 font-weight-bold mb-4" style="font-size:2.8rem; color:#856404;">
                                {{ getDisplayQty.toLocaleString() }}
                            </div>
                            <div class="d-flex flex-column gap-2 justify-content-center mb-3">
                                <button v-if="!transferSuccess.value" :disabled="!getCanTransfer || isProcessing"
                                    :class="['btn btn-lg flex-fill', (getCanTransfer && !isProcessing) ? 'btn-warning' : 'btn-secondary']"
                                    @click="transferToFGWarehouse">
                                    <span v-if="isProcessing" class="fa fa-spinner fa-spin mr-2"></span>
                                    <span v-else class="fa fa-truck mr-2"></span>
                                    {{ getCanTransfer ? 'Transfer ' + bomQty.toLocaleString() : (isDistributionBusy ?
                                        'Distribution Busy' :
                                        'Insufficient Qty') }}
                                </button>
                                <div v-else class="alert alert-success">
                                    <span class="fa fa-check-circle mr-2"></span>
                                    All transferred to {{ nextWorkOrder }}!
                                </div>
                            </div>
                        </div>

                        <!-- Safety Override -->
                        <div class="border rounded p-3 bg-warning-light">
                            <div class="d-flex">
                                <span class="fa fa-exclamation-triangle text-warning mr-2"></span>
                                <div>
                                    <div class="font-weight-bold text-warning">
                                        {{ __('Safety Override') }}
                                    </div>
                                    <div class="text-muted small">
                                        {{ __('Only you can override ingredient quantities.') }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div> <!-- /middle column -->
                </div> <!-- /d-flex for left+middle -->

                <div v-if="!jobCard" class="d-flex flex-column align-items-center justify-content-center p-5 mt-4">
                    <div v-if="loadingIngredients" class="d-flex flex-column align-items-center justify-content-center p-5 mt-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                        <p class="mt-3 text-muted">{{ __('Fetching latest job card details from server...') }}</p>
                    </div>
                    <div v-else class="text-center text-muted p-5 rounded border empty-queue-state">
                        <i class="fa fa-inbox fa-3x mb-3 text-muted-light"></i>
                        <h4 class="font-weight-bold">{{ __('No Job Card Available') }}</h4>
                        <p class="mb-0 mt-2">{{ __('Please wait for a job card to be available for this mixer.') }}</p>
                    </div>
                </div>
            </div> <!-- /main wrapper -->

            <!-- Right: Downstream Alerts -->
            <!-- <div class="p-4 border-left" style="width:300px; overflow-y: auto;">
                <div class="mb-2 d-flex align-items-center">
                    <div>
                        <div class="d-flex align-items-center">
                            <span class="fa fa-exclamation-circle text-danger mr-2"></span>
                            <div class="text-danger font-weight-bold">
                                {{ __('Alerts') }}
                            </div>
                        </div>

                        <div class="text-muted small">
                            {{ __('Real-time alerts from Presser, Cooler & Polishing stations.') }}
                        </div>
                    </div>
                </div>

                <div v-for="(a, idx) in alerts" :key="idx" class="border rounded p-3 mb-3" :style="a.tone === 'danger'
                    ? 'border-left:4px solid #dc3545;background:#ffecec;'
                    : 'border-left:4px solid #ffc107;background:#fff9e6;'">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="badge badge-light text-danger p-2 border border-danger" v-if="a.tone === 'danger'">
                            {{ __('QUALITY ISSUE') }}
                        </span>
                        <span class="badge badge-light text-warning p-2 border border-warning" v-else>
                            {{ __('MACHINE PROBLEM') }}
                        </span>
                        <div class="text-muted small">{{ a.time }}</div>
                    </div>
                    <div class="font-weight-bold mb-1">{{ a.title }}</div>
                    <div class="text-muted small mb-3">
                        {{ __('Source: {0}', [a.source]) }}
                        <template v-if="a.batch">
                            · {{ batchNo }}
                        </template>
                    </div>
                    <div class="d-flex">
                        <button class="btn btn-danger btn-sm mr-2" @click="haltFromAlert(a)">
                            {{ __('Halt Prod.') }}
                        </button>
                        <button class="btn btn-light btn-sm" @click="ignoreAlert(idx)">
                            {{ __('Ignore') }}
                        </button>
                    </div>
                </div>
            </div> --> <!-- /right column -->

        </div> <!-- /Main Content Wrapper -->
    </div> <!-- /root -->
</template>

<style scoped>
.added-checkbox {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
}

.added-text.added {
    color: #16a34a;
    /* green for Added */
    font-weight: 600;
}

.added-text.not-added {
    color: #6b7280;
    /* grey for Not Added */
}

.btn-disabled-pointer {
    cursor: not-allowed;
}

.queue-sidebar {
    max-height: calc(100vh - 150px);
    background-color: var(--bg-light, #fcfcfc);
    border-color: var(--border-color) !important;
}

[data-theme="dark"] .queue-sidebar {
    background-color: var(--control-bg, #1f2124);
}

.empty-queue-state {
    background-color: var(--fg-color);
    border: 2px dashed #a3a3a3 !important;
}

[data-theme="dark"] .empty-queue-state {
    border-color: #525252 !important;
}

.item-time-badge {
    background-color: var(--control-bg);
    color: var(--text-color);
    border-color: var(--border-color) !important;
}

.slab-card {
    transition: all 0.2s ease;
    border-radius: 8px;
    background-color: var(--fg-color, #ffffff);
}

[data-theme="dark"] .slab-card {
    background-color: var(--card-bg, #242629);
    border: 1px solid var(--border-color) !important;
}

.slab-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
}

[data-theme="dark"] .slab-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
}

.slab-card .card-body {
    border-left: 4px solid var(--border-color, #ddd);
    border-radius: inherit;
}

.slab-card.active-card {
    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.2) !important;
}

.slab-card.active-card .card-body {
    border-left: 4px solid var(--primary, #007bff);
    background-color: rgba(0, 123, 255, 0.05);
}

[data-theme="dark"] .slab-card.active-card .card-body {
    background-color: rgba(0, 123, 255, 0.2);
}
</style>
