import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify
from sqlalchemy import or_

from models import *
from utils.hooks import *
from config import *

accompRouter = SubRouter(__file__, prefix="/accomp")


# TODO：分页/分批
@accompRouter.post("/getAllAccomps")
async def getAllAccomps(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    accomps = session.query(Accomplishment).order_by(Accomplishment.date).all()
    accomps = [Accomplishment.to_json(acc) for acc in accomps]
    return jsonify({
        "status": 200,
        "message": "全部成果获取成功",
        "accomps": accomps
    })


@accompRouter.post("/addAccomp")
async def addAccomp(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    accompData = json.loads(data["accompData"])
    title = accompData["title"]
    content = accompData["content"]
    type = accompData["type"]
    authorId = accompData["authorId"]
    correspondingAuthorName = accompData["correspondingAuthorName"]
    otherNames = accompData["otherNames"]
    date = datetime.strptime(accompData["date"], "%Y-%m-%d").date()
    accomp = Accomplishment(title=title, content=content, type=type, authorId=authorId,
                            correspondingAuthorName=correspondingAuthorName, otherNames=otherNames, date=date)
    log = Log(operatorId=authorId, operation=f"添加研究成果")
    session.add(accomp)
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "研究成果添加成功"
    })


@accompRouter.post("/deleteAccomp")
async def deleteAccomp(request):
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
    accomp = session.query(Accomplishment).get(accompId)
    if accomp.authorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    session.delete(accomp)
    log = Log(operatorId=userId, operation=f"删除研究成果")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "研究成果删除成功"
    })


@accompRouter.post("/searchAccomp")
async def searchAccomp(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    searchContent = data["searchContent"]
    existUser = session.query(User).filter(User.username == searchContent).first()
    existUserId = None if not existUser else existUser.id
    accomps = session.query(Accomplishment).filter(
        or_(
            Accomplishment.title.contains(searchContent),
            Accomplishment.content.contains(searchContent),
            Accomplishment.authorId == existUserId,
            Accomplishment.correspondingAuthorName == searchContent,
            Accomplishment.otherNames.contains(searchContent),
        )
    ).order_by(Accomplishment.date).all()
    accomps = [Accomplishment.to_json(accomp) for accomp in accomps]
    return jsonify({
        "status": 200,
        "message": "查找研究成果成功",
        "accomps": accomps
    })
