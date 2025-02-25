import time

from robyn import SubRouter, WebSocket

socketRouter = SubRouter(__file__, prefix="/socket")

websocket = WebSocket(socketRouter, "/ws")

ws_ids = []


@websocket.on("message")
async def message(ws, msg):
    print(ws_ids)
    if len(ws_ids) != 2:
        print("有人离线")
        return "对方暂时不在线，请稍后再试"
    from_id = ws.id
    to_id = ws_ids[0] if ws_ids[1] == from_id else ws_ids[1]
    await ws.async_send_to(to_id, msg)
    return ""  # 若为异步函数，这个是必须的


@websocket.on("connect")
def connect(ws):
    global ws_ids
    if len(ws_ids) >= 2:
        ws_ids.remove(ws_ids[0])
    ws_ids.append(ws.id)
    ws_ids = list(set(ws_ids))  # 去重
    print("WebSocket已连接：", ws.id)


@websocket.on("close")
def close():
    print("WebSocket已关闭")
