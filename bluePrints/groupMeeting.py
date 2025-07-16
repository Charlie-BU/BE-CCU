import json
import os
import oss2
from robyn import SubRouter, jsonify

from config import *
from models import *
from utils.hooks import checkSessionid, checkUserAuthority

meetingRouter = SubRouter(__file__, prefix="/meeting")
# 初始化阿里云OSS Bucket
auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)


@meetingRouter.post("/getAllMeetings")
async def getAllMeetings(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    meetings = session.query(GroupMeeting).order_by(GroupMeeting.id.desc()).all()
    meetings = [GroupMeeting.to_json(meeting) for meeting in meetings]
    return jsonify({
        "status": 200,
        "message": "全部组会安排获取成功",
        "meetings": meetings
    })


# 注意：单个图片上传接口，只能传一张
@meetingRouter.post("/uploadToOSS")
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
        oss_path = f'images/conference/{file_name}'
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


@meetingRouter.post("/addMeeting")
async def addMeeting(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    meetingPics = json.loads(data["meetingPics"])
    for meetingPic in meetingPics:
        meeting = GroupMeeting(image=meetingPic)
        session.add(meeting)
    log = Log(operatorId=userId, operation=f"添加组会安排")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "组会安排添加成功"
    })


@meetingRouter.post("/deleteMeeting")
async def deleteMeeting(request):
    data = request.json()
    sessionid = data["sessionid"]
    res = checkSessionid(sessionid)
    if not res:
        return jsonify({
            "status": -1,
            "message": "用户无权限"
        })
    userId = res["userId"]
    if not checkUserAuthority(userId, "adminOnly"):
        return jsonify({
            "status": -2,
            "message": "权限不足"
        })
    meetingId = data["meetingId"]
    meeting = session.query(GroupMeeting).get(meetingId)
    image = meeting.image
    prefix = f'https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/'
    bucket.delete_object(image[len(prefix):])
    session.delete(meeting)
    log = Log(operatorId=userId, operation=f"删除组会安排")
    session.add(log)
    session.commit()
    return jsonify({
        "status": 200,
        "message": "组会安排删除成功"
    })