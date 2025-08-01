from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, Boolean, Column, Integer, String, Text, JSON, DateTime, Date, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.mutable import MutableList
from bcrypt import hashpw, gensalt, checkpw

from config import DATABASE_URI

engine = create_engine(
    DATABASE_URI,
    echo=True,
    pool_size=20,  # 默认连接池大小
    max_overflow=30,  # 最大溢出连接数
    pool_timeout=60,  # 连接超时时间
    pool_recycle=3600  # 连接回收时间，防止连接被数据库关闭
)
# 数据库表基类
Base = declarative_base()
naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
Base.metadata.naming_convention = naming_convention
# 会话，用于通过ORM操作数据库
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = Session()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(60), nullable=False)
    hashedPassword = Column(Text, nullable=False)
    # 性别：男1/女2
    gender = Column(Integer, nullable=False)
    email = Column(String(60), nullable=True)
    phone = Column(String(60), nullable=True)
    # 用户身份：学生1/教师2
    role = Column(Integer, default=False)
    # 用户权限级：普通用户1/普通管理员2/超级管理员6
    usertype = Column(Integer, nullable=False, default=1)
    # 学历：学士1/硕士2/博士3/其他4
    degree = Column(Integer, nullable=True)
    workNum = Column(String, nullable=True)
    graduateTime = Column(Date, nullable=True)
    avatarUrl = Column(Text, nullable=True)
    openid = Column(Text, nullable=True)
    activeScore = Column(Integer, nullable=True)
    isPrivate = Column(Boolean, nullable=False, default=False)
    # 研究方向
    directionId = Column(Integer, ForeignKey("direction.id"), nullable=True)
    direction = relationship("Direction", backref="users")
    # 导师（学生特有）
    supervisorId = Column(Integer, nullable=True)

    # 学生数（教师特有）
    @property
    def stuAmount(self):
        if self.role == 2:
            return session.query(User).filter(
                User.role == 1,
                User.supervisorId == self.id).count()
        return 0

    # 领用药品量（0-100）
    takingChemicalAmount = Column(Integer, nullable=True, default=0)

    # 是否有效
    @property
    def isValid(self):
        if self.role == 1 and self.graduateTime:
            if datetime.now().date() > self.graduateTime:
                return False
        return True

    @staticmethod  # 静态方法归属于类的命名空间，同时能够在不依赖类的实例的情况下调用
    def hashPassword(password):
        hashedPwd = hashpw(password.encode("utf-8"), gensalt())
        return hashedPwd.decode("utf-8")

    def checkPassword(self, password):
        return checkpw(password.encode("utf-8"), self.hashedPassword.encode("utf-8"))

    def to_json(self):
        data = {
            "id": self.id,
            "username": self.username,
            "gender": self.gender,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "usertype": self.usertype,
            "degree": self.degree,
            "workNum": self.workNum,
            "graduateTime": self.graduateTime,
            "avatarUrl": self.avatarUrl,
            "activeScore": self.activeScore,
            "isPrivate": self.isPrivate,
            "supervisorId": self.supervisorId,
            "stuAmount": self.stuAmount,
            "isValid": self.isValid,
        }
        if self.directionId:
            data["directionId"] = self.directionId
            data["directionName"] = self.direction.name
        return data


class UserUnchecked(Base):
    __tablename__ = "user_unchecked"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(60), nullable=False)
    hashedPassword = Column(Text, nullable=False)
    gender = Column(Integer, nullable=False)
    email = Column(String(60), nullable=True)
    phone = Column(String(60), nullable=True)
    role = Column(Integer, nullable=False)
    degree = Column(Integer, nullable=True)
    workNum = Column(String, nullable=False)
    graduateTime = Column(Date, nullable=True)
    directionId = Column(Integer, ForeignKey("direction.id"), nullable=True)
    direction = relationship("Direction", backref="users_unchecked")
    supervisorId = Column(Integer, nullable=True)
    joinTime = Column(DateTime, nullable=False, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "username": self.username,
            "gender": self.gender,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "degree": self.degree,
            "workNum": self.workNum,
            "graduateTime": self.graduateTime,
            "supervisorId": self.supervisorId,
            "joinTime": self.joinTime,
        }
        if self.directionId:
            data["directionId"] = self.directionId
            data["directionName"] = self.direction.name
        return data


