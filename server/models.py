from pydantic import BaseModel


class UserCredentials(BaseModel):
    username: str
    password: str


class User(BaseModel):
    username: str
    password: str
    fullname: str
    teachercode: str
    role: str = "student"
    task: str = ""
    group: str
    taskstatus: str
    taskvars: int

    @classmethod
    def from_tuple(cls, user_tuple: tuple):
        return cls(
            username=user_tuple[0],
            password=user_tuple[1],
            fullname=user_tuple[2],
            teachercode=user_tuple[3],
            role=user_tuple[4],
            task=user_tuple[5],
            group=user_tuple[6],
            taskstatus=user_tuple[7],
            taskvars=user_tuple[8],
        )
