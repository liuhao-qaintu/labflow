<template>
    <div>
        <el-card style="max-width: 90%;margin:0px auto">
            <template #header>
            <div style = "font-size:16px;font-weight:bold;">
                <span>实验室管理</span>
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
                <el-button type="success" :icon="Plus" @click="handlecreate">新增</el-button>
            </div>
                <el-table :data="tableData" style="width: 100%"
                :header-cell-style = "{backgroundColor:'#f5f7fa',color:'#333'}"
                v-loading = "loading">
                    <el-table-column label="名称" prop="name" />
                    <el-table-column label="封面" prop="img" >
                        <template #default="{ row }">
                            <div>
                                <img v-if="row.img" 
                                :src="row.img" 
                                style="display: block; width: 50px; height: 50px; border-radius: 50%;
                                alt:">
                            </div>
                        </template>
                    </el-table-column>
                    <el-table-column label="位置" prop="location" />
                    <el-table-column label="容量" prop="capacity" />
                    <el-table-column label="开放时间" width="140">
                         <template #default="{ row }">
                            {{ row.open_time && row.close_time ? `${row.open_time} - ${row.close_time}`: '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="状态" prop="status" width = "100">
                        <template #default="{ row }">
                            <el-tag :type = "row.status ===1?'success':'error'">
                                {{ row.status ===1 ?"开放" :'关闭' }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width ="160" header-align="center">
                        <template #default="{ row }">
                            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
                            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
           
        </el-card>
        <el-dialog v-model="dialogTableVisible" :title="form.id? '编辑' : '新增'" width="800">
            <el-form
            ref="formRef"
            style="max-width: 600px"
            :model="form"
            :rules="rules"
            label-width="auto"
            v-loading ="loading"
            >
                <el-form-item label="封面" >
                    <el-upload ref="uploadRef" 
                    action="#" 
                    list-type="picture-card" 
                    :auto-upload="true" 
                    :http-request ="handleFileUpload" 
                    accept="image/jpeg,image/png,image/gif,image/webp" 
                    :before-upload = "beforeAvatarUpload"
                    v-model:file-list="fileList">
                        <el-dialog v-model="previewDialogVisible" title="图片预览">
                            <img v-if="previewImageUrl" :src="previewImageUrl" alt="封面预览" style="display: block; max-width: 40%; margin: 0 auto" />
                        </el-dialog>
                        <el-icon><Plus /></el-icon>
                        <template #file="{ file }">
                            <div>
                                <img class="el-upload-list__item-thumbnail" :src="file.url" alt="" />
                                <span class="el-upload-list__item-actions">
                                    <span class="el-upload-list__item-preview" @click="handlePictureCardPreview(file)">
                                        <el-icon><zoom-in /></el-icon>
                                    </span>
                                    <span  v-if="!disabled"  class="el-upload-list__item-delete" @click="handleDownload(file)">
                                        <el-icon><Download /></el-icon>
                                    </span>
                                    <span v-if="!disabled" class="el-upload-list__item-delete" @click="handleRemove(file)">
                                        <el-icon><Delete /></el-icon>
                                    </span>
                                </span>
                            </div>
                        </template>
                    </el-upload>
                </el-form-item>
                <el-form-item label="名称" prop="name" >
                    <el-input  v-model="form.name" placeholder="请输入实验室名称" />
                </el-form-item>
                <el-form-item label="位置" prop="location" >
                    <el-input  v-model="form.location" placeholder="请输入位置" />
                </el-form-item>
                <el-form-item label="容量" prop="capacity" >
                    <el-input v-model="form.capacity" placeholder="请输入名称" />
                </el-form-item>      
                <el-form-item label="开放时间">
                    <el-time-picker
                        v-model="form.open_time"
                        format = "HH:mm"
                        value-format = "HH:mm"
                        placeholder = "开始"
                        style ="width:140px;margin-right: 8px;"
                        />
                    <el-time-picker
                        v-model="form.close_time"
                        format = "HH:mm"
                        value-format = "HH:mm"
                        placeholder = "结束"
                        style ="width:140px;"
                        />
                </el-form-item>
                <el-form-item label="简介" prop="description" >
                    <el-input v-model="form.description" placeholder="请输入简介" />
                </el-form-item> 
                <el-form-item label="状态">
                    <el-radio-group v-model="form.status">
                        <el-radio :value="1">正常</el-radio>
                        <el-radio :value="0">禁用</el-radio>
                    </el-radio-group>
                </el-form-item>
            </el-form>   
            <template #footer>
                <el-button @click = "dialogTableVisible=false">取消</el-button>
                <el-button type="primary" :loading="formLoading" @click= "handleSave">确认</el-button>
            </template>
        </el-dialog>

    </div>
</template>

<script setup>
import { ref,reactive,onMounted } from 'vue'
import { getLabPageList ,createLabApi,updateLabApi,deteleLabApi} from '@/router/lab';
import { Plus, Search } from '@element-plus/icons-vue';
import { ElMessage,ElMessageBox } from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { uploadFileApi } from '@/router/file'

const params = reactive ({
    page:1,
    pageSize:10,
    keywords:''
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogTableVisible =ref(false)
const fileList = ref([])
const previewDialogVisible = ref(false)
const previewImageUrl = ref('')
const formRef = ref()
const uploadRef = ref()
const disabled = ref(false)
const form =reactive({
    id:'',
    name:'',
    location:'',
    description:'',
    capacity:20,
    open_time:'08:00',
    close_time:'18:00',
    img:'',
    status:1
})
const formLoading = ref(false)


const rules = {
    name:[{required:true,message:'请输入实验室名称',trigger:'blur'}],
    capacity:[{required:true,message:'请输入容纳人数',trigger:'blur'}],
}
// 创建和更新共用一个表单,但是不同情况的值不一样，由id决定
const resetForm = () =>{
    Object.assign(form,{
        id:null,
        name:'',
        location:'',
        description:'',
        capacity:20,
        open_time:'08:00',
        close_time:'18:00',
        img:'',
        status:1
    })
    fileList.value = []
}

const beforeAvatarUpload = (file) => {
    const imageTypes = ['image/jpg','image/jpeg','image/png','image/gif','image/webp']
    if (!imageTypes.includes(file.type)) {
        ElMessage.error ('只能上传图片')
        return false
    }
    if (file.size/ 1024 /1024> 2){
        ElMessage.error ('那我问你')
        return false
    }
    return true
}

const handleFileUpload = async ({file})=> {
    try {
        const res = await uploadFileApi(file)
        if (res.code === 200){
            form.img = res.data?.url
        } else {
            ElMessage.error(res.message || '图片上传失败')
        }
    } catch (error) {
        ElMessage.error(error?.message || '图片上传失败')
    }
}

const handlePictureCardPreview = (file) => {
    previewImageUrl.value = file.url
    previewDialogVisible.value = true
}

const handleDownload = (file) => {
    const link = document.createElement('a')
    link.href = file.url
    link.download = file.name || 'image'
    link.click()
}

const handleRemove = (file) => {
    form.img = ''
    uploadRef.value?.handleRemove(file)
}


const handlecreate = () =>{
    resetForm()
    dialogTableVisible.value = true
}

const handleEdit = (row) =>{
    resetForm()
    Object.assign(form,{
        id:row.id,
        name:row.name,
        location:row.location,
        description:row.description,
        capacity:row.capacity,
        open_time:row.open_time,
        close_time:row.close_time,
        img:row.img,
        status:row.status
    })
    fileList.value = row.img ? [{ name: row.img, url: row.img }] : []
    dialogTableVisible.value =true
}
// 删除用户
const handleDelete = (row) =>{
    ElMessageBox.confirm(`确认删除实验室[${row.name}]?`,`确认删除`,{ type:`warning`}).then(
        async() =>{
            const res = await deteleLabApi(row.id)
            if(res.code==200){
            ElMessage.success('删除成功')
            load()       
            }
        }
    )
}
// 保存用户
const handleSave = async () =>{
    const vaild =await formRef.value.validate().catch(() => false)
    if (!vaild) return 
    formLoading.value =true
    try {
        const res = form.id ? await updateLabApi(form.id,form):await createLabApi(form)
        if (res.code ==200) {
            dialogTableVisible.value =false
            ElMessage.success('操作成功')
        }
    }finally {
            load()
            formLoading.value = false
        }
}
// 加载分页数据
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

onMounted(() => {
    load()
})
</script>
