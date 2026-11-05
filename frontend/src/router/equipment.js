import request from '@/utils/request'

// 说白了，保留增删改查四个能力就行，其他是给用户用的
export function getEquipmentPageList(params) {
    return request({
        url:`/router/equipment/list`,
        method:'get',
        params
    })
}


export function createEquipmentApi(data){
    return request({
        url:`/router/equipment`,
        method:'post',
        data
    })
}

export function updateEquipmentApi(equipmentId,data){
    return request({
        url:`/router/equipment/${equipmentId}`,
        method:'put',
        data
    })
}

export function deteleEquipmentApi(equipmentId){
    return request({
        url:`/router/equipment/${equipmentId}`,
        method:'delete',
    })
}