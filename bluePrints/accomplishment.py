import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify

from models import *
from utils.hooks import *
from config import *

accompRouter = SubRouter(__file__, prefix="/accomplishment")


@accompRouter.post("/getAllAccomplishments")
async def getAllAccomplishments(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    accomplishments = session.query(Accomplishment).order_by(Accomplishment.time).all()
    accomplishments = [Accomplishment.to_json(accomplishment) for accomplishment in accomplishments]
    return jsonify({
        "status": 200,
        "message": "全部成果获取成功",
        "accomplishments": accomplishments
    })


@accompRouter.post("/addAccomplishment")
async def addAccomplishment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    title = data["title"]
    content = data["content"]
    authorId = res["userId"]
    accomplishment = Accomplishment(title=title, content=content, authorId=authorId)
    log = Log(operatorId=authorId, operation=f"添加研究成果")
    session.add(accomplishment)
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "研究成果添加成功"
    })


@accompRouter.post("/deleteAccomplishment")
async def deleteAccomplishment(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    accompId = data["accompId"]
    accomplishment = session.query(Accomplishment).get(accompId)
    if accomplishment.authorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    session.delete(accomplishment)
    log = Log(operatorId=userId, operation=f"删除研究成果")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "研究成果删除成功"
    })
