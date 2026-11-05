<template>
    <div>
        <el-card>
            <template #header>
                <div style="font-size: 16px;font-weight: bold;">
                    <span>{{ PRODUCT_NAME }} · 资源协作助手</span>
                </div>
            </template>


            <div ref = "listRef"
                style="
                height:480px;
                overflow-y:auto;
                padding:8px 4px;
                background-color:#fafafa;
                border-radius:12px">
                <div v-for="(item,index) in messages"
                :key = "index"
                :style="{
                    display:'flex',
                    justifyContent:item.role ==='user'?'flex-end' : 'flex-start',
                    marginBottom:'12px'
                }"
                >
                    <div class="ai-markdown"
                    :style="{
                    maxWidth:'70%',
                    minWidth:0,
                    padding:'10px 12px',
                    borderRadius:'12px',
                    backgroundColor:item.role ==='user' ? '#409eff' :'#fff',
                    color: item.role ==='user' ? '#fff' : '#333',
                    lineHeight:'1.6',
                    wordBreak:'break-word',
                    boxShadow:'0 1px 2px rgba(0,0,0,0.06)'
                    }" >
                        <div
                            v-if="item.role === 'assistant' && item.status"
                            style="margin-bottom: 6px; font-size: 12px; color: #909399"
                        >
                            {{ item.status }}
                        </div>
                        
                        <div v-html="parseMarkdown(item.content)"></div>
                        </div>               
                </div>
            </div>
            <div v-if="pendingAction" class="confirm-card">
                <div class="confirm-title">需要你确认</div>
                <div class="confirm-question">
                    {{ pendingAction.payload.question || '是否确认执行这次操作？' }}
                </div>
                <div v-for="(value, key) in (pendingAction.payload.args || {})"
                     :key="key" class="confirm-row">
                    <span class="confirm-key">{{ argLabels[key] || key }}</span>
                    <span>{{ value }}</span>
                </div>
                <div style="display:flex;gap:8px;margin-top:12px">
                    <el-button type="primary" :loading="deciding" @click="decide(true)">确认提交</el-button>
                    <el-button :disabled="deciding" @click="decide(false)">取消</el-button>
                </div>
            </div>
            <div style ="margin-top: 12px;display: flex;gap: 8px;align-items: flex-end;">
                <el-input
                v-model="input"
                type="textarea"
                :rows="2"
                placeholder="问问实验室怎么预约,开放时间..."
                @keydown.enter.exact.prevent="handleSend"
                ></el-input>
                <el-button type="primary" @click="handleSend" :loading ="loading" :disabled="!!pendingAction">发送</el-button>
            </div>
        </el-card>
    </div>
</template>
<script setup>
import { ref,reactive,nextTick } from 'vue'
import { PRODUCT_NAME } from '@/branding'
import { chatStreamApi, resumeChatApi } from '@/router/ai';
import { marked } from 'marked';
import DOMPurify from 'dompurify' // 过滤危险的 HTML，防止 XSS 攻击
import { ElMessage } from 'element-plus';

const loading = ref(false)
const listRef = ref()
const messages = ref([
    {
        role:'assistant',
        content:`你好，我是 ${PRODUCT_NAME}。可以帮你查找实验室、设备和使用规则。需要预约时，我会先列出信息，等你确认后再提交。`
    }
])
const input = ref()
const threadId = ref('')
// 图停在 confirm 节点时待确认的操作：{threadId, payload:{tool, args, question}}
const pendingAction = ref(null)
const deciding = ref(false)
const argLabels = {
    lab_id: '实验室 ID',
    equipment_id: '设备 ID',
    date: '日期',
    start_time: '开始时间',
    end_time: '结束时间'
}
const scrollToBottom = () =>{
    nextTick(() =>{
        const elem = listRef.value
        if (elem) elem.scrollTop = elem.scrollHeight
    })
}

