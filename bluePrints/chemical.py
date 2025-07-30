import json

from dateutil.relativedelta import relativedelta
from robyn import SubRouter, jsonify
from sqlalchemy import or_

from models import *
from utils.hooks import checkSessionid, checkUserAuthority, parse_chinese_year_month, parse_chinese_year

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
        "message": "药品获取成功",
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
        specification=chemicalData["specification"],
        purity=float(chemicalData["purity"]),
        site=chemicalData["site"],
        amount=0,
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
    amount = float(data["amount"])
    if amount <= 0 or amount > chemical.amount:
        return jsonify({
            "status": -3,
            "message": "请输入领用药品瓶数（可填写小数），且领用药品瓶数不能大于库存"
        })
    chemical.takerIds.append(userId)
    user = session.query(User).get(userId)
    user.takingChemicalAmount = amount
    chemical.amount -= amount
    log = Log(operatorId=userId, operation=f"领用药品：{chemical.name} {amount}瓶")
    session.add(log)
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
    chemical.amount += user.takingChemicalAmount if user.takingChemicalAmount else 0
    user.takingChemicalAmount = 0
    log = Log(operatorId=userId, operation=f"归还药品：{chemical.name}")
    session.add(log)
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
    log = Log(operatorId=userId, operation=f"补充药品：{chemical.name}")
    session.add(log)
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


@chemicalRouter.post("/getLogs")
async def getLogs(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    if user.usertype == 1:
        return jsonify({
            "status": -2,
            "message": "用户无权限"
        })
    query = session.query(Log).filter(Log.operation.contains("药品"))
    keyword = data["keyword"].strip()
    # 先检验日期
    dt = parse_chinese_year_month(keyword)
    if dt:
        start_date = dt.replace(day=1)
        end_date = start_date + relativedelta(months=1)
        logs = query.filter(Log.time >= start_date, Log.time < end_date).order_by(Log.time.desc()).all()
    # 检验药品名
    else:
        year = parse_chinese_year(keyword)
        if year:
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            logs = query.filter(Log.time >= start, Log.time < end).order_by(Log.time.desc()).all()
        else:
            operator = session.query(User).filter(User.username.contains(keyword)).first()
            if operator:
                logs = query.filter(Log.operatorId == operator.id).order_by(Log.time.desc()).all()
            else:
                logs = query.filter(Log.operation.contains(keyword)).order_by(Log.time.desc()).all()
    logs = [Log.to_json(log) for log in logs]

    return jsonify({
        "status": 200,
        "message": "药品使用情况获取成功",
        "logs": logs
    })
