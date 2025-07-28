from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO,join_room,leave_room,send
import random
from string import ascii_uppercase
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'C@tsg0me0w'
socketio = SocketIO(app)

class Rooms:
    def __init__(self):
        self.rooms: list[Room] = []


class Room:
    def __init__(self,code:str):
        self.code = code
        self.members = 0
        self.messages: list[dict] = []
        self.text_color = "color: #000000"

rooms = Rooms()


def generate_room_code(length:int) -> str:
    """Randomly generating room code"""
    code = "".join(random.choices(ascii_uppercase, k=length))


    return code

def get_room(room_code: str) -> Room | None:
    '''Returns Room object if there is a room with that code or None'''
    return next((room for room in rooms.rooms if room.code == room_code), None)

def get_current_date() -> str:
    now = datetime.now()
    formatted = now.strftime("%m/%d/%Y, %I:%M:%S %p")

    if formatted.startswith("0"):
        formatted = formatted[1:]
    return formatted

@app.route('/',methods=['GET','POST'])
def home():
    session.clear()
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join',False)
        create = request.form.get('create',False)

        if not name:
            return render_template("home.html", error="Please enter a name",code=code,name=name)
        if join != False and not code:
            return render_template("home.html", error="Please enter a code",code=code,name=name)



        room: Room = get_room(code)


        if create != False:
            room_code = generate_room_code(6)
            room = Room(room_code)
            rooms.rooms.append(room)
        elif room is None:
            return render_template("home.html",error="Room does not exist.",code=code,name=name)

        session["room"] = room.code
        session["name"] = name
        print(session["room"])
        print(session["name"])

        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    room_code = session.get("room")

    room: Room = get_room(room_code)

    if room_code is None or session.get("name") is None or room is None:
        return redirect(url_for("home"))


    print(room.messages)
    return render_template('room.html',code=room_code,messages=room.messages)

@socketio.on("connect")
def connect(auth):
    room_code = session.get("room")
    name = session.get("name")

    room: Room = get_room(room_code)


    if not room or not name:
        return
    if room is None:
        leave_room(room_code)
        return

    join_room(room_code)
    send({"name": name,"message": "has entered the room","date": get_current_date(),"text_color": room.text_color},to=room_code)
    room.members += 1
    print(f"{name} joined room {room_code}")

@socketio.on("disconnect")
def disconnect():
    room_code = session.get("room")
    name = session.get("name")


    room: Room = get_room(room_code)

    if room in rooms.rooms:
        room.members -= 1
        if room.members <= 0:
            rooms.rooms.remove(room)
            del room

    send({"name": name, "message": "has left the room","date": get_current_date(),"text_color": room.text_color}, to=room_code)
    print(f"{name} has left the room {room_code}")

    leave_room(room_code)

@socketio.on("message")
def message(data):
    room_code = session.get("room")
    room: Room = get_room(room_code)

    if room not in rooms.rooms:
        return


    if data['text_color'] and f"color: {data['text_color']}" != room.text_color:
        print(f"color: {data['text_color']}")
        print(room.text_color)

        room.text_color = f"color: {data['text_color']}"
        send({"name": session["name"], "message": f"changed the room {room.text_color}", "date": get_current_date(), "text_color": room.text_color},
             to=room_code)

    content = {
        "name": session.get("name"),
        "message": data["data"],
        "date": get_current_date(),
        "text_color": room.text_color,
    }

    send(content,to=room_code)
    room.messages.append(content)
    print(f"{session.get('name')} said: {data['data']} at {get_current_date()}")



if __name__ == '__main__':
    socketio.run(app,debug=True,allow_unsafe_werkzeug=True)

