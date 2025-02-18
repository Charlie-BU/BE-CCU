from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.chemical import chemicalRouter
from bluePrints.equipment import equipmentRouter
from bluePrints.extras import extrasRouter
from bluePrints.groupMeeting import meetingRouter
from bluePrints.user import userRouter
from chemicalBatchImport.main import importFromExcel

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)
app.include_router(chemicalRouter)
app.include_router(equipmentRouter)
app.include_router(meetingRouter)
app.include_router(extrasRouter)


@app.get("/")
async def index():
    return "Welcome to CCU Platform"


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
