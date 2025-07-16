import os
import pathlib

from robyn import Robyn, ALLOW_CORS, jsonify
from robyn.templating import JinjaTemplate

from bluePrints.chemical import chemicalRouter
from bluePrints.equipment import equipmentRouter
from bluePrints.extras import extrasRouter
from bluePrints.groupMeeting import meetingRouter
from bluePrints.accomplishment import accompRouter
from bluePrints.user import userRouter
from bluePrints.socketRouter import socketRouter

current_file_path = pathlib.Path(__file__).parent.resolve()
JINJA_TEMPLATE = JinjaTemplate(os.path.join(current_file_path, "templates"))

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)
app.include_router(chemicalRouter)
app.include_router(equipmentRouter)
app.include_router(meetingRouter)
app.include_router(accompRouter)
app.include_router(extrasRouter)
app.include_router(socketRouter)


@app.get("/")
async def index():
    return JINJA_TEMPLATE.render_template("index.html")


# 下面可以放临时数据操作

# @app.get("/supervisorsBatchImport")
# async def supervisorsBatchImport():
#     supervisorList = [
#         ["韩利民", 1], ["王翠艳", 2], ["吕莉", 2], ["吴瑞凤", 2],
#         ["郝剑敏", 2], ["洪海龙", 1], ["王亚琦", 1], ["白一甲", 1], ["杜玉英", 2],
#         ["李彦杰", 1], ["李潇", 2], ["张威", 1], ["武朝军", 1],
#         ["胡宇强", 1], ["高雪川", 1], ["高媛媛", 2], ["郭庆祥", 1], ["谢晓虹", 2],
#         ["解瑞俊", 1], ["霍丽丽", 2], ["闫丽岗", 1], ["祁建磊", 1], ["张天行", 1],
#         ["陈秋月", 2], ["贾慧劼", 2], ["宋丽君", 2]
#     ]
#     for one in supervisorList:
#         supervisor = User(username=one[0], gender=int(one[1]), role=2,
#                           directionId=4,
#                           hashedPassword=User.hashPassword("ref43i$wf4uib"))
#         session.add(supervisor)
#     session.commit()
#     return jsonify({
#         "status": 200,
#         "message": "success",
#     })


# @app.get("/chemicalBatchImport")
# async def chemicalBatchImport():
#     path = "chemicalBatchImport/chemicals.xlsx"
#     importFromExcel(path)
#     return jsonify({
#         "status": 200,
#         "message": "success",
#     })


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8050)