# 研究方向
class Direction(Base):
    __tablename__ = "direction"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), nullable=False)
    description = Column(Text, nullable=True)
    responsorId = Column(Integer, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "responsorId": self.responsorId,
        }
        return data


# 项目
class Item(Base):
    __tablename__ = "item"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), nullable=False)
    description = Column(Text, nullable=True)
    # 项目类型：国家级1/省级2/校级3
    type = Column(Integer, nullable=False)
    # 项目状态：未开始1/进行中2/已完成3
    status = Column(Integer, nullable=False)
    # 项目负责人（一位）
    responsorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    responsor = relationship("User", backref="items")
    # 项目组成员id
    memberIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    startTime = Column(DateTime, nullable=False)
    endTime = Column(DateTime, nullable=False)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "responsorId": self.responsorId,
            "memberIds": self.memberIds,
            "startTime": self.startTime,
            "endTime": self.endTime,
        }
        return data


class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), nullable=False)
    # 设备状态：正常1/异常2/维修3/报废4
    status = Column(Integer, nullable=True)
    function = Column(Text, nullable=True)
    # 操作规范
    operateRegulation = Column(Text, nullable=True)
    imageUrl = Column(Text, nullable=True)
    # 设备负责人（一位）
    responsorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    responsor = relationship("User", backref="equipments")
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "function": self.function,
            "operateRegulation": self.operateRegulation,
            "imageUrl": self.imageUrl,
            "responsorId": self.responsorId,
            "responsorName": self.responsor.username,
            "info": self.info,
        }
        return data


class Chemical(Base):
    __tablename__ = "chemical"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(60), nullable=False)
    formula = Column(Text, nullable=True)
    CAS = Column(String(60), nullable=True)
    # 药品种类：无机1/有机2
    type = Column(Integer, nullable=True)
    # 药品危险性：常规1/易燃2/易爆3/腐蚀4/易制毒5/易制爆6
    dangerLevel = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 药品数量（瓶）
    amount = Column(Float, nullable=False)
    purity = Column(Float, nullable=True)
    specification = Column(Text, nullable=True)
    site = Column(Text, nullable=True)

    # 药品状态（根据药品数量动态计算）：药品数量<=1瓶：短缺；药品数量>1瓶：充足
    @property
    def status(self):
        return 2 if self.amount <= 1 else 1  # 2: 短缺, 1: 充足

    # 入库人（多个）
    registerIds = Column(MutableList.as_mutable(JSON()), nullable=False, default=[])
    # 药品负责人（一位）
    responsorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    responsor = relationship("User", backref="chemicals")
    # 领用人（多个）
    takerIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    info = Column(Text, nullable=True)

    def to_json(self):
        # 去重
        if self.registerIds and self.registerIds != list(set(self.registerIds)):
            self.registerIds = list(set(self.registerIds))
            session.commit()
        if self.takerIds and self.takerIds != list(set(self.takerIds)):
            self.takerIds = list(set(self.takerIds))
            session.commit()
        data = {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "CAS": self.CAS,
            "type": self.type,
            "dangerLevel": self.dangerLevel,
            "status": self.status,
            "purity": self.purity,
            "amount": self.amount,
            "specification": self.specification,
            "site": self.site,
            "registerIds": self.registerIds,
            "responsorId": self.responsorId,
            "takerIds": self.takerIds,
            "info": self.info,
        }
        return data


