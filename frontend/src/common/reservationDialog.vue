<template>
    <div>
        <el-dialog :model-value="visible"
        title="预约"
        width="450px"
        @open="formRef.resetFields()"
        @close="emit('update:visible',false)">
            <el-form
            ref="formRef"
            style="width: 100%; padding-right: 30px; padding-top: 16px"
            :model="form"
            :rules="rules"
            label-width="auto"
            >
                <el-form-item disabled label="需要预约的实验室">
                    <el-input :model-value="labName" disabled />
                </el-form-item>
                <el-form-item disabled label="预约设备名称"  >
                    <el-input :model-value="equipmentName" disabled />
                </el-form-item>
                <el-form-item label="预约日期" prop="date" >
                    <el-date-picker
                        v-model="form.date"
                        format = "YYYY-MM-DD"
                        value-format = "YYYY-MM-DD"
                        placeholder = "请选择日期"
                        style ="width: 100%;margin-right: 8px;"
                        />
                </el-form-item>    
                <el-form-item label="开始时间" prop = "startTime" ">
                    <el-time-picker
                        v-model="form.startTime"
                        format = "HH:mm  "
                        value-format = "HH:mm"
                        placeholder = "请选择开始事件"
                        style ="width: 100%;;margin-right: 8px;"
                        />
                </el-form-item>   
                <el-form-item label="结束时间"  prop="endTime">
                    <el-time-picker
                        v-model="form.endTime"
                        format = "HH:mm"
                        value-format = "HH:mm"
                        placeholder = "请选择结束事件"
                        style ="width: 100%;margin-right: 8px;"
                        />
                </el-form-item> 
                <el-form-item label="备注" >
                    <el-input type="textarea" v-model="form.remark" placeholder="请输入备注信息"></el-input>
                </el-form-item>  
            </el-form>   
            <template #footer>
                <el-button @click = "emit('update:visible',false)">取消</el-button>
                <el-button type="primary" :loading="submitting" @click= "handleSubmit">确认</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref,reactive } from "vue"
import { ElMessage } from "element-plus"
import { createReservationApi } from "@/router/reservation"

const props = defineProps({
    visible:Boolean,
    labId:Number,
    labName:String,
    equipmentId:Number,
    equipmentName:String
}
)
const formRef = ref()
const submitting = ref(false)
const emit = defineEmits(['update:visible'])
const form = reactive({
    date:'',
    startTime:'09:00',
    endTime:'18:00',
    remark:''
})


const rules = {
    date:[{required:true,message:'请选择预约日期',trigger:'change'}],
    startTime:[{required:true,message:'请选择开始时间',trigger:'change'}],
    endTime:[{required:true,message:'请选择结束时间',trigger:'change'}],
}


const handleSubmit = async ()=>{
    const vaild =await formRef.value.validate().catch(() => false)
    if (!vaild) return 
    submitting.value =true
    try {
        const res =  await createReservationApi({
        lab_id:props.labId,
        equipment_id:props.equipmentId,
        date:form.date,
        start_time:form.startTime,
        end_time:form.endTime,
        remark:form.remark,
        })
        if (res.code ==200) {
            ElMessage.success('预约已提交，请等待审核')
            emit('update:visible',false)
            }
    }finally {
            submitting.value = false
        }
}
</script>