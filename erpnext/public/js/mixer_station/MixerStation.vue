<script setup>
import { ref, computed, onMounted } from 'vue';

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
const selectedMixer = ref('');
const mixersList = ref([]);

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

// actions
onMounted(async () => {
    const route = frappe.get_route();
    jobCard.value = route[2] || null;

    if (!jobCard.value) {
        error.value = __('No Job Card found in route');
		loadingIngredients.value = true;
		jobCard.value = await getJobCardsList();
	}

    await loadMixers();
    const stateRes = await frappe.call({
        method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_mixer_state',
        args: { job_card: jobCard.value },
	});

	
    const s = stateRes.message || {};
    mixingReady.value = !!s.mixer_materials_confirmed;
    mixingStarted.value = !!s.mixer_started;
    mixingStartTime.value = s.mixer_start_time;

    jobCardSubmitted.value = !!s.job_card_submitted || false;  
    if (jobCardSubmitted.value) {
        preparedQty.value = s.prepared_qty || 0;
        stockEntryName.value = s.stock_entry_name || '';
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
    } 
    else {
        mixingElapsed.value = 0;
        if (mixingTimerHandle.value) {
            clearInterval(mixingTimerHandle.value);
            mixingTimerHandle.value = null;
        }
    }

    try {
        loadingIngredients.value = true;
        error.value = null;

        if (jobCard.value) {
            const jc = await frappe.db.get_doc('Job Card', jobCard.value);
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
            transferredQty.value = 0;
            transferSuccess.value = false;
            await loadBomQty();
        }
    } 
    catch (e) {
        error.value = e.message || e;
        frappe.msgprint(__('Failed to load BOM ingredients: {0}', [error.value]));
    } 
    finally {
        loadingIngredients.value = false;
    }
});

async function toggleReady() {
    if (mixingStarted.value) {
        return;
    } 
    if (!allAdditionalIngredientsAdded.value) {
        frappe.msgprint(__('Mark all additional ingredients as Added first.'));
        return;
    }
    frappe.confirm(
        __('Do you want to confirm the materials?'),
        async () => {
            try {
                const payload = ingredients.value.map(ing => ({
                    item_code: ing.item_code,
                    qty: ing.qty,
                    unit: ing.unit,
                    is_added: ing.is_added,
                }));

                const r = await frappe.call({
                    method: 'erpnext.manufacturing.page.mixer_station.mixer_station.confirm_materials',
                    args: {
                        job_card: jobCard.value,
                        ingredients: JSON.stringify(payload),
                    }
                });

                mixingReady.value = true;
                frappe.msgprint(
                    __('Materials confirmed. Stock Entry {0} created.', [r.message.stock_entry])
                );
            } catch (e) {
                frappe.msgprint(
                    __('Failed to confirm materials: {0}', [e.message || e])
                );
            }
        },
        () => {
            frappe.msgprint(__('Materials are not confirmed.'));
        }
    );
}

async function getJobCardsList() {
  const route = frappe.get_route();
  const station = route[1] || "";
  const result = await frappe.call({
    method: 'erpnext.manufacturing.doctype.operation.api.get_job_cards_list',
    args: {
      operation: station
    }
  });

	jobCard.value = result.message.name;
	return jobCard.value;
}

async function startMixing() {
    if (!mixingReady.value) {
        frappe.msgprint(__('Confirm materials before starting mixing.'));
        return;
    }
    frappe.confirm(
        __('Start mixing now?'),
        async () => {
            try {
                await frappe.call({
                    method: 'erpnext.manufacturing.page.mixer_station.mixer_station.start_mixing',
                    args: { job_card: jobCard.value }
                });
                mixingStarted.value = true;
                mixingStartTime.value = frappe.datetime.now_datetime();

                mixingElapsed.value = 0;
                if (mixingTimerHandle.value) {
                    clearInterval(mixingTimerHandle.value);
                }
                mixingTimerHandle.value = setInterval(() => {
                    mixingElapsed.value += 1;
                }, 1000);
    
                frappe.msgprint(__('Mixing started'));
            }
            catch (e) {
                frappe.msgprint(__('Failed to start Job Card: {0}', [e.message || e]));
            }
        },
        () => {
            frappe.msgprint(__('Mixing was not started.'));
        }
    );
}

