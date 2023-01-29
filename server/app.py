import asyncio
import functools
import random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import leninec

app = FastAPI(docs_url="/")


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def on_position_change(websocket: WebSocket, position: int):
    await websocket.send_text(escape_html(f"@positionchange {position}"))


async def on_register_change(websocket: WebSocket, registers: leninec.Registers):
    await websocket.send_text(escape_html(f"@registerschange {registers.to_str()}"))


async def on_stack_change(websocket: WebSocket, stack: leninec.Stack):
    await websocket.send_text(escape_html(f"@stackchange {stack.to_str()}"))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vm = leninec.VM()
    vm.add_position_change_hook(functools.partial(on_position_change, websocket))
    vm.add_registers_change_hook(functools.partial(on_register_change, websocket))
    vm.add_stack_change_hook(functools.partial(on_stack_change, websocket))
    try:
        data = await websocket.receive_text()
        while data.startswith("@"):
            if data.startswith("@delay "):
                delay = float(data.split(" ")[1])
                vm.delay = delay

            data = await websocket.receive_text()

        vm.update_code(data)
        inp = random.randint(1, 100)
        vm.stack.push(inp)
        await websocket.send_text(escape_html(f"@input {inp}"))
        await vm.run()
        await websocket.send_text(escape_html("@finish"))
    except leninec.errors.VMError as e:
        await websocket.send_text(escape_html(f"@error {e.__class__.__name__}: {e}"))
    except WebSocketDisconnect:
        pass

    await websocket.close()
