import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify
import requests
from sqlalchemy import or_

from models import *
from utils.hooks import *
from config import *

equipmentRouter = SubRouter(__file__, prefix="/equipment")


@equipmentRouter.post("/getThisEquipment")
async def getThisEquipment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    equipmentId = data["equipmentId"]
    equipment = session.query(Equipment).get(equipmentId)
    equipment = Equipment.to_json(equipment)
    return jsonify({
        "status": 200,
        "message": f"设备获取成功",
        "equipment": equipment
    })


@equipmentRouter.post("/getEquipmentAmount")
async def getEquipmentAmount(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    normalEquipmentLength = session.query(Equipment).filter(Equipment.status == 1).count()
    impairedEquipmentLength = session.query(Equipment).filter(Equipment.status == 2).count()
    repairingEquipmentLength = session.query(Equipment).filter(Equipment.status == 3).count()
    damagedEquipmentLength = session.query(Equipment).filter(Equipment.status == 4).count()
    return jsonify({
        "status": 200,
        "message": "设备数量获取成功",
        "data": {
            "normalEquipmentLength": normalEquipmentLength,
            "impairedEquipmentLength": impairedEquipmentLength,
            "repairingEquipmentLength": repairingEquipmentLength,
            "damagedEquipmentLength": damagedEquipmentLength
        }
    })


@equipmentRouter.post("/getEquipments")
async def getEquipments(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    # TODO：这样慢，尝试分页获取
    equipments = session.query(Equipment).order_by(Equipment.name).all()
    equipments = [Equipment.to_json(equipment) for equipment in equipments]
    return jsonify({
        "status": 200,
        "message": "全部设备获取成功",
        "equipments": equipments
    })


@equipmentRouter.post("/searchEquipment")
async def searchEquipment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    searchContent = data["searchContent"]
    equipments = session.query(Equipment).filter(
        Equipment.name.contains(searchContent)
    ).order_by(Equipment.name).all()
    equipments = [Equipment.to_json(equipment) for equipment in equipments]
    return jsonify({
        "status": 200,
        "message": "设备查找成功",
        "equipments": equipments
    })


@equipmentRouter.post("/addEquipment")
async def addEquipment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    equipmentData = data["equipmentData"]
    equipmentData = json.loads(equipmentData)
    equipment = Equipment(
        name=equipmentData["name"],
        status=int(equipmentData["status"]),
        function=equipmentData["function"],
        operateRegulation=equipmentData["operateRegulation"],
        imageUrl=equipmentData["imageUrl"],
        responsorId=equipmentData["responsorId"],
        info=equipmentData["info"]
    )
    session.add(equipment)
    log = Log(operatorId=res["userId"], operation=f"入库设备：{equipmentData['name']}")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "设备添加成功"
    })


@equipmentRouter.post("/modifyEquipmentInfo")
async def modifyEquipmentInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    equipmentId = data["equipmentId"]
    equipment = session.query(Equipment).get(equipmentId)
    if not equipment:
        return jsonify({
            "status": -3,
            "message": "设备不存在"
        })
    if equipment.responsorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    modified = False
    equipmentData = data["equipmentData"]
    equipmentData = json.loads(equipmentData)
    for field in equipmentData:
        if equipmentData[field] and getattr(equipment, field) != equipmentData[field]:
            setattr(equipment, field, equipmentData[field])
            modified = True
    if not modified:
        return jsonify({
            "status": -2,
            "message": "没有修改的信息"
        })
    log = Log(operatorId=userId, operation=f"修改设备信息：{equipmentData['name']}")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "设备信息修改成功"
    })


@equipmentRouter.post("/deleteEquipment")
async def deleteEquipment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    equipmentId = data["equipmentId"]
    equipment = session.query(Equipment).get(equipmentId)
    if equipment.responsorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    log = Log(operatorId=userId, operation=f"删除设备：{equipment.name}")
    session.add(log)
    session.delete(equipment)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "设备删除成功"
    })
