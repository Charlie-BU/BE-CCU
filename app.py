from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.chemical import chemicalRouter
from bluePrints.equipment import equipmentRouter
from bluePrints.extras import extrasRouter
from bluePrints.groupMeeting import meetingRouter
from bluePrints.user import userRouter
from models import *

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


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8050)
