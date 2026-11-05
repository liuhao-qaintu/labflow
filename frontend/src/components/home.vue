<template>
  <div style="min-height:80vh;display:flex;flex-direction:column;">
    <el-card shadow = "never">
      <div style="display: flex; justify-content: space-between;align-items: center; gap: 16px;">
        <div>
          <div style="font-size: 22px;font-weight: bold;color: #303133;">
            你好,{{ userInfo.name  || '同学'}}
          </div>
          <div style="margin-top: 8px; color: #909399; font-size: 14px">
           {{ PRODUCT_NAME }} · {{ PRODUCT_SUBTITLE }} · {{ userInfo.role === 'admin' ? '资源管理员' : '使用者' }}
          </div>
        </div>
        <el-button type="primary" @click = "$router.push('/manager/aichat')">打开AI智能助手</el-button>
      </div>
    </el-card>

    <el-row :gutter="16" style = "margin-bottom: 16px;">
          <el-col v-for = "item in statCards" :xs="24" :sm="12" :md="8" :key="item.label">
             <el-card shadow ="hover"  style = 'margin-top: 8px;'>
              <div style="color: #909399; font-size: 16px">
                  {{ item.label }}
              </div>
              <div style="margin-top: 8px; font-size: 28px; font-weight: 700; color: #303133">
                {{ item.value }}
              </div>
             </el-card>
          </el-col>
    </el-row>


    <el-card shadow="never" style = "margin-top: 20px;">
       <template #header >
          <span style="display:block;text-align: center;font-weight: 600;font-size: 20px;">系统能做什么</span>
       </template>
        <el-row :gutter="16">
          <el-col v-for = "item in features" :xs="24" :sm="12" :md="8" :key="item.title">
             <div style = "padding: 8px 4px 8px;margin-left: 8px;">
                <div style="font-size: 16px; font-weight: 600; color:#303133">
                   {{ item.title }}
                </div>
                <div style="margin-top: 8px; color: #606266; font-size: 13px; line-height: 1.7">
                    {{ item.desc }}
                </div>
             </div>
          </el-col>
        </el-row>
    </el-card>

    <el-card style="margin-top: auto;">
      <template #header>
        <span style="font-weight: 600;">快捷入口</span>
      </template>

      <div style="display: flex;flex-wrap: wrap;gap:12px">
        <el-button type="primary" v-for="item in shortcuts" :key = "item.path" @click="$router.push(item.path)">
          {{ item.label }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { useUser } from '@/utils/user';
import { PRODUCT_NAME, PRODUCT_SUBTITLE } from '@/branding'
import { computed, ref,onMounted} from 'vue';
import { getLabPageList } from '@/router/lab';
import { getReservationPageListApi } from '@/router/reservation';

const labTotal =ref('-')
const reservationTotal = ref('-')
const statCards = computed(() =>[
  {label:"开放实验室（约）" , value:labTotal.value},
  {label:"与我相关的预约" , value:reservationTotal.value},
  {label:"AI助手" , value:'已接入'},
])
const features = [
  {
    title:'业务预约',
    desc:'实验室/设备浏览、提交预约、我的预约和预约管理。'
  },
  {
    title:'知识库问答',
    desc:'RAG 检索规则与开放时间等文档，回答有据可依。'
  },
  {
    title:'协作助手',
    desc:'用自然语言查找资源、核对时间，确认预约信息后再提交。'
  }
]
const { userInfo} = useUser()

const shortcuts = computed(()=>{
  const list =[ 
    { label:'AI智能助手',path:'/manager/aichat'},
    { label:'实验室列表',path:'/manager/lablist'},
    { label:'我的预约',path:'/manager/myreservation'},
  ]
  if (userInfo.value?.role =='admin'){
    list.push(
      { label:'预约审核',path:'/manager/auditreservation'},
      { label:'实验室管理',path:'/manager/lab'},
      { label:'设备管理',path:'/manager/equipment'},
      { label:'用户管理',path:'/manager/userlist'},
    )
  }
  return list
})


onMounted(async() =>{
  try {
    const labRes = await getLabPageList({page:1,page_size:10,status:1})
    if (labRes.code === 200) labTotal.value = labRes.data?.total ?? 0
  }catch {
    labTotal.value = ''
  }

  try {
    const res = await getReservationPageListApi({page:1,page_size:10})
    if (res.code === 200) reservationTotal.value = res.data?.total ?? 0
  }catch {
    reservationTotal.value = '-'
  }
})


</script>
