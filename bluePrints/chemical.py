import json

from robyn import SubRouter, jsonify
from sqlalchemy import or_

from models import *
from utils.hooks import checkSessionid, checkUserAuthority

chemicalRouter = SubRouter(__file__, prefix="/chemical")


@chemicalRouter.post("/getThisChemical")
async def getThisChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    chemical = Chemical.to_json(chemical)
    return jsonify({
        "status": 200,
        "message": f"药品获取成功",
        "chemical": chemical
    })


@chemicalRouter.post("/getChemicalAmount")
async def getChemicalAmount(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    allChemicalLength = session.query(Chemical).count()
    inorganicChemicalLength = session.query(Chemical).filter(Chemical.type == 1).count()
    organicChemicalLength = allChemicalLength - inorganicChemicalLength
    # 易制毒制爆
    dangerousChemicalLength = session.query(Chemical).filter(
        or_(
            Chemical.dangerLevel.contains(5),
            Chemical.dangerLevel.contains(6))
    ).count()
    return jsonify({
        "status": 200,
        "message": "药品数量获取成功",
        "data": {
            "allChemicalLength": allChemicalLength,
            "inorganicChemicalLength": inorganicChemicalLength,
            "organicChemicalLength": organicChemicalLength,
            "dangerousChemicalLength": dangerousChemicalLength
        }
    })


@chemicalRouter.post("/getChemicals")
async def getChemicals(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    filterType = data["filterType"]
    # 无机药品
    if filterType == "1":
        chemicals = session.query(Chemical).filter(Chemical.type == 1).order_by(Chemical.formula).all()
        info = [201, "无机"]
    elif filterType == "2":
        chemicals = session.query(Chemical).filter(Chemical.type == 2).order_by(Chemical.formula).all()
        info = [202, "有机"]
    elif filterType == "3":
        chemicals = session.query(Chemical).filter(
            or_(
                Chemical.dangerLevel.contains(5),
                Chemical.dangerLevel.contains(6))
        ).order_by(Chemical.formula).all()
        info = [203, "易制毒制爆"]
    else:
        chemicals = session.query(Chemical).order_by(Chemical.formula).all()
        info = [200, "全部"]
    # TODO：这样慢，尝试获取每个药品的briefData，或分页获取
    chemicals = [Chemical.to_json(chemical) for chemical in chemicals]
    return jsonify({
        "status": info[0],
        "message": f"{info[1]}药品获取成功",
        "chemicals": chemicals
    })


@chemicalRouter.post("/getMyChemicals")
async def getMyChemicals(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicals = session.query(Chemical).filter(Chemical.takerIds.contains(userId)).order_by(Chemical.formula).all()
    chemicals = [Chemical.to_json(chemical) for chemical in chemicals]
    return jsonify({
        "status": 200,
        "message": "在借药品获取成功",
        "chemicals": chemicals
    })


@chemicalRouter.post("/searchChemical")
async def searchChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    searchContent = data["searchContent"]
    chemicals = session.query(Chemical).filter(or_(
        Chemical.name.contains(searchContent),
        Chemical.formula.contains(searchContent)
    )).order_by(Chemical.formula).all()
    chemicals = [Chemical.to_json(chemical) for chemical in chemicals]
    return jsonify({
        "status": 200,
        "message": f"药品查找成功",
        "chemicals": chemicals
    })


@chemicalRouter.post("/addChemical")
async def addChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    chemicalData = data["chemicalData"]
    chemicalData = json.loads(chemicalData)
    chemical = Chemical(
        name=chemicalData["name"],
        formula=chemicalData["formula"],
        CAS=chemicalData["CAS"],
        type=chemicalData["type"],
        dangerLevel=chemicalData["dangerLevel"],
        amount=1,
        info=chemicalData["info"],
        responsorId=chemicalData["responsorId"],
        registerIds=chemicalData["registerIds"],
    )
    session.add(chemical)
    log = Log(operatorId=res["userId"], operation=f"入库药品：{chemicalData["name"]}")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品入库成功"
    })


@chemicalRouter.post("/deleteChemical")
async def deleteChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    if chemical.responsorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    log = Log(operatorId=userId, operation=f"删除药品：{chemical.name}")
    session.add(log)
    session.delete(chemical)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品删除成功"
    })


@chemicalRouter.post("/takeChemical")
async def takeChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    if userId in chemical.takerIds:
        return jsonify({
            "status": -2,
            "message": "您已领用该药品"
        })
    amount = int(data["amount"])
    if amount <= 0 or amount > 100:
        return jsonify({
            "status": -3,
            "message": "请输入1～100间数字，表示领用该药品数量百分比"
        })
    if chemical.amount < amount / 100:
        return jsonify({
            "status": -4,
            "message": "药品剩余量不足领用量"
        })
    chemical.takerIds.append(userId)
    user = session.query(User).get(userId)
    user.takingChemicalAmount = amount
    chemical.amount -= amount / 100
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品领用成功"
    })


@chemicalRouter.post("/returnChemical")
async def returnChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    if userId not in chemical.takerIds:
        return jsonify({
            "status": -2,
            "message": "您未领用该药品"
        })
    chemical.takerIds.remove(userId)
    user = session.query(User).get(userId)
    chemical.amount += user.takingChemicalAmount / 100 if user.takingChemicalAmount else 0
    user.takingChemicalAmount = 0
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品归还成功"
    })


@chemicalRouter.post("/supplementChemical")
async def supplementChemical(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    chemical.registerIds.append(userId)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品补充成功"
    })


@chemicalRouter.post("/modifyChemicalInfo")
async def modifyChemicalInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    chemicalId = data["chemicalId"]
    chemical = session.query(Chemical).get(chemicalId)
    if chemical.responsorId != userId and not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    modified = False
    chemicalData = data["chemicalData"]
    chemicalData = json.loads(chemicalData)
    for field in chemicalData:
        if chemicalData[field] and getattr(chemical, field) != chemicalData[field]:
            setattr(chemical, field, chemicalData[field])
            modified = True
    if not modified:
        return jsonify({
            "status": -2,
            "message": "没有修改的信息"
        })
    log = Log(operatorId=userId, operation=f"修改药品信息：{chemicalData["name"]}")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "药品信息修改成功"
    })
