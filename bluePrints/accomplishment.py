import datetime
import json
import os
import shutil

import oss2
from robyn import SubRouter, jsonify, serve_file
from sqlalchemy import or_, extract

from models import *
from utils.hooks import *
from config import *

accompRouter = SubRouter(__file__, prefix="/accomp")
# 初始化阿里云OSS Bucket
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)


# TODO：分页/分批
@accompRouter.post("/getAllAccomps")
async def getAllAccomps(request):
    # 清空temp文件
    path = "./temp"
    if os.path.exists(path):
        shutil.rmtree(path)  # 删除整个文件夹
        os.makedirs(path)  # 重新创建空文件夹
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    accomps = session.query(Accomplishment).order_by(Accomplishment.date.desc()).all()
    accomps = [Accomplishment.to_json(acc) for acc in accomps]
    return jsonify({
        "status": 200,
        "message": "全部成果获取成功",
        "accomps": accomps
    })


@accompRouter.post("/uploadToOSS")
async def uploadToOSS(request):
    files = request.files
    if not files or len(files) == 0:
        return jsonify({
            "message": "没有上传的图片",
            "status": -1,
        })
    try:
        file_name = list(files.keys())[0]  # 获取上传文件名
        file_data = files[file_name]  # 获取文件数据
        # 临时保存文件
        tempDir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(tempDir, exist_ok=True)
        tempPath = os.path.join(tempDir, file_name)
        with open(tempPath, "wb") as f:
            f.write(file_data)  # 直接写入二进制数据
        # 上传到 OSS
        oss_path = f'images/accomplishments/{file_name}'
        with open(tempPath, 'rb') as fileobj:
            bucket.put_object(oss_path, fileobj)
        # 获取 OSS URL
        fileUrl = f'https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_path}'
        # 删除临时文件
        os.remove(tempPath)
        return jsonify({
            "url": fileUrl,
            "message": "成功保存至阿里云OSS",
            "status": 200,
        })
    except Exception as e:
        return jsonify({
            "status": -2,
            "message": f"上传失败: {str(e)}",
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
    pic = accompData["pic"]
    category = accompData["category"]
    type = accompData["type"]
    authorId = accompData["authorId"]
    correspondingAuthorName = accompData["correspondingAuthorName"]
    otherNames = accompData["otherNames"]
    date = datetime.strptime(accompData["date"], "%Y-%m-%d").date()
    accomp = Accomplishment(title=title, content=content, pic=pic, category=category, type=type, authorId=authorId,
                            correspondingAuthorName=correspondingAuthorName, otherNames=otherNames, date=date)
    log = Log(operatorId=authorId, operation=f"添加研究成果：{title}")
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
    if accomp.pic:
        prefix = f'https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/'
        bucket.delete_object(accomp.pic[len(prefix):])
    log = Log(operatorId=userId, operation=f"删除研究成果：{accomp.title}")
    session.add(log)
    session.delete(accomp)
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
    ).order_by(Accomplishment.date.desc()).all()
    try:
        year = int(searchContent)
        if 1000 <= year <= 3000:
            accomps = session.query(Accomplishment).filter(
                extract('year', Accomplishment.date) == year
            ).order_by(Accomplishment.date.desc()).all()
    except ValueError:
        pass
    accomps = [Accomplishment.to_json(accomp) for accomp in accomps]
    return jsonify({
        "status": 200,
        "message": "查找研究成果成功",
        "accomps": accomps
    })


@accompRouter.get("/exportAccomps")
async def exportAccomps(request):
    headers = request.headers
    sessionid = headers.get("sessionid")
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    year = headers.get("year")
    year = None if year == "" else int(year)
    if year:
        accomps = session.query(Accomplishment).filter(
            extract('year', Accomplishment.date) == year
        ).order_by(Accomplishment.date.desc()).all()
    else:
        accomps = session.query(Accomplishment).order_by(Accomplishment.date.desc()).all()
    fileName, filePath = generateAccompXlsx(accomps, year)
    log = Log(operatorId=res["userId"], operation="导出研究成果")
    session.add(log)
    return serve_file(file_path=filePath, file_name=fileName)
