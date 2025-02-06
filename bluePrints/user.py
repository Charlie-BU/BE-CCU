import datetime
import json
from datetime import timedelta
from robyn import SubRouter, jsonify
import requests
from sqlalchemy import or_
import hmac
import hashlib

from models import *
from utils.hooks import *
from config import *

userRouter = SubRouter(__file__, prefix="/user")


@userRouter.post("/login")
async def login(request):
    data = request.json()
    nameOrPhone = data["nameOrPhone"]
    password = data["password"]
    agree = data["agree"]
    if not agree:
        return jsonify({
            "status": -1,
            "message": "请同意小程序的协议与隐私政策",
        })
    existUsers = session.query(User).filter(User.username == nameOrPhone).all()
    if len(existUsers) > 1:
        return jsonify({
            "status": -4,
            "message": "存在同名用户，请用手机号登录"
        })
    user = session.query(User).filter(or_(
        User.username == nameOrPhone,
        User.phone == nameOrPhone)
    ).first()
    if not user:
        return jsonify({
            "status": -2,
            "message": "用户不存在",
        })
    if not user.checkPassword(password):
        return jsonify({
            "status": -3,
            "message": "密码错误",
        })
    if user.role == 1 and user.graduateTime:
        if datetime.now().date() > user.graduateTime:
            return jsonify({
                "status": -4,
                "message": "您已毕业，暂无法登录"
            })
    if not user.isValid:
        return jsonify({
            "status": -5,
            "message": "您暂无权登录"
        })
    rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={LOGIN_SIGNATURE}"
    sessionid = encode(rawSessionid)
    log = Log(operatorId=user.id, operation="用户登录（密码登录）")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


"""
微信一键登录接口
登录流程：
1. 小程序端调用/getOpenidAndSessionKey接口获取openid和session_key，发送至服务器端
2. 服务器端调用微信API获取接口调用凭据access_token
3. 计算用户登录态签名signature：用session_key对空字符串签名，即signature = hmac_sha256(session_key, "")
4. 服务器端调用微信API检验登录态。若返回errcode==0，通过openid获取用户进行登录（流程同密码登录）；若返回errcode==87009，签名无效，中止登录
"""


@userRouter.post("/wxLogin")
async def wxLogin(request):
    data = request.json()
    openid = data["openid"]
    session_key = data["session_key"]
    if not openid or not session_key:
        return jsonify({
            "status": -1,
            "message": "openid或session_key不存在"
        })
    params1 = {
        "grant_type": "client_credential",
        "appid": APPID,
        "secret": APPSECRET,
    }
    res1 = requests.get("https://api.weixin.qq.com/cgi-bin/token", params=params1)
    access_token = res1.json()["access_token"]
    if not access_token:
        return jsonify({
            "status": -2,
            "message": "access_token获取失败"
        })
    signature = hmac.new(session_key.encode("utf-8"), b"", hashlib.sha256).hexdigest()
    params2 = {
        "access_token": access_token,
        "openid": openid,
        "signature": signature,
        "sig_method": "hmac_sha256"
    }
    res2 = requests.get("https://api.weixin.qq.com/wxa/checksession", params=params2)
    errcode, errmsg = res2.json()["errcode"], res2.json()["errmsg"]
    if errcode != 0:
        return jsonify({
            "status": -3,
            "message": f"身份验证失败：{errmsg}"
        })
    # 可以进行登录
    user = session.query(User).filter(User.openid == openid).first()
    if not user:
        return jsonify({
            "status": -4,
            "message": "首次请通过密码登录，之后可进行微信一键登录"
        })
    if user.role == 1 and user.graduateTime:
        if datetime.now().date() > user.graduateTime:
            return jsonify({
                "status": -5,
                "message": "您已毕业，暂无法登录"
            })
    if not user.isValid:
        return jsonify({
            "status": -6,
            "message": "您暂无权登录"
        })
    rawSessionid = f"userId={user.id}&timestamp={int(time.time())}&signature={LOGIN_SIGNATURE}"
    sessionid = encode(rawSessionid)
    log = Log(operatorId=user.id, operation="用户登录（微信一键登录）")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "登录成功",
        "sessionid": sessionid,
    })


@userRouter.post("/loginCheck")
async def loginCheck(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId, timestamp = res["userId"], res["timestamp"]
    if time.time() - float(timestamp) > 10800:  # 3小时
        return jsonify({
            "status": -2,
            "message": "登录已过期，请重新登录"
        })
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户已登录",
        "data": {
            "id": user.id,
            "username": user.username,
        }
    })


@userRouter.post("/getUserInfo")
async def getUserInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "user": User.to_json(user)
    })


