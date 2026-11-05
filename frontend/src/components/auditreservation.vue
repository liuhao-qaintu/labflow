<template>
    <div>
        <el-card>
            <template #header>
                <div style="font-size: 16px;font-weight: bold;">
                    <span>当前预约请求</span>
                </div>
            </template>
            <div style="margin-bottom: 10px;">
                <el-select v-model="params.status"
                 placeholder="请选择状态" 
                 style="width: 240px;margin-right:8px;"
                 clearable
                 @change="handleSearch"
                 @clear = "handleSearch">
                    <el-option :value ="0" label ="待审核" />
                    <el-option :value ="1" label ="已通过" />
                    <el-option :value ="2" label ="已拒绝" />
                    <el-option :value ="3" label ="已取消" />
                </el-select>
                <el-button @click="handleSearch">查询</el-button>
            </div>
            <div>
                <el-table :data="tableData" width="100%"
                :header-cell-style = "{backgroundColor:'#f5f7fa',color:'#333'}"
                v-loading = "loading">
                    <el-table-column label="实验室" prop="lab_name" />
                    <el-table-column label="预约类型" >
                        <template #default="{ row }">
                            <el-tag :type="row.type ==='实验室'?'success':'primary'">{{ row.type }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="设备"  >
                        <template #default="{ row }">
                            {{row.equipment_name || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="日期" prop="date" />
                    <el-table-column label="预约时段" width="140">
                         <template #default="{ row }">
                            {{ row.start_time }} - {{ row.end_time }}
                        </template>
                    </el-table-column>
                    <el-table-column label="备注" prop="remark" width="300px"/>
                    <el-table-column label="预约状态" prop="status" width = "100">
                        <template #default="{ row }">
                            <el-tag :type = "statusType(row.status)">
                                {{ statusText(row.status) }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width ="180" header-align="center" align="center">
                        <template #default="{ row }">
                            <el-button type="success" text bg @click="handleAudit(row,1)">通过</el-button>
                            <el-button type="primary" text bg @click="handleAudit(row,2)">拒绝</el-button>
                        </template>
                    </el-table-column>
                </el-table>
                <div style="margin-top: 10px; 
                display: flex; 
                justify-content: flex-end">         
               <el-config-provider :locale="zhCn">
                <el-pagination
                    v-model:current-page="params.page"
                    v-model:page-size="params.pageSize"
                    :total="total"
                    background
                    layout="total, prev, pager, next"
                    @current-change="load"
                />
                </el-config-provider>
                </div>
            </div>
        </el-card>
    </div>
</template>

<script setup>
import { ref,reactive,onMounted }  from 'vue'
import { getReservationPageListApi,auditReservationApi } from '@/router/reservation';
import { ElMessage,ElMessageBox } from 'element-plus';

const loading =ref(false)
const tableData =ref([])
const total = ref(0)
const params = reactive({
    page:1,
    page_size:10,
    status:null
})

const statusType = (status)=>{
    const dict = {0:'warning',1:'success',2:'danger',3:'info'}
    if (status in dict){
        return dict[status]
    }else{
        return '-'
    }
}

const statusText = (status) =>{
    const dict = {0:'待审核',1:'已通过',2:'已拒绝',3:'已取消'}
    if (status in dict){
        return dict[status]
    }else{
        return '-'
    }
}
const load = async ()=>{
    loading.value =true
    try {
        const res = await getReservationPageListApi(params)
        if (res.code ==200){
            tableData.value =res.data?.list
            total.value = res.data?.total
        }
    }finally{
        loading.value =false
    }
}

const handleAudit =(row,status) =>{
    const action = status ===1?'通过':'拒绝'
    // 这个里面的type是控制弹窗出来的符号的类型，其实可以随便动，可以换成success或者info
    ElMessageBox.confirm(`${action}[${row.user_name}的预约？]`,'审核',{type:'warning'}).then(
    async()=>{
        const res = await auditReservationApi(row.id,status)
            if(res.code==200){
                ElMessage.success(`审核${action}`)
                load()
            }
        }
    )
}

const handleSearch = ()=>{
    params.page = 1
    load()
}

console.log(tableData)
onMounted(()=>{
    load()
})

</script>