class ChemicalRecord(Base):
    __tablename__ = "chemical_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chemicalId = Column(Integer, ForeignKey("chemical.id"), nullable=False)
    chemical = relationship("Chemical", backref="records")
    userId = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", backref="chemical_records")
    info = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "chemicalId": self.chemicalId,
            "chemicalName": self.chemical.name,
            "userId": self.userId,
            "username": self.user.username,
            "info": self.info,
        }
        return data


class GroupMeeting(Base):
    __tablename__ = "group_meeting"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 常规时间
    routine = Column(Text, nullable=True)
    venue = Column(Text, nullable=True)
    theme = Column(Text, nullable=True)
    desciption = Column(Text, nullable=True)
    reporterIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    startTime = Column(DateTime, nullable=True)
    image = Column(Text, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "routine": self.routine,
            "venue": self.venue,
            "theme": self.theme,
            "desciption": self.desciption,
            "reporterIds": self.reporterIds,
            "startTime": self.startTime,
            "image": self.image,
        }
        return data


# 组会报告
class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporterId = Column(Integer, ForeignKey("user.id"), nullable=False)
    reporter = relationship("User", backref="reports")
    otherIds = Column(MutableList.as_mutable(JSON()), nullable=True, default=[])
    # 报告类型：文献类1/工作类2
    type = Column(Integer, nullable=False)
    content = Column(Text, nullable=True)
    time = Column(DateTime, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "reporterId": self.reporterId,
            "otherIds": self.otherIds,
            "type": self.type,
            "content": self.content,
            "time": self.time,
        }
        return data


# 成果
class Accomplishment(Base):
    __tablename__ = "accomplishment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(60), nullable=True)
    authorId = Column(Integer, ForeignKey("user.id"), nullable=True)
    author = relationship("User", backref="accomplishments")

    @property
    def authorName(self):
        return self.author.username if self.author else None

    correspondingAuthorName = Column(String(60), nullable=True)
    otherNames = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    pic = Column(Text, nullable=True)
    # 种类：论文成果1/项目成果2
    category = Column(Integer, nullable=True)
    # 论文成果：中科院一区1/中科院二区2/中科院三区3/中科院四区4/EI5/中文核心6/其他7
    # 项目成果：国际级1/国家级2/省级3/校级4
    type = Column(Integer, nullable=True)
    date = Column(Date, nullable=True)

    def to_json(self):
        data = {
            "id": self.id,
            "title": self.title,
            "authorId": self.authorId,
            "authorName": self.authorName,
            "correspondingAuthorName": self.correspondingAuthorName,
            "otherNames": self.otherNames,
            "content": self.content,
            "pic": self.pic,
            "category": self.category,
            "type": self.type,
            "date": self.date,
        }
        return data


class Log(Base):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    operatorId = Column(Integer, ForeignKey("user.id"), nullable=False)
    operator = relationship("User", backref="logs")
    operation = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now)

    def to_json(self):
        data = {
            "id": self.id,
            "operatorId": self.operatorId,
            "operatorName": self.operator.username,
            "operation": self.operation,
            "time": self.time,
        }
        return data


class EmailCaptcha(Base):
    __tablename__ = "email_captcha"
    id = Column(Integer, primary_key=True, autoincrement=True)
    captcha = Column(Text, nullable=False)
    createdTime = Column(DateTime, nullable=False, default=datetime.now)
    userId = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User", backref="emailCaptchas")

    def to_json(self):
        data = {
            "id": self.id,
            "captcha": self.captcha,
            "createdTime": self.createdTime,
            "userId": self.userId,
        }
        return data


class Notice(Base):
    __tablename__ = "notice"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    time = Column(DateTime, default=datetime.now, nullable=True)
    releaserId = Column(Integer, ForeignKey("user.id"), nullable=False)
    releaser = relationship("User", backref="notices")

    def to_json(self):
        data = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "time": self.time,
            "releaserId": self.releaserId,
        }
        return data

# 创建所有表（被alembic替代）
# if __name__ == "__main__":
#     Base.metadata.create_all(bind=engine)
