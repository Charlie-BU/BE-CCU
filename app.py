from robyn import Robyn, ALLOW_CORS, jsonify

from bluePrints.chemical import chemicalRouter
from bluePrints.groupMeeting import meetingRouter
from bluePrints.user import userRouter
from models import *

app = Robyn(__file__)
ALLOW_CORS(app, origins=["*"])

# 注册蓝图
app.include_router(userRouter)
app.include_router(chemicalRouter)
app.include_router(meetingRouter)


@app.get("/")
async def index():
    return "Welcome to CCU Platform"


@app.get("/add")
async def add():
    for i in range(10):
        item = Item(name=f"item{i}", description=f"This is item {i}")
        session.add(item)
    session.commit()
    return {
        "status": 200,
        "message": "success"
    }


@app.get("/delete")
async def delete():
    item1 = session.query(Item).get(1)
    item2 = session.query(Item).filter_by(name="item5").first()
    if not item1 or not item2:
        return {
            "status": -1,
            "message": "nonexistent"
        }
    session.delete(item1)
    session.delete(item2)
    session.commit()
    return {
        "status": 200,
        "message": "success"
    }


@app.get("/modify")
async def modify():
    item1 = session.query(Item).get(3)
    if not item1:
        return {
            "status": -1,
            "message": "nonexistent"
        }
    item1.description = "This is a modified description"
    session.commit()
    return {
        "status": 200,
        "message": "success"
    }


@app.get("/query")
async def query():
    all_items = session.query(Item).all()
    return {
        "status": 200,
        "message": "success",
        "items": [Item.to_json(all_item) for all_item in all_items]
    }


@app.post("/find_items")
async def find_items(request):
    data = request.json()
    if data.get("code") != "PASSWORD":
        return {
            "status": -1,
            "message": "unauthorized",
        }
    all_items = session.query(Item).all()
    return {
        "status": 200,
        "message": "success",
        "items": [Item.to_json(all_item) for all_item in all_items]
    }


@app.post("/send_json")
async def send_json(request):
    data = request.json().get('message')  # 字典格式
    print(f"接收到消息: {data}")  # 输出收到的消息
    return jsonify({
        "status": 200,
        "message": "success",
        "data": data
    })


@app.get("/send_args")
async def send_args(request):
    data = request.query_params.get("message")  # 不是字典
    print(f"接收到消息: {data}")  # 输出收到的消息
    return {"message": data}  # 返回解析后的消息


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8050)
