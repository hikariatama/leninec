import functools
import random

from database import Database
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import User, UserCredentials

import leninec


TESTS_QUANTITY = 10

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

db = Database()

PREFIX = """global f

"""


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def on_position_change(websocket: WebSocket, position: int):
    await websocket.send_text(escape_html(f"@p {position}"))


async def on_register_change(websocket: WebSocket, registers: leninec.Registers):
    await websocket.send_text(escape_html(f"@r {registers.to_str()}"))


async def on_stack_change(websocket: WebSocket, stack: leninec.Stack):
    await websocket.send_text(escape_html(f"@s {stack.to_str()}"))


@app.get("/")
async def main_page(request: Request):
    if "session" in request.cookies:
        if user := db.verify_session(request.cookies["session"]):
            if user.role == "teacher":
                return Response(status_code=302, headers={"Location": "/teacher"})

            return templates.TemplateResponse(
                "client.html",
                {
                    "request": request,
                    "fullname": user.fullname + (
                        (" из " + user.group + " класса")
                        if user.role == "student"
                        else ""
                    ),
                    "user": user,
                    "input_sample": (
                        str(
                            [random.randint(0, 20) for _ in range(int(user.taskvars))]
                        ).strip("[]")
                        if user.taskvars
                        else ""
                    ),
                },
            )

    return templates.TemplateResponse("client.html", {"request": request})


@app.post("/register")
async def register(user: User):
    if db.register(user):
        session_cookie = db.session(user.username)
        return JSONResponse(
            status_code=200,
            content={"message": "User registered successfully"},
            headers={
                "Set-Cookie": f"session={session_cookie}; HttpOnly; SameSite=Strict"
            },
        )

    return JSONResponse(status_code=400, content={"message": "Registration failed"})


@app.post("/login")
async def login(user: UserCredentials):
    if db.login(user):
        session_cookie = db.session(user.username)
        return JSONResponse(
            status_code=200,
            content={"message": "User logged in successfully"},
            headers={
                "Set-Cookie": f"session={session_cookie}; HttpOnly; SameSite=Strict"
            },
        )

    return JSONResponse(status_code=400, content={"message": "Login failed"})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/logout")
async def logout(request: Request):
    return JSONResponse(
        status_code=302,
        content={"message": "User logged out successfully"},
        headers={"Set-Cookie": "session=; HttpOnly; SameSite=Strict", "Location": "/"},
    )


def teacher_only(func):
    @functools.wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if (
            "session" in request.cookies
            and (user := db.verify_session(request.cookies["session"]))
            and user.role == "teacher"
        ):
            return await func(request, *args, **kwargs)

        return Response(status_code=302, headers={"Location": "/"})

    return wrapper


@app.get("/teacher")
@teacher_only
async def teacher_page(request: Request):
    return templates.TemplateResponse(
        "teacher.html",
        {"request": request, "groups": db.get_usergroups()},
    )


@app.get("/groups/{group}/users")
@teacher_only
async def get_group_students(request: Request, group: str):
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"users": db.get_group_users(group)}),
    )


@app.get("/groups/{group}/task")
@teacher_only
async def get_task_for_group(request: Request, group: str):
    task = db.get_group_task(group)
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                **task,
                "template": next(
                    (
                        name
                        for name, tpl in TEMPLATES.items()
                        if escape_html(tpl) == task["task"]
                    ),
                    None,
                ),
            }
        ),
    )


@app.post("/groups/{group}/task")
@teacher_only
async def update_task_for_group(
    request: Request,
    group: str,
    task: str = Form(...),
):
    if "__" in task:
        return JSONResponse(status_code=400, content={"message": "Invalid task"})

    base = (
        next(
            line
            for line in db.sanitize_task(task).splitlines()
            if line.startswith("def f(")
        )
        + "\n"
        + "    ..."
    )
    for argcount in range(1, 10):
        try:
            exec(
                (
                    PREFIX
                    + base.replace("&gt;", ">")
                    .replace("&lt;", "<")
                    .replace("&amp;", "&")
                    + "\n\nf({})".format(str([10] * argcount).strip("[]"))
                ),
                {},
                {},
            )
        except Exception:
            continue
        else:
            break
    else:
        return JSONResponse(status_code=400, content={"message": "Invalid task"})

    inp = [random.randint(0, 20) for _ in range(argcount)]

    try:
        exec(
            (
                PREFIX
                + db.sanitize_task(task)
                .replace("&gt;", ">")
                .replace("&lt;", "<")
                .replace("&amp;", "&")
                + "\n\nassert isinstance(f({}), int)".format(str(inp).strip("[]"))
            ),
            {},
            {},
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"ok": db.set_group_task(group, task, argcount)}),
    )


@app.delete("/groups/{group}/task")
@teacher_only
async def delete_task_for_group(request: Request, group: str):
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"ok": db.delete_group_task(group)}),
    )


@app.get("/me")
async def get_me(request: Request):
    if "session" in request.cookies:
        if user := db.verify_session(request.cookies["session"]):
            return JSONResponse(
                status_code=200,
                content=jsonable_encoder(user),
            )

    return JSONResponse(status_code=400, content={"message": "Not logged in"})


TEMPLATES = {
    "maths": """def f(a: int, b: int, c: int) -> int:
    return a + (b // 2) * c - 10""",
    "loop": """def f(a: int, b: int, c: int) -> int:
    for i in range(1, a + 1):
        b += c * i
    return b""",
    "recursion": """def f(a: int) -> int:
    if a == 1:
        return 1

    if a == 2:
        return 1

    return f(a - 1) + f(a - 2)""",
    "hard": """def f(n: int) -> int:
    if n == 1:
        return 1

    return sum(f(i) for i in range(1, n) if n % i == 0) + n""",
}


@app.get("/templates/{template}")
async def get_template_code(request: Request, template: str):
    if template not in TEMPLATES:
        return JSONResponse(status_code=404, content={"message": "Not found"})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"template": TEMPLATES[template]}),
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    if (
        not (session := websocket.cookies.get("session"))
        or not (user := db.verify_session(session))
        or not user.task
    ):
        await websocket.close()
        return

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
            inp = [random.randint(1, 20) for _ in range(int(user.taskvars))]
            vm.reset_state()
            for i in reversed(inp):
                vm.stack.push(i)
            flag = "--debug" if delay else f"--test {test + 1}"
            await websocket.send_text(escape_html(f"@i {inp} {flag}"))
            await vm.run()
            if not vm.stack.is_empty:
                ans = vm.stack.pop()
                try:
                    exec(
                        (
                            PREFIX
                            + user.task.replace("&gt;", ">")
                            .replace("&lt;", "<")
                            .replace("&amp;", "&")
                            + "\n\nassert f({}) == {}".format(str(inp).strip("[]"), ans)
                        ),
                        {},
                        {},
                    )
                except AssertionError:
                    await websocket.send_text(
                        escape_html(f"@e WA (Wrong Answer) test#{test + 1}")
                    )
                    break

            test += 1
        else:
            await websocket.send_text(escape_html("@o Finished" if delay else "@o OK"))
            db.set_done(user)

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
