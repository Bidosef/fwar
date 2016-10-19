#  coding: utf-8 

import os
import tornado.ioloop
import tornado.web
import tornado.websocket
import util
from rooms import *
from players import *

from cgi import escape

import sys
reload(sys)
sys.setdefaultencoding("utf-8")


class RoomsListerHandler(tornado.web.RequestHandler):
    def initialize(self, room_lister, player_lister):
        self.room_lister = room_lister
        self.player_lister = player_lister

    def get(self):
        self.write(util.read_page("roomsList.html", rooms = room_lister.rooms, player = self.player_lister.find_player(self.get_secure_cookie("user")), player_lister = self.player_lister))

    def post(self):
        pseudo = self.get_secure_cookie("user")
        player = self.player_lister.find_player(pseudo)
        if player == None:
            self.redirect("/login")
            return
        if not player.set_room(None):
            self.redirect("/room/"+str(player.room.id))
            return
        room = Room(escape(self.get_body_argument("room_name"), quote=True).replace(':','&#58;'), player, self.room_lister)
        self.room_lister.add_room(room)
        self.redirect("/room/"+str(room.id))



class RoomHandler(tornado.web.RequestHandler):
    def initialize(self, room_lister, player_lister):
        self.room_lister = room_lister
        self.player_lister = player_lister

    def get(self, room_id):
        pseudo = self.get_secure_cookie("user")
        player = self.player_lister.find_player(pseudo)
        if player == None:
            self.redirect("/login")
            return
        if(room_id == "redirect"):
            if(player.room != None):
                self.redirect("/room/"+str(player.room.id))
            else:
                self.redirect("/rooms")
            return
        room = self.room_lister.get_room(int(room_id))
        if(room != None):
            if not player.set_room(room):
                self.redirect("/room/"+str(player.room.id))
                return
            if room.creator() is player:
                self.write(util.read_page("room.html", room = room, player = player, spectator=False, creator=True))
            else:
                if room.have_joined(pseudo):
                    self.write(util.read_page("room.html", room = room, player = player, spectator=False, creator=False))
                else:
                    self.write(util.read_page("room.html", room = room, player = player, spectator=True, creator=False))
        else:
            raise tornado.web.HTTPError(404)

        
class InscriptionHandler(tornado.web.RequestHandler):
    def initialize(self):
        pass

    def get(self):
        self.write(util.read_page("inscription.html", error = 0))

    def post(self):
        pseudo = self.get_argument("pseudo")
        if pseudo=="" or ' ' in pseudo or ':' in pseudo or '[' in pseudo or ']' in pseudo:
            self.write(util.read_page("inscription.html", error = 1))
            return
        if not util.check_pseudo(pseudo):
            self.write(util.read_page("inscription.html", error = 2))
            return
        if len(pseudo) > 12:
            self.write(util.read_page("inscription.html", error = 3))
            return
        password = self.get_argument("password")
        if len(password) <= 1:
            self.write(util.read_page("inscription.html", error = 4))
            return
        util.add_player(pseudo, password)
        self.write(util.read_page("inscription.html", error = -1))


class LoginHandler(tornado.web.RequestHandler):
    def initialize(self, player_lister):
        self.player_lister = player_lister

    def get(self):
        if self.get_secure_cookie("user"): 
            if self.player_lister.find_player(self.get_secure_cookie("user")) == None:
                self.clear_cookie("user")
            else:
                self.redirect("/")
                return
        self.write(util.read_page("login.html", error = 0))

    def post(self):
        pseudo = self.get_argument("pseudo")
        password = self.get_argument("password")
        info = self.get_argument("info")
       # if self.player_lister.find_player(pseudo) != None:
       #     self.write(util.read_page("login.html", error = 4))
       #     return
       # res, t = util.check_player(pseudo, password)
       # if res != 0:
       #     self.write(util.read_page("login.html", error = -res))
       #     return
		t=0
        uid = self.get_argument("uid")
        print(uid)
        ip = self.request.headers.get("X-Real-IP") or self.request.remote_ip
        if(not self.player_lister.create_player(pseudo, t, ip, info, uid)):
            self.write(util.read_page("login.html", error = 4))
            return
        self.set_secure_cookie("user", escape(self.get_body_argument("pseudo"), quote=True), expires_days=None)
        self.redirect("/")

class LogoutHandler(tornado.web.RequestHandler):
    def initialize(self, player_lister):
        self.player_lister = player_lister

    def get(self):
        pseudo = self.get_secure_cookie("user")
        player = self.player_lister.find_player(pseudo)
        if player.set_room(None):
            self.player_lister.remove_player(player)
        else:
            player.room.player_to_remove.append(player)
        self.clear_cookie("user")
        self.redirect("/")

class RoomSocket(tornado.websocket.WebSocketHandler):
    def initialize(self, room_lister, player_lister):
        self.room_lister = room_lister
        self.player_lister = player_lister

    def open(self, room_id, pseudo):
        if(self.get_secure_cookie("user") != pseudo):
            self.close()
            return
        self.player = self.player_lister.find_player(pseudo)
        if self.player is None:
            self.close()
            return
        self.player.set_socket_handler(self)
        self.room = room_lister.get_room(int(room_id))

    def on_message(self, message):
        if(len(message)>255):
            return
        #if message != ".":
        #    print(message)
        message = escape(message, quote=True)
        if message[0] == '0':
            self.room.message(self.player, message[1:])
        elif message[0] == '1':
            self.room.request(self.player, message[1:])
        elif message[0] == '2':
            self.room.admin_request(message[1:], self.player)
        elif message == "JOIN":
            self.room.player_join(self.player)
        elif message == "QUIT":
            self.player.set_room(None)

    def on_close(self):
        pass


class RulesHandler(tornado.web.RequestHandler):
    def initialize(self, room_lister, player_lister):
        self.room_lister = room_lister
        self.player_lister = player_lister

    def get(self):
        self.write(util.read_page("rules.html", rooms = room_lister.rooms, player = self.player_lister.find_player(self.get_secure_cookie("user")), player_lister = self.player_lister))




if __name__ == "__main__":
    room_lister = RoomLister()
    player_lister = PlayerLister()
    application = tornado.web.Application([
        (r"/", RoomsListerHandler, {"room_lister":room_lister, "player_lister":player_lister}),
        (r"/rooms", RoomsListerHandler, {"room_lister":room_lister, "player_lister":player_lister}),
        (r"/room/(.*)", RoomHandler, {"room_lister":room_lister, "player_lister":player_lister}),
        (r"/inscription", InscriptionHandler),
        (r"/login", LoginHandler, {"player_lister":player_lister}),
        (r"/logout", LogoutHandler, {"player_lister":player_lister}),
        (r"/rules", RulesHandler, {"room_lister":room_lister, "player_lister":player_lister}),
        (r"/ws/(.*)/(.*)", RoomSocket, {"room_lister":room_lister, "player_lister":player_lister})
    ], cookie_secret = "AsetdztfXEsrTDrdyh6Vtc7", static_path = os.path.join(os.path.dirname(__file__), "static"),
    debug=True)
    application.listen(int(os.environ.get("PORT", 5000)))
    tornado.ioloop.IOLoop.current().start()