# coding: utf-8 

from __future__ import unicode_literals
import random
import tornado.ioloop
import inspect
from collections import Counter

from players import *
import util
import traceback


# Liste type messages envoye par le serveur :
# 0 : info : ( 00pseudo connection ) ( 01pseudo rejoint partie ) ( 02pseudo quitte ) ( 03pseudo1:pseudo2 signalement) (08pseudo  signalement poucave) (09Room_id new room)
# 1 : simple message     10 message joueur  11 message modo 12 message morts  13 messages spectateurs 14 message epop 15 message multi-comptes
# 2 : compo
# S : start   SE    Srole    STOP (stop)
# T : time   Tseconds
# P : Reset signalements
# R : request   R<type>:<desc>:<arg1>:<arg2>:.....
# A : action

# Liste type messages envoye par le client :
# 0 message chat  
# 1 requete
# 2 admin 20 : commencez le jeu 21 : compo (21E = error)  22 : kick    23 : Recreer room     24 : show ip
# JOIN
# QUIT

class RoomLister():
    def __init__(self):
        self.rooms = []

    def create_room(self, name, player):
        room = Room(name, player, self)
        self.add_room(room)

    def add_room(self, room):
        self.rooms.append(room)

    def remove_room(self, room):
        if room not in self.rooms:
            print "Erreur, room pas dans la liste des rooms"
            print room
            print self.rooms
            traceback.print_stack()
            return
        self.rooms.remove(room)

    def get_room(self, room_id):
        for room in self.rooms:
            if room.id == room_id:
                return room