@userRouter.post("/getUsersInfoByIds")
async def getUsersInfoByIds(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userIds = data["userIds"]
    userIds = json.loads(userIds) if isinstance(userIds, str) else list(userIds)
    users = [session.query(User).get(userId) for userId in userIds]
    users = [User.to_json(user) for user in users]
    return jsonify({
        "status": 200,
        "message": "用户信息获取成功",
        "users": users
    })


@userRouter.post("/register")
async def register(request):
    data = request.json()
    username = data.get("username")
    gender = data.get("gender")
    email = data.get("email")
    phone = data.get("phone")
    role = data.get("role")
    degree = data.get("degree")
    workNum = data.get("workNum")
    graduateTime = datetime.strptime(data.get("graduateTime"), "%Y-%m").date() if data.get("graduateTime") else None
    password = data.get("password")
    # 唯一性校验
    existUser = session.query(User).filter(User.phone == phone).first()
    if existUser:
        return jsonify({
            "status": -3,
            "message": "该手机号已注册"
        })
    existUser2 = session.query(User).filter(User.email == email).first()
    if existUser2:
        return jsonify({
            "status": -3,
            "message": "该邮箱已注册"
        })
    existUser3 = session.query(User).filter(User.workNum == workNum).first()
    if existUser3:
        return jsonify({
            "status": -3,
            "message": "该学号 / 工号已注册"
        })
    userUnchecked = UserUnchecked(username=username, gender=gender, email=email, phone=phone, role=role, degree=degree,
                                  workNum=workNum, graduateTime=graduateTime,
                                  hashedPassword=User.hashPassword(password))
    session.add(userUnchecked)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "注册信息提交成功，请等待审核"
    })


# 管理员审核新注册用户
@userRouter.post("/checkNewUser")
async def checkNewUser(request):
    data = request.json()
    sessionid = data["sessionid"]
    myId = checkSessionid(sessionid).get("userId")
    if not checkUserAuthority(myId, "adminOnly"):
        return jsonify({
            "status": -1,
            "message": "权限不足"
        })
    opinion = data.get("opinion")
    if opinion != "agreed" and opinion != "disagreed":
        return jsonify({
            "status": -2,
            "message": "审核意见无效"
        })
    uncheckedUserId = data.get("uncheckedUserId")
    uncheckedUser = session.query(UserUnchecked).get(uncheckedUserId)
    massage = data.get("massage")
    if opinion == "disagreed":
        sendEmail(
            to=uncheckedUser.email,
            subject="用户注册拒绝通知",
            content=f"【功能分子材料研究组管理平台】抱歉，您的注册申请没有通过。\n理由：{massage}\n请调整后重新注册，谢谢！",
        )
        log = Log(operatorId=myId, operation=f"拒绝用户「{uncheckedUser.username}」注册")
        session.add(log)
        session.delete(uncheckedUser)
        session.commit()
        return jsonify({
            "status": 201,
            "message": "用户未通过审核，已通过邮件告知用户"
        })
    sendEmail(
        to=uncheckedUser.email,
        subject="用户注册通过通知",
        content=f"【功能分子材料研究组管理平台】恭喜您，您的注册申请已通过，您可在平台正常登录。谢谢！",
    )
    user = User(username=uncheckedUser.username, gender=uncheckedUser.gender, email=uncheckedUser.email,
                phone=uncheckedUser.phone, role=uncheckedUser.role, degree=uncheckedUser.degree,
                workNum=uncheckedUser.workNum, graduateTime=uncheckedUser.graduateTime,
                hashedPassword=uncheckedUser.hashedPassword)
    session.add(user)
    log = Log(operatorId=myId, operation=f"同意用户「{uncheckedUser.username}」注册")
    session.add(log)
    session.delete(uncheckedUser)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "用户通过审核，注册成功"
    })


@userRouter.post("/getOpenidAndSessionKey")
async def getOpenidAndSessionKey(request):
    tempCode = request.json().get("tempCode")
    params = {
        "appid": APPID,
        "secret": APPSECRET,
        "js_code": tempCode,
        "grant_type": "authorization_code",
    }
    response = requests.get("https://api.weixin.qq.com/sns/jscode2session", params=params)
    openid = response.json().get("openid")
    session_key = response.json().get("session_key")
    if not openid or not session_key:
        return jsonify({
            "status": -1,
            "message": response.json().get("errmsg")
        })
    return jsonify({
        "status": 200,
        "message": "openid及session_key获取成功",
        "openid": openid,
        "session_key": session_key,
    })