async function finishAndDischarge() {
    if (mixingTimerHandle.value) {
        clearInterval(mixingTimerHandle.value);
        mixingTimerHandle.value = null;
    }
    try {
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
        transferredQty.value = 0;
        transferSuccess.value = false;

        frappe.msgprint(result.message.message);    
        if (result.message.work_order_status === 'Completed') {
            frappe.show_alert({
                message: __('Work Order also Completed!'),
                indicator: 'green'
            });
        }
    }
    catch (error) {
        console.error('error.message:', error.message);
        const errorMsg = error.message || 
                        (error._server_messages?.[0]?.message) || 
                        JSON.stringify(error);
        
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: `Failed to complete Job Card:<br><pre>${errorMsg}</pre>`
        });
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
                    frappe.msgprint(__('Failed: {0}', [e.message]));
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
    if (!getCanTransfer()) { 
        frappe.msgprint(__('Insufficient qty ({0}) for BOM requirement ({1})', 
            [getDisplayQty().toLocaleString(), bomQty.value.toLocaleString()]));
        return;
    }
    
    try {
        const jc = await frappe.db.get_doc('Job Card', jobCard.value);
        const workOrder = jc.work_order; 
        const qty = bomQty.value
        
        if (!workOrder) {
            frappe.msgprint(__('Work Order required from Job Card'));
            return;
        }

        const result = await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.transfer_to_next_process',
            args: {
                mixing_work_order: workOrder,  
                qty: bomQty.value
            },
            freeze: true,
            freeze_message: __('Transferring to Distribution')
        });
        
        transferredQty.value += result.message.qty_transferred;   
        if (getDisplayQty() <= 0) {
            transferSuccess.value = true;
        }

        frappe.msgprint({
            title: __('Transfer Complete'),
            message: result.message.message,
            indicator: 'green'
        });
        
        frappe.show_alert({
            message: `Next: ${result.message.next_work_order}`,
            indicator: 'blue'
        });
        
    } catch (error) {
        frappe.msgprint(__('Transfer failed: {0}', [error.message]));
    }
}

function getDisplayQty() {
    return parseFloat((preparedQty.value - transferredQty.value).toFixed(3));
}

function getCanTransfer() {
    const display = getDisplayQty();
    const bom = parseFloat(bomQty.value.toFixed(2));
    return display >= bom && !transferSuccess.value;
}

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

async function loadMixers() {
    const response = await frappe.call({
        method: 'erpnext.manufacturing.page.mixer_station.mixer_station.get_all_mixers',
        args: {
            job_card: jobCard.value,
        }
    });
    mixersList.value = response.message || [];
}

async function onMixerChange() {
    if (selectedMixer.value) {
        await frappe.call({
            method: 'erpnext.manufacturing.page.mixer_station.mixer_station.assign_mixer_to_job_card',
            args: {
                job_card: jobCard.value,
                mixer: selectedMixer.value
            }
        })
    }
}
</script>