class Room():
    room_id = 0
    def __init__(self, name, creator, room_lister):
        self.name = name
        self.id = Room.room_id
        Room.room_id += 1
        self.playing = False
        self.players = []
        self.spectators = []
        self.phase = -1
        self.turn = 0
        self.compo = [Moderateur, Forumeur]
        self.room_lister = room_lister
        self.ban = None
        self.player_to_remove = []
        self.finished = False
        self.can_recreate = False
        self.history = []
        self.str_compo = "1/1/0/0"
        creator.set_room(self)


    def creator(self):
        return self.players[0]

    def nb_modos(self):
        return int(self.str_compo.split("/")[0])

    def nb_forumeurs(self):
        return int(self.str_compo.split("/")[1])

    def nb_multicomptes(self):
        return int(self.str_compo.split("/")[2])

    def nb_aleatoires(self):
        return int(self.str_compo.split("/")[3])

    def isRoleInCompo(self, role):
        if(role == "Moderateur" and self.nb_modos() >= 1):
            return True
        elif(role == "Forumeur" and self.nb_forumeurs() >= 1):
            return True
        elif(role == "MultiCompte" and self.nb_multicomptes() >= 1):
            return True
        elif(role == "Aleatoire" and self.nb_aleatoires() >= 1):
            return True
        return role in self.str_compo.split("/")

    def htmlClassForRole(self, role):
        if self.isRoleInCompo(role):
            return "simple_block_selected"
        else:
            return "simple_block"

    def nb_alive_players(self):
        nb = 0
        for player in self.players:
            if isrole(player.role, AlivePlayer):
                nb += 1
        return nb

    def nb_alive_forumeurs(self):
        nb = 0
        for player in self.players:
            if isrole(player.role, Forumeur):
                nb+=1
        return nb

    def nb_alive_modo(self):
        nb = 0
        for player in self.players:
            if isrole(player.role, Moderateur):
                nb+=1
        return nb

    def add_player(self, player):
        if(len(self.players) == 0):
            self.players.append(player)
        else:
            self.spectators.append(player)
        self.send_to_all_players("00", player.pseudo)

    def have_joined(self, pseudo):
        for player in self.players:
            if player.pseudo == pseudo:
                return True
        return False

    def find_player(self, pseudo):
        for player in self.players:
            if player.pseudo == pseudo:
                return player
        for player in self.spectators:
            if player.pseudo == pseudo:
                return player


    def player_join(self, player):
        if(len(self.players) < len(self.compo)):
            self.spectators.remove(player)
            self.players.append(player)
            self.send_to_all_players("01", player.pseudo)

    def remove_player(self, player):
        if player in self.players:
            if self.playing and player.role.name() != "Dead":
                return
            else:
                self.players.remove(player)
        elif player in self.spectators:
            self.spectators.remove(player)
        else:
            return
        self.send_to_all_players("02", player.pseudo)
        if(len(self.players)==0):
            self.room_lister.remove_room(self)
            for spectator in self.spectators:
                spectator.send("Q","")
                spectator.set_room(None)

    def message(self, player, message):
        if not player.role.can_post():
            return
        if(not self.playing):
            player.role.on_message(None, message)
        else:
            player.role.on_message(self.phase, message)

    def request(self, player, request):
        if not player.role.can_post():
            return
        player.role.on_request(request, self.phase)


    def admin_request(self, request, pl):
        if not (pl == self.creator() or pl.type == 1):
            return
        if self.playing:
            return
        if request[0] == "0":
            if(len(self.compo)==len(self.players)):
                self.start_game()
            else:
                self.creator().send("S", "E")
        elif request[0] == "1":
            self.change_compo(request[1:])
        elif request[0] == "2":
            self.kick(request[1:])
        elif request[0] == "3" and self.can_recreate:
            self.can_recreate = False
            self.recreate_room()
        elif request[0] == "4":
            for player in self.players:
                pl.send(13,player.pseudo + " : " + player.ip)
            for player in self.spectators:
                pl.send(15,player.pseudo + " : " + player.ip)
        elif request[0] == "5":
            for player in self.players:
                pl.send(13,player.pseudo + " : " + player.info)
            for player in self.spectators:
                pl.send(15,player.pseudo + " : " + player.info)


    def recreate_room(self):
        croom = Room(self.name, self.creator(), self.room_lister)
        self.room_lister.add_room(croom)
        croom.change_compo(self.str_compo)
        self.send_to_all_players("09",str(croom.id))


    def kick(self, pseudo):
        for i in xrange(len(self.players)):
            if self.players[i].pseudo == pseudo:
                self.send_to_all_players("07",pseudo)
                self.players[i].send("Q","")
                self.players[i].room = None
                self.players[i].socket_handler.close()
                self.players[i].socket_handler = None
                self.players.pop(i)
                break
        for i in xrange(len(self.spectators)):
            if self.spectators[i].pseudo == pseudo:
                self.send_to_all_players("07", pseudo)
                self.spectators[i].send("Q","")
                self.spectators[i].room = None
                self.spectators[i].socket_handler.close()
                self.spectators[i].socket_handler = None
                self.spectators.pop(i)
                break
        if(len(self.players)==0):
            self.room_lister.remove_room(self)
            for spectator in self.spectators:
                spectator.send("Q","")
                spectator.set_room(None)
            self.spectators = []


    def change_compo(self, string):
        compo = string.split("/")
        print compo
        composition = []
        for i in xrange(int(compo[0])):
            composition.append(Moderateur)
        for i in xrange(int(compo[1])):
            composition.append(Forumeur)
        for i in xrange(int(compo[2])):
            composition.append(MultiCompte)
        for i in xrange(int(compo[3])):
            composition.append(Aleatoire)
        if len(compo)>4:
            for role in compo[4:]:
                try:
                    class_role = globals()[role]
                    if AlivePlayer not in inspect.getmro(class_role):
                        self.creator().send(2,"E")
                        return
                    composition.append(class_role)
                except:
                    self.creator().send(2,"E")
                    return
        if(len(composition) >= len(self.players)):
            self.compo = composition
            self.str_compo = string
            self.send_to_all_players(2, string)
        else:
            self.creator().send(2,"E")


    def send_to_all_players(self, message_type, message):
        for player in self.players:
            player.send(message_type, message)
        for player in self.spectators:
            player.send(message_type, message)
        self.add_message_history(str(message_type), util.replace_smiley(message))

    def add_message_history(self, message_type, message):
        if message_type == "G":
            self.history.append("<li class='mg'>" + message + "</li>")
        elif message_type == "A":
            self.history.append("<li class='ma'>" + message + "</li>")
        elif message_type[0] == "0":
            if message_type[1] == "0": 
                self.history.append("<li class='mi'>" + message + " s'est connecté !</li>")
            elif message_type[1] == "1":
                self.history.append("<li class='mi'>" + message + " a rejoint la partie.</li>")
            elif message_type[1] == "2":
                self.history.append("<li class='mi'>" + message + " s'est deconnecté.</li>")
            elif message_type[1] == "3":
                pseudos = message.split(":")
                if pseudos[1] == "":
                    self.history.append("<li class='mi'>" + pseudos[0] + " signale personne.</li>")
                else:
                    self.history.append("<li class='mi'>" + pseudos[0] + " signale " + pseudos[1] + ".</li>")
            elif message_type[1] == "6":
                pseudos = message.split(":")
                if pseudos[1] == "":
                    self.history.append("<li class='mil'>" + pseudos[0] + " veut bannir personne.</li>")
                else:
                    self.history.append("<li class='mil'>" + pseudos[0] + " veut bannir " + pseudos[1] + ".</li>")
            elif message_type[1] == "7":
                self.history.append("<li class='mi'>" + message + " a été kick !</li>")
            elif message_type[1] in "45":
                pass
            else:
                self.history.append("<li class='mi'>" + message + "</li>")
        elif message_type[0] == "1":
            self.history.append("<li class='m" + message_type + "'>" + message + "</li>")
        elif message_type[0] == "2":
            self.history.append("<li class='mi'>La composition a été changé !</li>")
        elif message_type[0] == "S" and message_type not in ["STOP","SE"]:
            self.history.append("<h1>Le jeu vient de commencer !</h1>")


    def send_to_players(self, message_type, message, callback):
        for player in self.players:
            if callback(player):
                player.send(message_type, message)
        for player in self.spectators:
            if callback(player):
                player.send(message_type, message)

    def player_count(self):
        return len(self.players)

    def link(self):
        return "/room/"+str(self.id)

    def __equals__(self, room):
        return self.id == room.id

    def list_roles(self):
        st = []
        for role in self.compo:
            if role != Moderateur and role != Forumeur:
                st.append(role(None, None).name())
        return st



    # GAME GESTION

    def start_game(self):
        self.phase = -1
        self.playing = True
        random.shuffle(self.compo)
        for i in xrange(len(self.players)):
            self.players[i].role = self.compo[i](self.players[i], self)
            self.players[i].send("S",self.players[i].role.name())
            self.players[i].send("G",self.players[i].role.description())
        for player in self.players:
            player.role.action(self.phase)
        self.send_to_players("S","O",lambda pl: isrole(pl.role, Spectator))
        self.send_to_all_players("T","10")
        self.timeout = tornado.ioloop.IOLoop.current().call_later(10, self.next_phase)
        self.timeout2 = None
        self.ban = None
        self.boostix = False


    def most_voted_players(self):
        max_votes = max(self.players, key=lambda pl: pl.role.nb_signal if isrole(pl.role, AlivePlayer) else 0).role.nb_signal
        if(max_votes == 0):
            return []
        v = [player for player in self.players if  isrole(player.role, AlivePlayer) and player.role.nb_signal == max_votes]
        #for player in self.players:
        #    if isrole(player.role, AlivePlayer):
        #        print(player.pseudo + str(player.role.nb_signal))
        return v

    def check_boostix(self):
        self.boostix = False
        pl_votes = self.most_voted_players()
        if(len(pl_votes) == 1):
            self.send_to_all_players("G", "Suite aux nombreux signalements, " + pl_votes[0].pseudo + " qui était " + pl_votes[0].role.name() + " a été banni.")
            pl_votes[0].role.on_death(self.phase, self.turn)
            pl_votes = self.most_voted_players()
        for player in pl_votes:
            self.send_to_all_players("G", "Suite aux nombreux signalements, " + player.pseudo + " qui était " + player.role.name() + " a été banni.")
            player.role.on_death(self.phase, self.turn)
        for player in self.players:
            player.role.nb_signal = 0
            player.role.signal = None


    def next_phase(self):
        try:
            tornado.ioloop.IOLoop.current().remove_timeout(self.timeout)
            if self.timeout2 != None:
                tornado.ioloop.IOLoop.current().remove_timeout(self.timeout2)
            #End of 
            if(self.phase > 3):
                for player in self.players:
                    if isrole(player.role, SecEtNerveux):
                        player.role.on_death(self.phase, self.turn)
                        self.send_to_all_players("G","Le sec et nerveux s'est fait maitrisé et n'a donc pu éliminer personne !")
                        break
                self.phase %= 3
            elif(self.phase == 0):
                pl_votes = self.most_voted_players()
                for player in self.players:
                    player.role.nb_signal = 0
                    player.role.signal = None
                if(len(pl_votes) >= 1):
                    self.ban = pl_votes[0]
                    for player in self.players:
                        if isrole(player.role, Oldfag):
                            if isrole(player.role, Fake):
                                if self.ban == player.role.role.save:
                                    self.ban = None
                            else:
                                if self.ban == player.role.save:
                                    self.ban = None

            elif(self.phase == 1):
                if self.ban != None and isrole(self.ban.role, Dead):
                    self.ban = None
                if self.ban != None and (isrole(self.ban.role, EnfantDuForum) or isrole(self.ban.role, SummerFag)) and self.ban.role.live:
                    print "Enfant Du Forum"
                    print self.ban.role.live
                    self.ban.role.live = False
                    self.ban = None
                if(self.ban != None):
                    self.send_to_all_players("G", "Les modérateurs ont décidé de bannir " + self.ban.pseudo + " qui était " + self.ban.role.name() + ".")
                    self.ban.role.on_death(self.phase, self.turn)
                    self.ban = None
                else:
                    self.send_to_all_players("G", "Les modérateurs n'ont banni personne.")

            elif(self.phase == 2):
                if(self.boostix):
                    self.check_boostix()
                else:
                    pl_votes = self.most_voted_players()
                    nuisible = None
                    for player in self.players:
                        if isrole(player.role, Nuisible) and player.role.nb_signal >= 1 and player not in pl_votes:
                            nuisible = player
                        player.role.nb_signal = 0
                        player.role.signal = None
                    if nuisible != None:
                        self.send_to_all_players("G","Le nuisible "+nuisible.pseudo+" a été banni.")
                        nuisible.role.on_death(self.phase, self.turn)
                    if(len(pl_votes) == 1 and not isrole(pl_votes[0], Nuisible)):
                        self.send_to_all_players("G", "Suite aux nombreux signalements, " + pl_votes[0].pseudo + " qui était " + pl_votes[0].role.name() + " a été banni.")
                        pl_votes[0].role.on_death(self.phase, self.turn)
                    else:
                        self.send_to_all_players("G", "Egalité ! ")
                        for player in self.players:
                            if isrole(player.role, Victime):
                                self.send_to_all_players("G", player.pseudo + " est alors désigné à la place et se fait bannir parce que c'est une grosse victime.")
                                player.role.on_death(self.phase, self.turn)
                                break

            if(self.phase > 3):
                self.send_to_all_players("G","Le Sec et Nerveux va eliminer quelqu'un.")
                self.send_to_all_players("T","20")
                for player in self.players:
                    player.role.action(self.phase)
                self.timeout = tornado.ioloop.IOLoop.current().call_later(20, self.next_phase)
                return


            #test win
            if len([player for player in self.players if isrole(player.role, AlivePlayer)]) == 0:
                self.send_to_all_players("G", "<h2>Tout le monde est mort ! Il n'y a aucun gagnant !</h2>")
                self.end_game()
                return
            for player in self.players:
                if player.role.win():
                    self.end_game()
                    return


            self.phase = (self.phase+1)%3

            #Beginning of phases
            if(self.phase == 0):
                self.turn += 1
                t = 60
                nb_alive = self.nb_alive_modo()
                if nb_alive < 5:
                    t = 45
                if nb_alive < 3:
                    t = 30
                if nb_alive == 1:
                    t = 15
                self.send_to_all_players("T",str(t))
                self.send_to_all_players("P","")
                self.timeout = tornado.ioloop.IOLoop.current().call_later(t, self.next_phase)
                self.send_to_all_players("G", "Les modérateurs se rassemblent en secret pour le conseil, ils vont décider de bannir un forumeur")
            elif(self.phase == 1):
                self.send_to_all_players("T","15")
                self.send_to_all_players("P","")
                self.timeout = tornado.ioloop.IOLoop.current().call_later(15, self.next_phase)
                self.send_to_all_players("G", "Le conseil des modérateurs vient de se terminer")
            elif(self.phase == 2):
                t = 300
                nb_alive = self.nb_alive_players()
                if nb_alive < 24:
                    t = 240
                if nb_alive < 16:
                    t = 180
                if nb_alive < 8:
                    t = 120
                if nb_alive < 4:
                    t = 60
                self.send_to_all_players("T",str(t))
                self.timeout = tornado.ioloop.IOLoop.current().call_later(t, self.next_phase)
                self.timeout2 = tornado.ioloop.IOLoop.current().call_later(t-10, self.t_10)
                self.send_to_all_players("G", "Le forum est de nouveau actif")
            for player in self.players:
                player.role.action(self.phase)
        except Exception as e:
            print e

    def t_10(self):
        self.send_to_all_players("T","10")

    def result(self):
        for player in self.players:
            if isrole(player.role, Dead):
                rolename = player.role.role.name()
            else:
                rolename = player.role.name()
            end = " a perdu !"
            if(player.role.victory):
                end = " a gagné !"
            self.send_to_all_players("G",player.pseudo + " qui était " + rolename + end)


    def end_game(self):
        self.result()
        self.playing = False
        self.finished = True
        self.can_recreate = True
        self.send_to_all_players("STOP","")
        for pl in self.players:
            pl.role = Spectator(pl, self)
        self.send_to_all_players("G","La Room va être supprimé dans 5 minutes")
        tornado.ioloop.IOLoop.current().call_later(300, self.destroy)
        for player in self.player_to_remove:
            if player in self.players:
                player.set_room(None)



    def destroy(self):
        for player in self.players:
            player.send("Q","")
            player.set_room(None)
        for player in self.spectators:
            player.send("Q","")
            player.set_room(None)