@userRouter.post("/storeOpenid")
async def storeOpenid(request):
    data = request.json()
    sessionid = data["sessionid"]
    userId = checkSessionid(sessionid).get("userId")
    user = session.query(User).get(userId)
    openid = data["openid"]
    if not user.openid:
        user.openid = openid
        existUsers = session.query(User).filter(User.openid == openid).all()
        for exiUser in existUsers:
            exiUser.openid = None
        session.commit()
        return jsonify({
            "status": 200,
            "message": "openid保存成功"
        })
    return jsonify({
        "status": -1,
        "message": "openid已存在"
    })


@userRouter.post("/sendEmailCaptcha")
async def sendEmailCaptcha(request):
    data = request.json()
    username = data["username"]
    workNum = data["workNum"]
    user = session.query(User).filter(User.username == username, User.workNum == workNum).first()
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户不存在或信息错误"
        })
    if not user.email:
        return jsonify({
            "status": -2,
            "message": "您未登记邮箱，请联系管理员重置密码"
        })
    captcha = generateCaptcha()
    emailCaptcha = EmailCaptcha(captcha=captcha, userId=user.id)
    session.add(emailCaptcha)
    session.commit()
    sendEmail(
        to=user.email,
        subject="忘记密码",
        content=f"【功能分子材料研究组管理平台】您好，您正在执行密码重置操作，您的验证码为『{captcha}』，有效期5分钟。若非本人操作请忽略。",
    )
    return jsonify({
        "status": 200,
        "message": "邮箱验证码发送成功"
    })


@userRouter.post("/resetPassword")
async def resetPassword(request):
    data = request.json()
    username = data["username"]
    workNum = data["workNum"]
    captcha = data["captcha"]
    user = session.query(User).filter(User.username == username, User.workNum == workNum).first()
    if not user:
        return jsonify({
            "status": -1,
            "message": "用户不存在"
        })
    allCaptchas = user.emailCaptchas
    if datetime.now() - allCaptchas[-1].createdTime > timedelta(minutes=5):
        return jsonify({
            "status": -2,
            "message": "验证码已过期"
        })
    hisCaptchas = [this.captcha for this in allCaptchas]
    for capt in allCaptchas:
        session.delete(capt)
    if captcha not in hisCaptchas:
        return jsonify({
            "status": -3,
            "message": "验证码错误"
        })
    elif captcha in hisCaptchas and captcha != hisCaptchas[-1]:
        return jsonify({
            "status": -2,
            "message": "验证码已过期"
        })
    user.hashedPassword = User.hashPassword("12345")
    log = Log(operatorId=user.id, operation=f"用户重置密码")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "密码已重置为『12345』，请尽快修改密码"
    })


@userRouter.post("/getSupervisorInfo")
async def getSupervisorInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    supervisor = session.query(User).get(user.supervisorId)
    if not supervisor:
        return jsonify({
            "status": -2,
            "message": "导师不存在"
        })
    return jsonify({
        "status": 200,
        "message": "导师获取成功",
        "supervisorName": supervisor.username,
    })


@userRouter.post("/getEquipmentAndChemicalInfo")
async def getEquipmentAndChemicalInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    equipmentCount = session.query(Equipment).filter(Equipment.takerIds.contains(userId)).count()
    equipmentEgName = session.query(Equipment).filter(
        Equipment.takerIds.contains(userId)).first().name if equipmentCount > 0 else None
    chemicalCount = session.query(Chemical).filter(Chemical.takerIds.contains(userId)).count()
    chemicalEgName = session.query(Chemical).filter(
        Chemical.takerIds.contains(userId)).first().name if chemicalCount > 0 else None
    return jsonify({
        "status": 200,
        "message": "领用设备及药品信息获取成功",
        "data": {
            "equipmentInfo": [equipmentCount, equipmentEgName],
            "chemicalInfo": [chemicalCount, chemicalEgName],
        }
    })


@userRouter.post("/modifyUserInfo")
async def modifyUserInfo(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    modified = False
    userData = data["userData"]
    userData = json.loads(userData)
    for field in userData:
        if userData[field] and getattr(user, field) != userData[field]:
            if field == "graduateTime":
                setattr(user, field, datetime.strptime(userData[field], "%Y-%m").date())
            else:
                setattr(user, field, userData[field])
            modified = True
    if not modified:
        return jsonify({
            "status": -2,
            "message": "没有修改的信息"
        })
    log = Log(operatorId=userId, operation=f"修改用户信息")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "用户信息修改成功"
    })


@userRouter.post("/modifyPassword")
async def modifyPassword(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户未登录"
        })
    userId = res["userId"]
    user = session.query(User).get(userId)
    oldPassword = data["oldPassword"]
    newPassword = data["newPassword"]
    if not user.checkPassword(oldPassword):
        return jsonify({
            "status": -2,
            "message": "原密码输入错误"
        })
    user.hashedPassword = User.hashPassword(newPassword)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "密码修改成功"
    })

# @userRouter.get("/")
# def index():
