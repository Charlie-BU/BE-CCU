import base64
import hashlib
import hmac
import os
import re
import string
import time
import pandas as pd
import yagmail
import random

from dateutil import parser
from sqlalchemy import extract

from config import LOGIN_SECRET, EMAIL_ADDRESS, EMAIL_PWD, EMAIL_HOST
from models import session, User, Accomplishment


def encode(inputString):
    byteString = inputString.encode('utf-8')
    base64_bytes = base64.b64encode(byteString)
    encodedString = base64_bytes.decode()
    return encodedString


def decode(encodedString):
    try:
        base64_bytes = encodedString.encode('utf-8')
        byteString = base64.b64decode(base64_bytes)
        decodedString = byteString.decode()
    except Exception:
        return None
    return decodedString


# 计算sessionid携带签名
def calcSignature(message):
    secret = LOGIN_SECRET.encode('utf-8')
    message = str(message).encode('utf-8')
    signature = hmac.new(secret, message, hashlib.sha512).hexdigest()
    return signature


def checkSignature(signature, message):
    secret = LOGIN_SECRET.encode('utf-8')
    message = str(message).encode('utf-8')
    correctSig = hmac.new(secret, message, hashlib.sha512).hexdigest()
    return hmac.compare_digest(signature, correctSig)


def checkSessionid(sessionid):
    decodedSessionid = decode(sessionid)
    if not decodedSessionid:
        return None
    pattern = rf"^userId=(\d+)&timestamp=(\d+)&signature=(.+)&algorithm=sha256$"  # 必须用()包含住捕获组才能被match.group捕获
    match = re.match(pattern, decodedSessionid)
    if not match:
        return None
    userId = match.group(1)
    timestamp = match.group(2)
    signature = match.group(3)
    if not checkSignature(signature, userId):  # 签名无效
        return None
    if time.time() - float(timestamp) > 10800:  # 3小时有效
        return None
    return {
        "userId": int(userId),
        "timestamp": timestamp
    }


def checkUserAuthority(userId, operationLevel="adminOnly"):
    user = session.query(User).get(userId)
    usertype = user.usertype
    if operationLevel == "adminOnly":
        return usertype == 2 or usertype == 6
    elif operationLevel == "superAdminOnly":
        return usertype == 6
    else:
        return True


def sendEmail(to, subject=None, content=None):
    yag = yagmail.SMTP(EMAIL_ADDRESS, EMAIL_PWD, host=EMAIL_HOST)
    yag.send(to, subject, content)


def generateCaptcha():
    source = string.digits * 6
    captcha = random.sample(source, 6)
    captcha = "".join(captcha)
    return captcha


def getAccompTypeConvention(category, type):
    category, type = int(category), int(type)
    convention = {}
    if category == 1:
        convention = {
            1: "中科院一区",
            2: "中科院二区",
            3: "中科院三区",
            4: "中科院四区",
            5: "EI",
            6: "中文核心",
            7: "其他"
        }
    elif category == 2:
        convention = {
            1: "国际级",
            2: "国家级",
            3: "省级",
            4: "校级"
        }
    return convention[type]


def generateAccompXlsx(accomps, year=None):
    fileName = f"研究成果-{year}年.xlsx" if year else "研究成果-全部.xlsx"
    filePath = os.path.join("./temp", fileName)
    # 构造DataFrame
    data = []
    for accomp in accomps:
        data.append({
            "成果标题": accomp.title,
            "成果内容": accomp.content,
            "成果种类": "论文成果" if accomp.category == 1 else "项目成果",
            "成果类型": getAccompTypeConvention(accomp.category, accomp.type),
            "发表日期": accomp.date.strftime("%Y-%m-%d") if accomp.date else "",
            "第一作者 / 项目负责人": accomp.authorName,
            "通讯作者": accomp.correspondingAuthorName,
            "其他成员": accomp.otherNames,
        })
    df = pd.DataFrame(data)
    # 写入Excel
    os.makedirs(os.path.dirname(filePath), exist_ok=True)
    df.to_excel(filePath, index=False, engine="openpyxl")
    if not os.path.exists(filePath):
        raise Exception(f"Excel文件未成功生成: {filePath}")
    return fileName, filePath


def parse_chinese_year_month(s: str):
    match = re.fullmatch(r'(\d{4})年(\d{1,2})月', s.strip())
    if not match:
        return None
    iso_str = f"{match.group(1)}-{match.group(2)}"
    return parser.parse(iso_str)


def parse_chinese_year(s: str):
    match = re.fullmatch(r'(\d{4})年', s.strip())
    if not match:
        return None
    return int(match.group(1))