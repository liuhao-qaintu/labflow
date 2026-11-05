<template>
    <div class="auth-page">
        <el-card class="recovery-card">
            <div class="auth-brand">{{ PRODUCT_NAME }}</div>
            <h1>找回密码</h1>
            <p class="intro">提交申请，由管理员核验身份；通过申请凭据查看回复、补充材料。</p>
            <el-tabs v-model="activeTab">
                <el-tab-pane label="提交申请" name="submit">
                    <el-alert title="用户名必填，其余信息可帮助管理员核验。请勿填写原密码或验证码。" type="info" :closable="false" show-icon />
                    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" style="margin-top:20px">
                        <el-form-item label="用户名" prop="username"><el-input v-model="form.username" maxlength="50" placeholder="请输入要找回的账号" /></el-form-item>
                        <div class="form-grid">
                            <el-form-item label="姓名（选填）"><el-input v-model="form.name" maxlength="50" /></el-form-item>
                            <el-form-item label="手机号（选填）" prop="phone"><el-input v-model="form.phone" maxlength="30" /></el-form-item>
                        </div>
                        <el-form-item label="邮箱（选填）" prop="email"><el-input v-model="form.email" maxlength="100" placeholder="如有已绑定邮箱，可用于辅助核对；系统不会发送邮件" /></el-form-item>
                        <el-form-item label="申请原因与证明说明（选填）"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="1500" show-word-limit placeholder="例如：所属实验室、账号使用情况或其他可供核验的信息" /></el-form-item>
                        <p class="hint">通常约1～3天处理，材料不足时需要补充。仅知道用户名不能证明账号归属。</p>
                        <el-button type="primary" :loading="submitting" :disabled="!!receipt" @click="submit">提交给管理员</el-button>
                        <el-button v-if="receipt" @click="activeTab='track'">查看本次申请</el-button>
                    </el-form>
                </el-tab-pane>
                <el-tab-pane label="凭据查询与跟进" name="track">
                    <p class="hint">申请凭据有效期为30天，只能跟进对应申请。编号或用户名不能代替凭据；丢失后需重新申请。</p>
                    <el-alert v-if="receipt" title="申请已提交：请立即保存下方凭据，本页不会自动保存，关闭后不能取回。" type="success" :closable="false" show-icon />
                    <div v-if="receipt" class="receipt-box">
                        <b>申请编号：{{ receipt.number }}</b>
                        <p>凭据有效至 {{ recoveryTime(receipt.expires_at) }}（30天）。请勿交给他人；丢失后需重新申请。</p>
                        <el-input :model-value="receipt.credential" type="password" show-password readonly autocomplete="off" />
                        <el-button style="margin-top:10px" @click="copyCredential">复制申请凭据</el-button>
                    </div>
                    <el-form label-position="top" @submit.prevent="lookup">
                        <el-form-item label="申请凭据"><el-input v-model="credential" type="password" show-password autocomplete="off" :disabled="supplementing" placeholder="粘贴保存的43位申请凭据；申请编号不能代替凭据" @input="detail=null; supplement=''" @keyup.enter="lookup" /></el-form-item>
                        <el-button type="primary" :loading="querying" @click="lookup">查询进度</el-button>
                        <el-button @click="clearTracking">清除当前凭据</el-button>
                    </el-form>
                    <section v-if="detail" class="tracking-detail">
                        <div class="detail-heading"><b>{{ detail.number }} · {{ detail.username }}</b><el-tag>{{ recoveryStatusLabels[detail.status] }}</el-tag></div>
                        <p class="hint">凭据有效至 {{ recoveryTime(detail.expires_at) }}</p>
                        <el-steps :active="recoveryStep(detail.status)" finish-status="success" simple style="margin:20px 0">
                            <el-step title="已提交" /><el-step title="核验与补充" /><el-step :title="detail.status==='rejected'?'未通过':'处理结果'" />
                        </el-steps>
                        <el-timeline>
                            <el-timeline-item v-for="(event,index) in detail.events" :key="index" :timestamp="recoveryTime(event.time)" placement="top">
                                <b>{{ event.actor==='admin'?'管理员回复':'申请记录' }}</b><p class="event-content">{{ event.content }}</p>
                            </el-timeline-item>
                        </el-timeline>
                        <el-alert v-if="detail.status==='resolved'" title="申请已核验并重置，请登录后立即修改初始密码" type="success" :closable="false" />
                        <div v-if="detail.initial_password" class="receipt-box">
                            <p>本次初始密码仅在尚未改密、且此次重置仍有效时显示。请登录后立即修改。</p>
                            <el-input :model-value="detail.initial_password" readonly type="password" show-password autocomplete="off" />
                            <el-button style="margin-top:10px" type="primary" @click="goLogin">前往登录并改密</el-button>
                        </div>
                        <p v-else-if="detail.status==='resolved'" class="hint">初始密码已不再交付，可能已完成改密或发生了后续重置。请使用你设置的新密码登录，仍有问题可重新申请。</p>
                        <el-form v-if="['pending','need_more_info'].includes(detail.status)" label-position="top" style="margin-top:20px">
                            <el-form-item label="补充材料"><el-input v-model="supplement" type="textarea" :rows="3" maxlength="1500" show-word-limit placeholder="按管理员要求补充说明，请勿填写密码或验证码" /></el-form-item>
                            <el-button type="primary" :loading="supplementing" @click="sendSupplement">提交补充</el-button>
                        </el-form>
                    </section>
                </el-tab-pane>
            </el-tabs>
            <el-button link type="primary" style="margin-top:22px" @click="goLogin">返回登录</el-button>
        </el-card>
    </div>
