<template>
    <div>
        <el-card style="max-width: 90%;margin:0px auto">
            <template #header>
            <div style = "font-size:16px;font-weight:bold;">
                <span>实验设备管理</span>
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
                    <el-table-column label="所属实验室" prop="lab_name" />
                    <el-table-column label="设备名称" prop="name" />
                    <el-table-column label="图片" prop="img" >
                        <template #default="{ row }">
                            <div>
                                <img v-if="row.img" 
                                :src="row.img" 
                                style="display: block; width: 50px; height: 50px; border-radius: 50%;
                                alt:">
                            </div>
                        </template>
                    </el-table-column>
                    <el-table-column label="型号规格" prop="spec" />
                    <el-table-column label="数量" prop="quantity" />
                    <el-table-column label="状态" prop="status" width = "100">
                        <template #default="{ row }">
                            <el-tag :type = "row.status ===1?'success':'danger'">
                                {{ row.status ===1 ?"正常" :'维修' }}
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
            v-loading ="formLoading"
            >
                <el-form-item label="所属实验室" prop="lab_id">
                  <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%;">
                    <el-option
                    v-for="item in labOptions"
                    :key = "item.id"
                    :label="item.name"
                    :value ="item.id"/>
                  </el-select>

                </el-form-item>
                <el-form-item label="设备名称" prop="name" >
                    <el-input  v-model="form.name" placeholder="请输入实验设备名称" />
                </el-form-item>
                <el-form-item label="说明"  >
                    <el-input type="textarea" v-model="form.description" placeholder="请输入说明" />
                </el-form-item>    
                <el-form-item label="图片" >
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
                <el-form-item label="型号规格"  >
                    <el-input v-model="form.spec" placeholder="例如 RTX4090 246" />
                </el-form-item> 
                <el-form-item label="数量" prop="quantity" >
                    <el-input-number v-model="form.quantity" :min="1" :max="100"  @change="handleChange"/>
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
import { getEquipmentPageList ,createEquipmentApi,updateEquipmentApi,deteleEquipmentApi} from '@/router/equipment';
import { Plus, Search } from '@element-plus/icons-vue';
import { ElMessage,ElMessageBox } from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { uploadFileApi } from '@/router/file'
import { getLabPageList } from '@/router/lab';

const params = reactive ({
    page:1,
    pageSize:10,
    keywords:'',
    lab_id:null,
})

const loading = ref(false)
const tableData = ref([])
const labOptions = ref([])
const total = ref(0)
const dialogTableVisible =ref(false)
const fileList=ref([])
const previewDialogVisible = ref(false)
const previewImageUrl = ref('')
const formRef = ref()
const uploadRef = ref()
const disabled = ref(false)
const form =reactive({
    id:null,
    lab_id:null,
    name:'',
    description:'',
    quantity:1,
    spec:'',
    img:'',
    status:1
})
const formLoading = ref(false)


const rules = {
    lab_id:[{required:true,message:'请选择实验室',trigger:'change'}],
    name:[{required:true,message:'请输入设备名称',trigger:'blur'}],
    quantity:[{required:true,message:'请输入数量',trigger:'blur'}],
}
// 创建和更新共用一个表单,但是不同情况的值不一样，由id决定
const resetForm = () =>{
    Object.assign(form,{
        id:null,
        lab_id:null,
        name:'',
        description:'',
        quantity:1,
        spec:'',
        img:'',
        status:1,
    })
    fileList.value =[]
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
        lab_id:row.lab_id,
        name:row.name,
        description:row.description,
        quantity:row.quantity,
        spec:row.spec,
        img:row.img,
        status:row.status
    })
    fileList.value = row.img?[{name:row.img,url:row.img}]:[],
    dialogTableVisible.value =true
}
// 删除用户
const handleDelete = (row) =>{
    ElMessageBox.confirm(`确认删除实验室设备[${row.name}]?`,`确认删除`,{ type:`warning`}).then(
        async() =>{
            const res = await deteleEquipmentApi(row.id)
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
        const res = form.id ? await updateEquipmentApi(form.id,form):await createEquipmentApi(form)
        if (res.code ==200) {
            dialogTableVisible.value =false
            ElMessage.success('操作成功')
        }else {
          ElMessage.error(res.message ||'操作失败')
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
        const res = await getEquipmentPageList({
            page:params.page,
            page_size:params.pageSize,
            keywords:params.keywords,
            lab_id:params.lab_id
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

const loadLabs = async () => {   
  const res = await getLabPageList({ page: 1, page_size: 100 })   
  if (res.code === 200) { 
    labOptions.value = res.data?.list   
  } 
}
const handleChange = (currentValue, oldValue) => {
  console.log("当前数量：", currentValue)
  console.log("原来数量：", oldValue)
}

onMounted(() => {
    loadLabs()
    load()
})
</script>
