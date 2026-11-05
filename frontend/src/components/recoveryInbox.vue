<template>
    <el-dialog v-model="visible" title="找回密码申请" width="min(1000px,96vw)" @closed="detail=null; reply.message=''">
        <div class="inbox-toolbar">
            <span>只显示分配给当前管理员的申请</span>
            <el-select v-model="status" clearable placeholder="全部状态" style="width:150px" @change="page=1; load()">
                <el-option v-for="(label,value) in recoveryStatusLabels" :key="value" :label="label" :value="value" />
            </el-select>
            <el-button :loading="loading || opening !== null" :disabled="handling" @click="detail ? openDetail(detail.id) : load()">刷新申请</el-button>
        </div>
        <div v-if="!detail" v-loading="loading">
            <el-empty v-if="!items.length && !loading" description="当前没有申请" />
            <el-card v-for="item in items" :key="item.id" shadow="never" class="request-card">
                <div class="request-heading"><b>{{ item.username }}</b><el-tag>{{ item.expired?'已到期':recoveryStatusLabels[item.status] }}</el-tag></div>
                <p>{{ item.number }} · {{ recoveryTime(item.submitted_at) }}</p>
                <div class="request-footer"><span>申请人填写姓名：{{ item.name || '未填写' }}</span><el-button type="primary" plain :loading="opening===item.id" @click="openDetail(item.id)">查看与处理</el-button></div>
            </el-card>
            <el-pagination v-if="total" v-model:current-page="page" :page-size="10" :total="total" layout="total,prev,pager,next" style="margin-top:18px;justify-content:flex-end" @current-change="load" />
        </div>
        <section v-else>
            <el-button link type="primary" @click="detail=null">← 返回申请列表</el-button>
            <div class="detail-heading"><h3>{{ detail.number }} · {{ detail.username }}</h3><el-tag>{{ detail.expired?'已到期':recoveryStatusLabels[detail.status] }}</el-tag></div>
            <el-alert title="填写信息只是核验线索，用户名匹配不代表身份已验证。请先核验，再操作重置。" type="warning" :closable="false" show-icon />
            <h4>申请人填写的信息</h4>
            <el-descriptions :column="2" border>
                <el-descriptions-item label="用户名">{{ detail.username }}</el-descriptions-item>
                <el-descriptions-item label="姓名">{{ detail.applicant.name || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="邮箱">{{ detail.applicant.email || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="手机号">{{ detail.applicant.phone || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="申请说明" :span="2"><span class="event-content">{{ detail.applicant.description || '未填写' }}</span></el-descriptions-item>
            </el-descriptions>
            <h4>系统登记资料 · 仅供管理员核对</h4>
            <el-descriptions v-if="detail.account" :column="2" border>
                <el-descriptions-item label="账号">{{ detail.account.username }}</el-descriptions-item>
                <el-descriptions-item label="姓名">{{ detail.account.name }}</el-descriptions-item>
                <el-descriptions-item label="邮箱">{{ detail.account.email || '未绑定' }}</el-descriptions-item>
                <el-descriptions-item label="手机号">{{ detail.account.phone || '未绑定' }}</el-descriptions-item>
            </el-descriptions>
            <el-alert v-else title="无法唯一定位账号，请要求申请人核对用户名；当前不可重置。" type="info" :closable="false" />
            <h4>处理时间线</h4>
            <el-timeline>
                <el-timeline-item v-for="(event,index) in detail.events" :key="index" :timestamp="recoveryTime(event.time)" placement="top">
                    <b>{{ event.actor==='admin'?'管理员回复':'申请人' }}</b><p class="event-content">{{ event.content }}</p>
                </el-timeline-item>
            </el-timeline>
            <el-form v-if="!detail.expired && ['pending','need_more_info'].includes(detail.status)" label-position="top" style="margin-top:20px">
                <el-form-item label="处理方式">
                    <el-radio-group v-model="reply.action">
                        <el-radio-button value="need_more_info">要求补充信息</el-radio-button>
                        <el-radio-button value="reject">不予通过</el-radio-button>
                        <el-radio-button value="reset" :disabled="!detail.account?.can_reset_password">核验并重置</el-radio-button>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="给申请人的回复"><el-input v-model="reply.message" type="textarea" :rows="3" maxlength="1500" show-word-limit placeholder="说明需补充哪些信息或本次处理结果。请勿把系统登记资料、原密码或验证码复制到回复中。" /></el-form-item>
                <el-checkbox v-if="reply.action==='reset'" v-model="reply.identity_verified">我已通过独立材料核验账号归属，确认重置此账号密码</el-checkbox>
                <div style="margin-top:16px"><el-button type="primary" :loading="handling" @click="handleSubmit">{{ reply.action==='reset'?'确认重置并回复':'提交处理意见' }}</el-button></div>
            </el-form>
        </section>
    </el-dialog>
</template>

<style scoped>
.inbox-toolbar,.request-heading,.request-footer,.detail-heading { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.inbox-toolbar { margin-bottom:20px; }
.inbox-toolbar>span { margin-right:auto; color:#74838d; font-size:13px; }
.request-card { margin-bottom:12px; border-radius:8px; }
.request-heading,.request-footer,.detail-heading { justify-content:space-between; }
.request-card p { color:#74838d; font-size:13px; margin:10px 0; }
.request-footer span { color:#526673; font-size:13px; }
h4 { margin:24px 0 14px; }
.event-content { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.8; margin-top:8px; }
</style>

<script setup>
import { ref,reactive,computed,watch } from 'vue'
import { ElMessage,ElMessageBox } from 'element-plus'
import { getRecoveryRequestsApi,getRecoveryDetailApi,handleRecoveryApi } from '@/router/user'
import { recoveryStatusLabels,recoveryTime } from '@/utils/recovery'

const props = defineProps({modelValue:Boolean})
const emit = defineEmits(['update:modelValue','updated'])
const visible = computed({get:() => props.modelValue,set:value => emit('update:modelValue',value)})
const loading = ref(false),handling = ref(false),opening = ref(null)
const items = ref([]),total = ref(0),page = ref(1),status = ref('')
const detail = ref(null)
const reply = reactive({action:'need_more_info',message:'',identity_verified:false})
const load = async() => {
    loading.value = true
    try {
        const res = await getRecoveryRequestsApi({page:page.value,page_size:10,status:status.value || undefined})
        if (res.code ===200) { items.value = res.data.list; total.value = res.data.total }
    } catch {
        // 请求层统一提示。
    } finally { loading.value = false }
}
const openDetail = async(id) => {
    if (opening.value !== null) return
    opening.value = id
    try {
        const res = await getRecoveryDetailApi(id)
        if (res.code ===200) {
            detail.value = res.data
            Object.assign(reply,{action:'need_more_info',message:'',identity_verified:false})
        }
    } catch {
        // 请求层统一提示。
    } finally { opening.value = null }
}
const handleSubmit = async() => {
    if (handling.value) return
    if (!reply.message.trim()) return ElMessage.warning('请填写给申请人的回复')
    if (reply.action==='reset') {
        if (!reply.identity_verified) return ElMessage.warning('请先核验并确认账号归属')
        try {
            await ElMessageBox.confirm(`确认重置账号“${detail.value.account.username}”？旧密码和登录状态会失效。申请人将能凭申请凭据查看初始密码，首次登录必须改密。`, '确认已完成身份核验', {type:'warning',confirmButtonText:'确认重置',cancelButtonText:'取消'})
        } catch { return }
    }
    handling.value = true
    try {
        const res = await handleRecoveryApi(detail.value.id,{...reply,target_user_id:reply.action==='reset'?detail.value.account.id:null})
        if (res.code ===200) {
            detail.value = res.data
            Object.assign(reply,{action:'need_more_info',message:'',identity_verified:false})
            ElMessage.success(res.message)
            emit('updated')
            await load()
        }
    } catch {
        // 不记录申请内容或重置请求。
    } finally { handling.value = false }
}
watch(() => props.modelValue,value => {
    if (value) { detail.value = null; page.value = 1; load() }
})
</script>