const handleSend = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  if (pendingAction.value) {
    ElMessage.warning('请先确认或取消当前预约')
    return
  }

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  // 必须用 reactive：普通对象 push 后再改字段，视图可能不更新
  const assistant = reactive({
    role: 'assistant',
    content: '', // 正文：靠 token 一点点拼
    status: '正在思考…', // 当前状态文案
    steps: [] // 过程流水，不进下次 history
  })
  messages.value.push(assistant)

  const history = messages.value
    .filter((item) => item.role === 'user' || item.role === 'assistant')
    .slice(0, -1) // 去掉刚插入的空助手，避免把空 content 送回去
    // 只保留 role/content；status、steps 丢掉
    .map(({ role, content }) => ({ role, content }))

  try {
    // 第二个参数是回调：每解析出一条 SSE 事件就进一次
    await chatStreamApi({ messages: history }, (evt) => {
      if (evt.type === 'thread') {
        threadId.value = evt.thread_id || threadId.value
      } else if (evt.type === 'status') {
        assistant.status = evt.message || '正在思考…'
      } else if (evt.type === 'tool_start') {
        const label = evt.label || evt.name || '工具'
        assistant.status = `正在${label}…`
        assistant.steps.push(`开始：${label}`)
      } else if (evt.type === 'tool_end') {
        const label = evt.label || evt.name || '工具'
        assistant.status = `${label}完成`
        assistant.steps.push(`完成：${label}`)
      } else if (evt.type === 'token') {
        assistant.content += evt.content || '' // 打字机：追加，不是覆盖
        assistant.status = '' // 开始出字后清掉「正在…」，避免叠在一起
      } else if (evt.type === 'interrupt') {
        // 图已暂停，写操作还没执行；等用户点按钮再发 resume
        assistant.status = ''
        if (!assistant.content) assistant.content = '已准备好预约信息，请先确认。'
        assistant.steps.push('等待人工确认')
        pendingAction.value = {
          threadId: evt.thread_id || threadId.value,
          payload: evt.payload || {}
        }
      } else if (evt.type === 'done') {
        assistant.status = ''
        // 注意：不要在这里再 append 一整段正文，否则会双份
      } else if (evt.type === 'error') {
        assistant.status = ''
        if (!assistant.content) {
          assistant.content = evt.message || '请求失败'
        }
        ElMessage.error(evt.message || '请求失败')
      }
      scrollToBottom()
    })
  } catch (err) {
    assistant.status = ''
    if (!assistant.content) {
      assistant.content = err.message || '网络异常'
    }
    ElMessage.error(err.message || '网络异常')
  } finally {
    loading.value = false
    assistant.status = ''
    scrollToBottom()
  }
}

// 确认/取消：向被挂起的图发 resume，批准后才真正写库
const decide = async (approved) => {
  if (!pendingAction.value || deciding.value) return
  const action = pendingAction.value
  deciding.value = true
  try {
    const res = await resumeChatApi({ thread_id: action.threadId, approved })
    // 业务错误（code != 200）由 request 拦截器提示，保留卡片便于重试
    if (res?.code !== 200) return
    messages.value.push({
      role: 'assistant',
      content: res?.data?.content || (approved ? '已提交，等待管理员审核。' : '已取消本次预约。')
    })
    pendingAction.value = null
  } catch (err) {
    // 请求层已提示错误；保留卡片，允许重试
  } finally {
    deciding.value = false
    scrollToBottom()
  }
}

const parseMarkdown =(text) =>{
    if (!text) return ''
    //使用 marked 解析，然后用 DOMPurify 清理
    const rawHtml = marked.parse(text, { breaks: true })
    return DOMPurify.sanitize(rawHtml)
}

</script>

<style scoped>
.ai-markdown :deep(p) {
    margin: 0 0 8px;
}
.ai-markdown :deep(ul),
.ai-markdown :deep(ol) {
    margin: 6px 0;
    padding-left: 1.4em;
    list-style: revert;
}

.confirm-card {
    margin-top: 12px;
    padding: 12px;
    border: 1px solid #e4e7ed;
    border-left: 4px solid #e6a23c;
    border-radius: 8px;
    background: #fdf6ec;
}
.confirm-title {
    font-weight: 600;
    margin-bottom: 6px;
}
.confirm-question {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}
.confirm-row {
    display: flex;
    gap: 12px;
    font-size: 13px;
    line-height: 1.9;
}
.confirm-key {
    color: #909399;
    min-width: 72px;
}
</style>
