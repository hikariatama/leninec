import functools
import random

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import leninec

TESTS_QUANTITY = 20

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def f(n: int) -> int:
    if n == 1:
        return 1

    return sum(f(i) for i in range(1, n) if n % i == 0) + n


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def on_position_change(websocket: WebSocket, position: int):
    await websocket.send_text(escape_html(f"@p {position}"))


async def on_register_change(websocket: WebSocket, registers: leninec.Registers):
    await websocket.send_text(escape_html(f"@r {registers.to_str()}"))


async def on_stack_change(websocket: WebSocket, stack: leninec.Stack):
    await websocket.send_text(escape_html(f"@s {stack.to_str()}"))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("client.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vm = leninec.VM()
    vm.add_position_change_hook(functools.partial(on_position_change, websocket))
    vm.add_registers_change_hook(functools.partial(on_register_change, websocket))
    vm.add_stack_change_hook(functools.partial(on_stack_change, websocket))
    test = 0
    try:
        data = await websocket.receive_text()
        while data.startswith("@"):
            if data.startswith("@d "):
                delay = float(data.split(" ")[1])
                vm.delay = delay

            data = await websocket.receive_text()

        vm.update_code(data)

        while test in range(1 if delay else TESTS_QUANTITY):
            inp = random.randint(1, 100)
            vm.reset_state()
            vm.stack.push(inp)
            flag = "--debug" if delay else f"--test {test + 1}"
            await websocket.send_text(escape_html(f"@i {inp} {flag}"))
            await vm.run()
            if not vm.stack.is_empty:
                ans = vm.stack.pop()
                if ans != f(inp):
                    await websocket.send_text(
                        escape_html(
                            f"@e WA (Wrong Answer) test#{test + 1} ({ans} != {f(inp)})"
                        )
                    )
                    break

            test += 1
        else:
            await websocket.send_text(
                escape_html("@o Finished" if delay else "@o All tests passed")
            )

        await websocket.send_text(escape_html("@f"))
    except leninec.errors.TimeoutExceededError:
        await websocket.send_text(
            escape_html(f"@e TL (Time-Limit Exceeded) test#{test}")
        )
    except leninec.errors.VMError as e:
        await websocket.send_text(escape_html(f"@e {e.__class__.__name__}: {e}"))
    except WebSocketDisconnect:
        pass

    await websocket.close()