<template>
    <div class="page-card p-0 d-flex">

        <!-- Left + middle columns wrapper -->
        <div class="w-100">
            <!-- Top header -->
            <div class="d-flex align-items-center mb-4">
                <div>
                    <div class="mb-1">
                        <a href="javascript:history.back()" class="small text-muted">
                            &larr; {{ __('Back to Queue') }}
                        </a>
                    </div>
                    <h2 class="mb-3">{{ batchNo }}</h2>
                    <div class="text-danger font-weight-bold">{{ jobCard }}</div>
                </div>

                <div class="ml-4">
                    <span class="badge badge-pill badge-light border px-3 py-2" style="font-size:1rem">
                        {{ phase }}
                    </span>
                </div>
            </div> <!-- /header -->

            <div class="d-flex">
                <!-- Left: Raw Material Inputs -->
                <div class="flex-fill mr-4" style="font-size: medium;">
                    <div class="mb-3">
                        <h3 class="mb-1">{{ __('Raw Material Inputs') }}</h3>
                        <div class="text-muted small">
                            {{ __('Review and adjust calculated quantities before mixing.') }}
                        </div>
                    </div>

                    <div class="mb-3 d-flex justify-content-between">
                        <label class="form-label bold">{{ __('Select Mixer') }}</label>
                        <select v-model="selectedMixer" style="width: 30%;" class="form-control" :disabled="mixingReady || mixingStarted" @change="onMixerChange">
                            <option value="" disabled selected>
                                {{ __('Select Mixer Type...') }}
                            </option>
                            <option v-for="mixer in mixersList" :key="mixer.name" :value="mixer.name">
                                {{ mixer.name}}
                            </option>
                        </select>
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
                                            <span
                                            class="added-text"
                                            :class="ing.is_added ? 'added' : 'not-added'"
                                            >
                                            {{ ing.is_added ? 'Added' : 'Not Added' }}
                                            </span>
                                        </label>
                                        <div v-if="ing.is_added" class="d-flex align-items-center">
                                            <input
                                            type="number"
                                            class="form-control text-right"
                                            :readonly="inputsReadonly"
                                            :class="inputsReadonly ? 'bg-light' : ''"
                                            style="width:120px;"
                                            v-model.number="ing.qty"
                                            />
                                            <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                        </div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div class="d-flex align-items-center">
                                        <input type="number"
                                            class="form-control text-right"
                                            :readonly="inputsReadonly"
                                            :class="inputsReadonly ? 'bg-light' : ''"
                                            style="width:120px;"
                                            v-model.number="ing.qty" />
                                        <span class="ml-2 text-muted">{{ ing.unit }}</span>
                                    </div>
                                </template>
                            </div>
                        </div>

                    </div>
                </div> <!-- /left column -->

                <!-- Middle: Mixing card -->
                <div style="width:315px;" class="mr-4 p-4">
                    <!-- Ready to Mix state -->
                    <div v-if="!mixingStarted && !jobCardSubmitted" class="border rounded p-4 mb-3 text-center">
                        <div class="mb-2 text-success font-weight-bold">
                            {{ __('Ready to Mix?') }}
                        </div>
                        <div class="text-muted small mb-3">
                            {{ __('Confirm all materials are loaded and weighed correctly.') }}
                        </div>

                        <div class="mb-3">
                            <button v-if="!mixingReady" :disabled="!isMixerSelected || !allAdditionalIngredientsAdded" :class="!isMixerSelected || !allAdditionalIngredientsAdded ? 'btn-disabled-pointer' : ''" class="btn btn-sm border border-success" @click="toggleReady">
                                <span class="fa fa-check mr-1"></span>
                                {{ __('Confirm Materials') }}
                            </button>

                            <button v-else class="btn btn-success btn-block py-2" :disabled="mixingStarted" @click="startMixing">
                                <span class="fa fa-play mr-1"></span>
                                {{ __('Start Mixing') }}
                            </button>
                        </div>
                    </div>

                    <!-- Mixing in Progress state -->
                    <div v-else-if="mixingStarted && !jobCardSubmitted" class="border rounded p-4 mb-3 text-center" style="background:#e8f8ec;">
                        <div
                            class="mb-2 text-success font-weight-bold d-flex justify-content-center align-items-center">
                            <span class="fa fa-spinner fa-spin mr-2"></span>
                            {{ __('Mixing in Progress') }}
                        </div>
                        <div class="display-4 font-weight-bold mb-3" style="font-size:2.5rem;">
                            {{ formattedMixingTime }}
                        </div>
                        <div class="d-flex flex-column gap-2 justify-content-center mb-3">
                            <button class="btn btn-success flex-fill" @click="finishAndDischarge">
                                <span class="fa fa-check mr-1"></span>
                                {{ __('Finish & Discharge') }}
                            </button>
                            <button class="btn btn-outline-primary flex-fill mt-2 border border-dark" @click="openAddMaterials">
                                <span class="fa fa-plus mr-1"></span>
                                {{ __('Add Materials') }}
                            </button>
                        </div>
                        
                        <div class="text-muted small mt-2">
                            {{ __('Started at {0}', [startedAtLabel]) }}
                        </div>
                    </div>

                    <div v-else-if="jobCardSubmitted" class="border rounded p-4 mb-3 text-center" style="background:#fff3cd;">
                        <div class="mb-3 text-warning font-weight-bold d-flex justify-content-center align-items-center">
                            <span class="fa fa-cube mr-2"></span>
                            {{ transferSuccess ? 'Transfer Completed!' : 'Ready for Transfer' }}
                        </div>
                        <div class="display-4 font-weight-bold mb-4" style="font-size:2.8rem; color:#856404;">
                            {{ getDisplayQty().toLocaleString() }}
                        </div>
                        <div class="d-flex flex-column gap-2 justify-content-center mb-3">
                            <button 
                                v-if="!transferSuccess.value" 
                                :disabled="!getCanTransfer()"
                                :class="['btn btn-lg flex-fill', getCanTransfer() ? 'btn-warning' : 'btn-secondary']"
                                @click="transferToFGWarehouse">
                                <span class="fa fa-truck mr-2"></span>
                                {{ getCanTransfer() ? 'Transfer ' + bomQty.toLocaleString() : 'Insufficient Qty' }}
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
                                    {{ __('Only you can override ingredient quantities. All changes are logged for quality assurance.') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div> <!-- /middle column -->
            </div> <!-- /d-flex for left+middle -->
        </div> <!-- /w-100 wrapper -->

        <!-- Right: Downstream Alerts -->
        <div style="width:400px;">
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
        </div> <!-- /right column -->

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
  color: #16a34a;      /* green for Added */
  font-weight: 600;
}

.added-text.not-added {
  color: #6b7280;      /* grey for Not Added */
}

.btn-disabled-pointer {
    cursor: not-allowed;
}
</style>