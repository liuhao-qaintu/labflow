<template>
    <el-card style="max-width: 90%;margin:0px auto">
            <template #header>
            <div style = "font-size:16px;font-weight:bold;">
                <span>实验室列表</span>
            </div>
            </template>
             <div style="margin-bottom: 10px;">
                <el-input placeholder ="请输入账号或者名称查询" 
                v-model="params.keywords"
                style="width:240px;margin-right: 8px;"
                clearable
                @keyup.enter="handlesearch"
                @clear = "handlesearch"></el-input>
                <el-button type="primary" :icon="Search" @click="handlesearch">查询</el-button>
            </div>
            <div>
                <el-row :gutter = "16" v-loading ="loading">
                    <el-col v-for="item in tableData" :key="item.id" :span="8" style="margin-bottom:16px ;">
                        <el-card shadow = "hover">
                            <img v-if="item.img" 
                            :src="item.img" 
                            style="display: block; width: 100%; height: 300px; border-radius: 6px;object-fit: cover;
                            alt:">
                            <div v-else style="width: 100%;height: 300px;background-color: #f5f7fa;border-radius: 6px;"></div>
                            <div style="font-size: 13px; margin-top: 8px; color: #666">{{ item.name }}</div>
                            <div style="font-size: 13px; margin-top: 8px; color: #666">位置:{{ item.location }}</div>
                            <div style="font-size: 13px; margin-top: 8px; color: #666">容量:{{ item.capacity }}</div>
                            <div style="font-size: 13px; margin-top: 8px; color: #666">开放:{{item.open_time&&item.close_time?`${item.open_time}-${item.close_time}`:'-'}}</div>
                            <div style="margin-top: 12px;display: flex;gap:8px">
                                <el-button style="flex:1" @click="handleRouterEquipment(item)">查看设备</el-button>
                                <el-button style="flex:1" type="primary" @click="handleReserve(item)">预约</el-button>
                            </div>
                        </el-card>
                        <reservation-dialog v-model:visible="reserveVisible" 
                        :lab-id="currentLab?.id" 
                        :lab-name="currentLab?.name"></reservation-dialog>
                    </el-col>
                </el-row>
                <div style="margin-top: 10px; display: flex; justify-content: flex-end">  
                    <el-pagination
                    v-model:current-page="params.page"
                    v-model:page-size="params.pageSize"
                    :total="total"
                    background
                    layout="total, prev, pager, next"
                    @current-change="load"
                />
                </div>
            </div>
    </el-card>
</template>

<script setup>
import { Plus, Search } from '@element-plus/icons-vue';
import { ref,reactive,onMounted } from 'vue'
import { ElMessage,ElMessageBox } from 'element-plus';
import { getLabPageList } from '@/router/lab';
import router from "@/router"
import reservationDialog from '@/common/reservationDialog.vue';


const params = reactive ({
    page:1,
    pageSize:10,
    keywords:''
})

const reserveVisible = ref(false)
const currentLab = ref(null)

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const load = async () =>{
    loading.value = true
    try{
        const res = await getLabPageList({
            page:params.page,
            page_size:params.pageSize,
            keywords:params.keywords
        }
        )
        if (res.code ==200){
            tableData.value =res.data?.list
            total.value = res.data?.total
        }
    }finally{
        loading.value =false
    }
}

const handlesearch = async () =>{
    params.page = 1
    load()
}

const handleRouterEquipment = async (lab)=>{
    router.push({path:'/manager/labEquipment',query:{lab_id:lab.id}})
}

const handleReserve = async(lab) =>{
    currentLab.value = lab
    reserveVisible.value = true
}
onMounted(()=> {
    load()
})
</script>