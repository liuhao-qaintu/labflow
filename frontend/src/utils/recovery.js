export const recoveryStatusLabels = {
    pending:'待核验', need_more_info:'待补充', resolved:'已重置', rejected:'未通过'
}

export function credentialError(value){
    return /^[A-Za-z0-9_-]{43}$/.test(value.trim()) ? '' : '请输入完整的43位申请凭据'
}

export function recoveryStep(status){
    return {pending:1,need_more_info:1,resolved:3,rejected:2}[status] ?? 0
}

export function recoveryTime(value){
    return value ? new Date(value).toLocaleString('zh-CN',{hour12:false}) : ''
}