</template>

<style scoped>
.auth-page { min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px; background:linear-gradient(145deg,#eef6f5,#f6f8fc); }
.recovery-card { width:680px; max-width:100%; border-radius:18px; padding:14px; }
.auth-brand { color:#176d78; font-size:28px; font-weight:750; }
h1 { margin:8px 0; font-size:23px; color:#203b4c; }
.intro,.hint { color:#74838d; font-size:13px; line-height:1.8; margin-bottom:20px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.receipt-box { margin:18px 0; padding:16px; border:1px solid #dce7ec; border-radius:8px; background:#f5f9fa; font-size:13px; line-height:1.8; }
.receipt-box p { margin:8px 0; }
.tracking-detail { margin-top:28px; padding-top:20px; border-top:1px solid #e0e8ed; }
.detail-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.event-content { margin-top:8px; line-height:1.8; white-space:pre-wrap; overflow-wrap:anywhere; }
@media(max-width:600px) { .form-grid { grid-template-columns:1fr; gap:0; } .auth-page { padding:12px; } .recovery-card { padding:0; } }
</style>

<script setup>
import { ref,reactive,onMounted,onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { PRODUCT_NAME } from '@/branding'
import { submitRecoveryApi,lookupRecoveryApi,supplementRecoveryApi } from '@/router/auth'
import { recoveryStatusLabels,recoveryStep,recoveryTime,credentialError } from '@/utils/recovery'

const activeTab = ref('submit')
const formRef = ref()
const form = reactive({username:'',name:'',email:'',phone:'',description:''})
const rules = {
    username:[{required:true,message:'请输入用户名',trigger:'blur'},{pattern:/\S/,message:'用户名不能为空白',trigger:'blur'}],
    email:[{type:'email',message:'邮箱格式不正确',trigger:'blur'}],
    phone:[{pattern:/^[+0-9 ()-]{5,30}$/,message:'手机号格式不正确',trigger:'blur'}]
}
const submitting = ref(false),querying = ref(false),supplementing = ref(false)
const receipt = ref(null),detail = ref(null)
const credential = ref(''),supplement = ref('')
const submit = async() => {
    if (submitting.value || receipt.value) return
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    submitting.value = true
    try {
        const res = await submitRecoveryApi(form)
        if (res.code !==200) return
        receipt.value = res.data
        credential.value = res.data.credential
        activeTab.value = 'track'
        ElMessage.success(res.message)
        await lookup()
    } catch {
        // 请求层统一提示，不打印含申请信息或凭据的请求。
    } finally { submitting.value = false }
}
const lookup = async() => {
    if (querying.value) return
    const error = credentialError(credential.value)
    if (error) return ElMessage.warning(error)
    querying.value = true
    detail.value = null
    const requestedCredential = credential.value.trim()
    try {
        const res = await lookupRecoveryApi({credential:requestedCredential})
        if (res.code ===200 && credential.value.trim() === requestedCredential) detail.value = res.data
    } catch {
        // 无效、到期及网络错误由请求层提示。
    } finally { querying.value = false }
}
const sendSupplement = async() => {
    if (supplementing.value) return
    if (!supplement.value.trim()) return ElMessage.warning('请填写补充说明')
    supplementing.value = true
    const requestedCredential = credential.value.trim()
    try {
        const res = await supplementRecoveryApi({credential:requestedCredential,content:supplement.value.trim()})
        if (res.code ===200 && credential.value.trim() === requestedCredential) { detail.value = res.data; supplement.value = ''; ElMessage.success(res.message) }
    } catch {
        // 请求层统一提示。
    } finally { supplementing.value = false }
}
const copyCredential = async() => {
    try { await navigator.clipboard.writeText(receipt.value.credential); ElMessage.success('已复制，请妥善保存') }
    catch { ElMessage.warning('复制失败，请点击密码框显示后手动保存') }
}
const clearTracking = () => { credential.value = ''; detail.value = null; receipt.value = null; supplement.value = '' }
const goLogin = () => { clearTracking(); router.push('/login') }
onBeforeUnmount(clearTracking)
onMounted(() => {
    if (router.currentRoute.value.hash) router.replace({path:'/forgot-password',hash:''})
})
</script>
