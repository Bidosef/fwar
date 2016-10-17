# coding: utf-8 
from __future__ import unicode_literals

import time
import tornado.ioloop
import util
import random
import copy

#Phase
BEGIN = -1
CONSEIL = 0
APRES_CONSEIL = 1
DEBAT = 2



class Player():
    def __init__(self, pseudo, t, ip, info, uid):
        self.pseudo = pseudo
        self.last_action = time.time()
        self.room = None
        self.socket_handler = None
        self.role = None
        self.history = []
        self.uid = ""
        self.type = t
        self.ip = ip
        self.info = info
        if(uid == ""):
            self.info += "  UID VIDE"

    def action(self):
        self.last_action = time.time()

    def set_room(self, room):
        if self.room == room:
            return True
        if self.room != None and self.room.playing and isrole(self.role, AlivePlayer):
            return False
        if self.room != None:
            self.room.remove_player(self)
        if(self.socket_handler != None):
            self.socket_handler.close()
        self.room = room
        self.history = []
        self.socket_handler = None
        if self.room != None:
            self.role = Spectator(self, self.room)
            self.room.add_player(self)
        else:
            self.role = None
        self.action()
        return True


    def set_socket_handler(self, socket_handler):
        self.socket_handler = socket_handler
        self.action()

    def send(self, message_type, message):
        if(self.socket_handler == None):
            return
        try:
            if(str(message_type)[0] == "1"):
                message = str(util.replace_smiley(message))
            self.socket_handler.write_message(str(message_type)+str(message))
        except:
            pass

    def to_deco(self):
        return time.time() - self.last_action > 600 and self.set_room(None)


class PlayerLister():
    def __init__(self):
        self.players = []
        self.timeout = None

    def create_player(self, pseudo, t, ip, info, uid=""):
        player = Player(pseudo, t, ip, info, uid)
        if(uid!=""):
            player.uid = uid
            for pl in self.players:
                if pl.uid == uid:
                    return False
        self.players.append(player)
        self.check_deco()
        return True
        

    def remove_player(self, player):
        self.players.remove(player)

    def find_player(self, pseudo):
        if pseudo is None:
            return
        for player in self.players:
            if player.pseudo.lower() == pseudo.lower():
                return player

    def check_deco(self):
        if self.timeout != None:
            tornado.ioloop.IOLoop.current().remove_timeout(self.timeout)
        deco = []
        for player in self.players:
            if player.to_deco():
                deco.append(player)
        print str(time.time()) + "  Deco automatique :"
        for player in deco:
            self.remove_player(player)
            print player.pseudo
        if(len(self.players)>0):
            self.timeout = tornado.ioloop.IOLoop.current().call_later(30, self.check_deco)







#BASE ROLES

def isrole(instance, cls):
    if isinstance(instance, Fake) and instance.role != None:
        return cls == Fake or isrole(instance.role, cls)
    return isinstance(instance,cls) or (isinstance(instance, Promu) and isinstance(instance.role, cls) and cls != Forumeur) or (isinstance(instance, PetitBras) and isinstance(instance.role, cls))


class Role():
    def __init__(self, player, room):
        self.player = player
        self.room = room
        self.last_message_time = 0
        self.victory = False
        self.can_speak = True

    def can_post(self):
        return (time.time() - self.last_message_time) > 2

    def on_message(self, phase, message):
        self.last_message_time = time.time()
        self.player.action()

    def action(self, phase):
        pass

    def reload_action(self, phase):
        pass

    def on_request(self, request, phase):
        self.last_message_time = time.time()
        self.player.action()

    def on_death(self, phase, turn):
        pass

    def name(self):
        return ""

    def description(self):
        return ""

    def win(self):
        return False

    def value(self):
        return 0

    def victoryChance(self, fvalue, mvalue):
        pass

class AlivePlayer(Role):
    def __init__(self, player, room):
        Role.__init__(self, player, room)
        self.signal = None
        self.alive_players = []
        self.nb_signal = 0

    def action(self, phase):
        self.alive_players = []
        if phase == DEBAT:
            req = "S1:Signaler:personne"
            for player in self.room.players:
                if player.role.name() != "Dead":
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)

    def reload_action(self, phase):
        sign = self.signal
        self.action(phase)
        self.signal = sign

    def on_request(self, request, phase):
        Role.on_request(self, request, phase)
        if phase == DEBAT:
            n = int(request)
            if n == -1:
                if self.signal != None:
                    self.signal.role.nb_signal -= 1
                    self.signal = None
                    self.room.send_to_all_players("03", self.player.pseudo+":")
            elif self.signal != self.alive_players[n]:
                if self.signal != None:
                    self.signal.role.nb_signal -=1
                self.signal = self.alive_players[n]
                self.signal.role.nb_signal += 1
                self.room.send_to_all_players("03", self.player.pseudo+":"+self.signal.pseudo)

    def on_message(self, phase, message):
        Role.on_message(self, phase, message)
        if phase == DEBAT and self.can_speak:
            self.room.send_to_all_players(10, "<b>"+self.player.pseudo + "</b> : " + message)

    def on_death(self, phase, turn):
        self.player.role = Dead(self.player, self.room, self)
        self.room.send_to_all_players("04",self.player.pseudo)








class Forumeur(AlivePlayer):
    def __init__(self, player, room):
        AlivePlayer.__init__(self, player, room)
        self.forumeurs = []


    def name(self):
        return "Forumeur"

    def description(self):
        return "Vous êtes forumeur, votre but est de gagner avec les autres forumeurs en éliminant tout les modérateurs."

    def win(self):
        for player in self.room.players:
            if isrole(player.role, Moderateur) or isrole(player.role, SuceBoule) or isrole(player.role, EnfantDuForum):
                return False
        self.room.send_to_all_players("G", "<h2>Les Forumeurs ont gagné !</h2>")
        for player in self.room.players:
            if isrole(player.role, Forumeur) or (isrole(player.role, Dead) and isrole(player.role.role, Forumeur)):
                player.role.victory = True
        return True

    def value(self):
        return 10

    def victoryChance(self, fvalue, mvalue):
        self.vc = fvalue*2 - mvalue
        if self.vc < 1:
            self.vc = 1




class Moderateur(AlivePlayer):
    def __init__(self, player, room):
        AlivePlayer.__init__(self, player, room)

    def on_message(self, phase, message):
        AlivePlayer.on_message(self, phase, message)
        if phase == CONSEIL:
            self.room.send_to_players(11, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, Moderateur))
            self.room.send_to_players(11, "<b>???</b> : " + message, lambda pl: isrole(pl.role, Hacker) or isrole(pl.role, ExMod))

    def action(self, phase):
        AlivePlayer.action(self, phase)
        self.forumeurs = []
        if phase == CONSEIL:
            req = "S1:Bannir:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer) and not isrole(player.role, Moderateur) and (not isrole(player.role, Fantome) or  player.role.speak) and not isrole(player.role, ExMod):
                    req+=":"+player.pseudo
                    self.forumeurs.append(player)
            self.player.send("R", req)

    def reload_action(self, phase):
        sign = self.signal
        self.action(phase)
        self.signal = sign

    def on_request(self, request, phase):
        AlivePlayer.on_request(self, request, phase)
        if phase == CONSEIL:
            n = int(request)
            if n == -1:
                if self.signal != None:
                    self.signal.role.nb_signal -= 1
                    self.signal = None
                    self.room.send_to_players("06", self.player.pseudo+":", lambda pl: isrole(pl.role, Moderateur))
            elif self.signal != self.forumeurs[n]:
                if self.signal != None:
                    self.signal.role.nb_signal -= 1
                self.signal = self.forumeurs[n]
                self.signal.role.nb_signal += 1
                self.room.send_to_players("06", self.player.pseudo+":"+self.signal.pseudo, lambda pl: isrole(pl.role, Moderateur))

    def name(self):
        return "Moderateur"

    def description(self):
        return "Vous êtes modérateur, votre but est de gagner avec les autres modérateurs en éliminant tout les forumeurs"

    def win(self):
        for player in self.room.players:
            if (isrole(player.role, Forumeur) and not isrole(player.role, SummerFag)) or isrole(player.role, EnfantDuForum):
                return False
        self.room.send_to_all_players("G", "<h2>Les Modérateurs ont gagné !</h2>")
        for player in self.room.players:
            if (isrole(player.role, Moderateur) or isrole(player.role, SuceBoule)) or (isrole(player.role, Dead) and (isrole(player.role.role, Moderateur) or isrole(player.role.role, SuceBoule))):
                player.role.victory = True
        return True

    def value(self):
        return 40

    def victoryChance(self, fvalue, mvalue):
        self.vc = mvalue

class Dead(Role):
    def __init__(self, player, room, role):
        Role.__init__(self, player, room)
        self.nb_signal = 0
        self.signal = None
        self.role = role

    def on_message(self, phase, message):
        Role.on_message(self, phase, message)
        self.room.send_to_players(12, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, Dead))
        if(phase == CONSEIL):
            self.room.send_to_players(12, "<b>???</b> : " + message, lambda pl: isrole(pl.role, Reclam))

    def name(self):
        return "Dead"

class Spectator(Role):
    def __init__(self, player, room):
        Role.__init__(self, player, room)

    def on_message(self, phase, message):
        Role.on_message(self, phase, message)
        if self.player.type == 1:
            self.room.send_to_all_players(11, "<b>"+self.player.pseudo + "</b> : " + message)
        elif(phase == None):
            self.room.send_to_all_players(10, "<b>"+self.player.pseudo + "</b> : " + message)
        else:
            self.room.send_to_players(13, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, Spectator))

    def name(self):
        return "Spectateur"


class Aleatoire(Role):
    def __init__(self, player, room):
        Role.__init__(self, player, room)
        self.role = random.choice([Forumeur, Stalker, MageNoir, Hacker, Poucave, Victime, ExMod, Floodeur, Epop, Fantome, KikooJap, Oldfag, First, Reclam, Boostix, BGTimide, Fake])(player, room)

    def action(self, phase):
        self.player.role = self.role

    def name(self):
        return self.role.name()

    def description(self):
        return self.role.description()




# ROLES Uniques


class Stalker(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.sonde = False

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.sonde = False
            req = "S2:Stalker:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer):
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)

    def reload_action(self, phase):
        if phase == APRES_CONSEIL and not self.sonde:
            self.action(phase)
        else:
            Forumeur.reload_action(self, phase)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL:
            n = int(request)
            if n != -1 and not self.sonde:
                self.sonde = True
                pl = self.alive_players[n]
                rolename = pl.role.name()
                if isrole(pl.role, ExMod):
                    rolename = "Moderateur"
                elif isrole(pl.role, SuceBoule):
                    rolename = "Forumeur"
                elif isrole(pl.role, Promu) and isrole(pl.role, Fake):
                    rolename = pl.role()
                elif isrole(pl.role, Fake) and pl.role.role != None:
                    rolename = pl.role.role.name()
                    if isrole(pl.role.role, ExMod):
                        rolename = "Moderateur"
                self.room.send_to_all_players("A","Le stalker a trouvé un " + rolename)
                self.player.send("A", "Grâce à vos talent de stalkage, vous avez trouvé que " + pl.pseudo + " est enfait un " + rolename)

    def name(self):
        return "Stalker"

    def description(self):
        return "Vous êtes Stalker, votre but est de gagner avec les forumeurs. Chaque tour, vous pourrez stalker quelqu'un et révéler son rôle."

    def value(self):
        return 35

class Poucave(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.signal2 = None

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.signal2 = None
            req = "S2:Denoncer:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer):
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)

    def reload_action(self, phase):
        if phase == APRES_CONSEIL and self.signal2 == None:
            self.action(phase)
        else:
            Forumeur.reload_action(self, phase)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL:
            n = int(request)
            if n!=-1 and self.signal2 == None:
                self.signal2 = self.alive_players[n]
                self.signal2.role.nb_signal += 2
                self.room.send_to_all_players("A", "La poucave a dénoncé " + self.signal2.pseudo + " !")
                self.room.send_to_all_players("08",self.signal2.pseudo)

    def name(self):
        return "Poucave"

    def description(self):
        return "Vous êtes une Poucave, votre but est de gagner avec les forumeurs. Apres chaque conseil, vous pourrez choisir de denoncer un autre joueur. Celui-ci aura alors 2 signalements contre lui"

    def value(self):
        return 25

class Hacker(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Hacker"

    def description(self):
        return "Vous êtes Hacker, votre but est de gagner avec les forumeurs. Grâce à vos pouvoirs, vous allez pouvoir espionner les conversations des modérateurs lors des conseils."

    def value(self):
        return 15

class MageNoir(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.life = True
        self.death = True

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase==APRES_CONSEIL:
            if self.life and self.room.ban != None:
                self.player.send("R", "B:Sauver:"+self.room.ban.pseudo)
            if self.death:
                req = "S2:Bannir:personne"
                for player in self.room.players:
                    if isrole(player.role, AlivePlayer):
                        req+=":"+player.pseudo
                        self.alive_players.append(player)
                self.player.send("R", req)

    def reload_action(self, phase):
        if phase == APRES_CONSEIL:
            self.action(phase)
        else:
            Forumeur.action(self, phase)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL:
            if self.life and request == "":
                self.life = False
                self.room.ban = None
            elif self.death:
                n = int(request)
                if n!=-1:
                    self.death = False
                    self.room.send_to_all_players("A","Le Mage Noir a décidé d'utiliser ses pouvoirs pour bannir " + self.alive_players[n].pseudo + " qui était " + self.alive_players[n].role.name() + " .")
                    self.alive_players[n].role.on_death(phase, self.room.turn)

    def name(self):
        return "Mage Noir"

    def description(self):
        return "Vous êtes Mage Noir, votre but est de gagner avec les forumeurs. Grâce a vos pouvoirs, vous pourrez sauver une victime des moderateurs et tuez un joueur de votre choix."

    def value(self):
        return 25


class Epop(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def on_message(self, phase, message):
        if phase == DEBAT:
            self.room.send_to_all_players(14, "<b>"+self.player.pseudo + "</b> : " + message)

    def name(self):
        return "Epop"

    def description(self):
        return "Vous êtes Epop, votre rôle est de gagner avec les forumeurs."

    def value(self):
        return 12

class Folaillon(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.can_signal = True

    def on_death(self, phase, turn):
        if phase == DEBAT and self.can_signal:
            self.can_signal = False
            self.room.send_to_all_players("G","Cependant, en voyant ses messages, les admins ont prit pitié de son cas et ont décidé de le debannir pour cette fois.")
        else:
            Forumeur.on_death(self, phase, turn)

    def action(self, phase):
        if self.can_signal:
            Forumeur.action(self, phase)

    def reload_action(self, phase):
        if self.can_signal:
            Forumeur.reload_action(self, phase)

    def on_request(self, request, phase):
        if self.can_signal:
            Forumeur.on_request(self, request, phase)

    def name(self):
        return "Folaillon"

    def description(self):
        return "Vous êtes un Folaillon, votre but est de gagner avec les forumeurs. La premiere fois que vous êtes banni à cause des signalements des forumeurs, vous survivez mais perdez votre droit de signalement."

    def value(self):
        return 12


class Reclam(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Habitué du Reclam"

    def description(self):
        return "Vous êtes un Habitué du Reclam, votre but est de gagner avec les forumeurs. Vous pourrez voir des messages des joueurs banni à certains moments de la partie."

    def value(self):
        return 20

class SecEtNerveux(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def on_death(self, phase, turn):
        if(phase < 3):
            self.room.phase += 3
        else:
            Forumeur.on_death(self, phase, turn)

    def action(self, phase):
        Forumeur.action(self, phase)
        if(phase > 3):
            req = "S2:Eliminer:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer) and player != self.player:
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)

    def reload_action(self, phase):
        if(phase > 3):
            self.action(phase)
        else:
            Forumeur.reload_action(self, phase)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if(phase == 4 or phase == 5):
            n = int(request)
            if n!= -1:
                self.room.send_to_all_players("A", "Le sec est nerveux a décidé d'éliminer " + self.alive_players[n].pseudo + " qui était " + self.alive_players[n].role.name())
                self.alive_players[n].role.on_death(phase, self.room.turn)
                Forumeur.on_death(self, phase, self.room.turn)
                self.room.next_phase()

    def name(self):
        return "Sec et nerveux"

    def description(self):
        return "Vous êtes sec et nerveux, votre but est de gagner avec les forumeurs. Si vous êtes banni, vous pourrez choisir un joueur de votre choix et l'éliminer"

    def value(self):
        return 15

class First(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.count = 2

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.count -= 1
            if self.count <= 0:
                req = "S2:Eliminer:personne"
                for player in self.room.players:
                    if isrole(player.role, AlivePlayer):
                        req+=":"+player.pseudo
                        self.alive_players.append(player)
                self.player.send("R", req)

    def reload_action(self, phase):
        if phase == APRES_CONSEIL and self.count <= 0:
            self.action(phase)
        else:
            Forumeur.reload_action(self, phase)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL:
            n = int(request)
            if n!=0 and self.count <= 0:
                self.count = 3
                self.room.send_to_all_players("A","Le first sanglant a eliminé " + self.alive_players[n].pseudo + " qui était " + self.alive_players[n].role.name() + " !")
                if isrole(self.alive_players[n].role, Moderateur):
                    self.room.send_to_all_players("A", self.alive_players[n].pseudo + " étant un moderateur, " + self.player.pseudo + " qui était le first sanglant se retrouve banni !")
                    self.player.role.on_death(phase, self.room.turn)
                self.alive_players[n].role.on_death(phase, self.room.turn)


    def name(self):
        return "First sanglant"

    def description(self):
        return "Vous êtes un first sanglant, votre but est de gagner avec les forumeurs. Vous pouvez decider tout les 3 tours d'eliminer quelqu'un, cependant si le joueur que vous eliminez est un moderateur, vous finirez banni !"

    def value(self):
        return 15


class Victime(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Victime"

    def description(self):
        return "Vous êtes une victime, votre but est de gagner avec les forumeurs. Si il y a égalité lors de signalement, c'est vous qui finissez éliminé."

    def value(self):
        return 7

class Oldfag(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.save = None

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == CONSEIL:
            req = "S2:Défendre:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer) and player != self.save:
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)
            self.save = None

    def reload_action(self, phase):
        if phase == APRES_CONSEIL and self.count <= 0:
            self.action(phase)
        else:
            Forumeur.reload_action(self, phase)


    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == CONSEIL:
            n = int(request)
            if n != -1:
                self.save = self.alive_players[n]
                self.player.send("A","Vous defendez " + self.alive_players[n].pseudo + " des moderateurs ce tour.")

    def name(self):
        return "Oldfag"

    def description(self):
        return "Vous êtes un Oldfag, votre but est de gagner avec les forumeurs. Durant chaque conseil, vous pouvez défendre quelqu'un. Celui-ci ne pourra pas se faire ban par les moderateurs. Vous ne pouvez pas choisir deux fois de suite la même personne."

    def value(self):
        return 20

class MultiCompte(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def on_message(self, phase, message):
        Forumeur.on_message(self, phase, message)
        if phase == APRES_CONSEIL:
            self.room.send_to_players(15, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, MultiCompte))

    def name(self):
        return "Multi-compte"

    def description(self):
        return "Vous êtes un multi-compte, votre but est de gagner avec les forumeurs. Vous pourrez communiquer avec les autres multi-comptes apres le conseil."

    def value(self):
        return 10 + (self.room.nb_multicomptes()-1)*4

class KikooJap(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == DEBAT:
            for i in xrange(len(self.alive_players)):
                if self.alive_players[i] == self.player and (self.check(self.alive_players[(i-1)%len(self.alive_players)].role) or self.check(self.alive_players[(i+1)%len(self.alive_players)].role)):
                    self.room.send_to_all_players("A","Nya !")

    def check(self, role):
        return isrole(role, Moderateur) or isrole(role, ExMod)

    def name(self):
        return "Kikoo Jap"

    def description(self):
        return "Vous êtes un kikoo jap, votre but est de gagner avec les forumeurs. Si un moderateur se trouve a coté de vous, vous miaulez. Nya !"

    def value(self):
        return 25

class Fantome(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.speak = False

    def on_message(self, phase, message):
        Forumeur.on_message(self, phase, message)
        if phase == DEBAT:
            self.speak = True

    def name(self):
        return "Forumeur Fantome"

    def description(self):
        return "Vous êtes un forumeur fantome, votre but est de gagner avec les forumeurs. Tant que vous ne parlez pas, vous ne vous ferez pas bannir par les modérateurs."

    def value(self):
        return 12

class Floodeur(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == DEBAT:
            self.player.send("R", "B:Flooder:")

    def on_request(self, request, phase):
        if phase == DEBAT and request == "":
            self.room.send_to_all_players("G","Flood massif sur les forum, celui-ci devient inacessible et les signalements sont annulés !")
            for player in self.room.players:
                player.role.nb_signal = 0
                player.role.signal = None
            self.room.send_to_all_players("G","Suite au Flood massif, le conseil des moderateurs a du être tenu en urgence pour s'occuper du floodeur.")
            self.room.ban = self.player
            self.room.phase += 1
            self.room.next_phase()
        else:
            Forumeur.on_request(self, request, phase)


    def name(self):
        return "Floodeur"

    def description(self):
        return "Vous êtes un floodeur, votre but est de gagner avec les forumeurs. Durant une phase de débat, vous pouvez decider de flooder pour y mettre fin. Tout les signalements seront alors annulés mais vous serez banni par les modos lors du conseil !"

    def value(self):
        return 14

class Alpha(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Alpha"

    def description(self):
        return "Vous êtes un forumeur alpha, votre but est de gagner avec les forumeurs. Vous ne pouvez ni être charmé par l'AW, ni être recruté en tant que petit bras, ni être promu en moderateur."

    def value(self):
        return 15

class ExMod(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def on_message(self, phase, message):
        AlivePlayer.on_message(self, phase, message)
        if phase == CONSEIL:
            self.room.send_to_players(11, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, Moderateur))
            self.room.send_to_players(11, "<b>???</b> : " + message, lambda pl: isrole(pl.role, Hacker))
            self.player.send(11, "<b>"+self.player.pseudo + "</b> : " + message)

    def name(self):
        return "Ex-Moderateur"

    def description(self):
        return "Vous êtes un ex-moderateur, votre but est de gagner avec les forumeurs. Vous pouvez voir les messages des moderateurs et leurs envoyer des messages. Ils ne peuvent pas vous bannir durant un conseil mais certains roles vous confondront pour un vrai moderateur."

    def value(self):
        return 15

class Fake(Forumeur):
    def __init__(self, player, room):
        self.role = None
        Forumeur.__init__(self, player, room)
        self.choix_role = None

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if self.role != None and name not in ["role","player","room"]:
            self.role.__dict__[name] = value

    def __getattr__(self, name):
        if name in ["role","player","room"]:
            return self.__dict__[name]
        if self.role == None:
            return self.__dict__[name]
        return self.role.__dict__[name]

    def on_message(self, phase, message):
        if(self.role == None):
            Forumeur.on_message(self, phase, message)
        else:
            self.role.on_message(phase, message)

    def action(self, phase):
        if(self.role == None):
            Forumeur.action(self, phase)
            if(phase == APRES_CONSEIL):
                self.choix_role = random.choice([Forumeur, Stalker, MageNoir, Hacker, Poucave, Victime, ExMod, Floodeur, Epop, Fantome, KikooJap, Oldfag, First, Reclam, Boostix, BGTimide])(self.player, self.room)
                self.player.send("R","B:Usurper:"+self.choix_role.name())
        else:
            self.role.action(phase)

    def on_request(self, request, phase):
        if(self.role == None):
            Forumeur.on_request(self, request, phase)
            if(phase == APRES_CONSEIL):
                if request == "":
                    self.role = self.choix_role
                    self.role.player = self.player
                    self.player.send("A","Vous êtes devenu un "+self.role.name())
                    self.player.send("A",self.role.description())
        else:
            self.role.on_request(request, phase)

    def on_death(self, phase, turn):
        if(self.role != None and isrole(self.role, SecEtNerveux) and phase < 3):
            self.room.phase += 3
        else:
            Forumeur.on_death(self, phase, turn)

    def win(self):
        if(self.role == None):
            return Forumeur.win(self)
        else:
            return self.role.win()

    def name(self):
        if(self.role == None):
            return "Fake"
        else:
            return "Fake "+self.role.name()

    def description(self):
        return "Vous êtes un fake. Votre but est de gagner avec les forumeurs. Une fois durant la partie, vous pourrez choisir de prendre le role d'un forumeur choisis au hasard."

    def value(self):
        return 21

class Boostix(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.canUseBoost = True

    def action(self, phase):
        Forumeur.action(self, phase)
        if(phase == DEBAT and self.canUseBoost):
            self.player.send("R","B:Booster:")

    def on_request(self, request, phase):
        if(phase == DEBAT and request == "" and self.canUseBoost):
            self.canUseBoost = False
            self.room.boostix = True
            return
        Forumeur.on_request(self, request, phase)


    def name(self):
        return "Boostix"

    def description(self):
        return "Vous êtes un boostix. Votre but est de gagner avec les forumeurs. Une fois durant la partie, vous pourrez décider que les deux joueurs les plus signalé (et tout ceux qui sont à égalité avec eux) seront banni."

    def value(self):
        return 18

class Rageux(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def on_request(self, request, phase):
        Role.on_request(self, request, phase)
        if phase == DEBAT:
            n = int(request)
            if n == -1:
                if self.signal != None:
                    self.signal.role.nb_signal -= 2
                    self.signal = None
                    self.room.send_to_all_players("03", self.player.pseudo+":")
            elif self.signal != self.alive_players[n]:
                if self.signal != None:
                    self.signal.role.nb_signal -=2
                self.signal = self.alive_players[n]
                self.signal.role.nb_signal += 2
                self.room.send_to_all_players("03", self.player.pseudo+":"+self.signal.pseudo)

    def name(self):
        return "Rageux"

    def description(self):
        return "Vous êtes un rageux. Votre but est de gagner avec les forumeurs. Vos signalements comptent double mais les autres joueurs ne le savent pas."

    def value(self):
        return 18

class Nuisible(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Nuisible"

    def description(self):
        return "Vous êtes un nuisible. Votre but est de gagner avec les forumeurs. Un signalement suffit pour vous faire bannir mais si vous avez la majorité des signalements, vous n'êtes pas banni."

    def value(self):
        return 1

class BGTimide(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.choix = None

    def action(self, phase):
        Forumeur.action(self, phase)
        if self.choix != None and isrole(self.choix.role, Dead):
            self.choix = None
        if phase == CONSEIL and self.choix == None:
            req = "S2:Parler à:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer):
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)


    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == CONSEIL and self.choix == None:
            n = int(request)
            if n != -1:
                self.choix = self.alive_players[n]

    def on_message(self, phase, message):  
        if self.choix != None:
            self.choix.send(15, "<b>"+self.player.pseudo + "</b> : " + message)

    def name(self):
        return "BG Timide"

    def description(self):
        return "Vous êtes un bg timide. Votre but est de gagner avec les forumeurs. La nuit vous pourrez choisir une personne, vous ne pourrez parler qu'avec celle-ci la journée. Quand cette personne meurt, vous pourrez choisir une autre personne."

    def value(self):
        return 7

class KolossalBlagueur(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.blague = True

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.blague = True
            req = "S2:Faire une blague:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer):
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and self.blaque:
            self.blague = False
            n = int(request)
            if n != -1:
                player = self.alive_players[n]
                player.send("A",self.player.pseudo+" vous a envoyé une blague KOLOSSAL !")
                self.player.send("A","Vous avez fait une blaque à "+player.pseudo)
                if(isrole(player.role, Moderateur)):
                    self.room.send_to_all_players("A",self.player.pseudo+" a été banni à cause de son kolossal talent !")
                    self.on_death(phase, self.room.turn)

    def name(self):
        return "Kolossal Blagueur"

    def description(self):
        return "Vous êtes un Kolossal blagueur, votre but est de gagner avec les forumeurs. Chaque nuit vous pourrez envoyer une blague à un joueur, si ce joueur est un moderateur vous êtes banni."

    def value(self):
        return 21


#########################################
#                                       #
#                                       #
#               MODOS                   #
#                                       #
#                                       #
#########################################


class Cedric(Moderateur):
    def __init__(self, player, room):
        Moderateur.__init__(self, player, room)
        self.modos = []
        self.count = 2

    def action(self, phase):
        Moderateur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.count -= 1
            if self.count <= 0:
                self.count = 2
                req = "S2:Eliminer:personne"
                for player in self.room.players:
                    if player != self.player and (isrole(player.role, Moderateur) and not isrole(player.role, Fantome)) or isrole(player.role, ExMod):
                        req+=":"+player.pseudo
                        self.modos.append(player)
                if len(self.modos) != 0:
                    self.player.send("R",req)

    def on_request(self, request, phase):
        Moderateur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and self.count == 2:
            n = int(request)
            if n!=-1:
                self.room.send_to_all_players("A","Cedric Ciré a décidé d'éliminer " + self.modos[n].pseudo + " qui était " + self.modos[n].role.name() + " !")
                self.modos[n].role.on_death(phase, self.room.turn)

    def win(self):
        alive = [player for player in self.room.players if isrole(player.role, AlivePlayer) and not isrole(player.role, SummerFag)]
        if self.player in alive and len(alive)==1:
            self.room.send_to_all_players("G","<h2>Cedric Ciré a gagné !</h2>")
            self.victory = True
            return True
        return False

    def description(self):
        return "Vous êtes Cédric ciré, votre but est de gagner seul. Vous avez les mêmes pouvoirs qu'un moderateur mais vous pourrez également éliminer un moderateur tout les deux tours."

    def name(self):
        return "Cédric Ciré"

    def value(self):
        return 10


class Admin(Moderateur):
    def __init__(self, player, room):
        Moderateur.__init__(self, player, room)
        self.promotion = False

    def action(self, phase):
        Moderateur.action(self, phase)
        if not self.promotion and phase == APRES_CONSEIL:
            req = "S2:Promouvoir:personne"
            for player in self.room.players:
                if isrole(player.role, Forumeur) and not isrole(player.role, ExMod):
                    req+=":"+player.pseudo
                    self.forumeurs.append(player)
            self.player.send("R", req)

    def on_request(self, request, phase):
        Moderateur.on_request(self, request, phase)
        if not self.promotion and phase == APRES_CONSEIL:
            n = int(request)
            if n!= -1:
                if(isrole(self.forumeurs[n].role, Dead)):
                    self.player.send("A", "Votre choix a été annulé !")
                    return
                elif(isrole(self.forumeurs[n].role, Alpha)):
                    self.player.send("A", self.forumeurs[n].pseudo + " est un forumeur alpha qui ne veut pas devenir un moderateur esclave.")
                    return
                self.promotion = True
                self.forumeurs[n].role = Promu(self.forumeurs[n], self.room, self.forumeurs[n].role)

    def name(self):
        return "Admin"

    def description(self):
        return "Vous êtes un admin, votre but est de gagner avec les moderateurs. Vous pourrez promouvoir un forumeur de votre choix une nuit, celui-ci rejoindra le camp des moderateurs et gardera ses pouvoirs"

    def value(self):
        return 100


class Promu(Moderateur):
    def __init__(self, player, room, role):
        self.role = role
        Moderateur.__init__(self, player, room)
        if isrole(role, Oldfag) or isrole(role, AW):
            player.send("A", "Vous avez été promu modérateur !")
        else:
            player.send("A", "Vous avez été promu modérateur, vous gardez vos pouvoirs et vous devez gagner avec les moderateurs !")

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if name not in ["role","player","room"]:
            self.role.__dict__[name] = value

    def __getattr__(self, name):
        if name in ["role","player","room"]:
            return self.__dict__[name]
        return self.role.__dict__[name]
        

    def on_message(self, phase, message):
        if phase == CONSEIL:
            Moderateur.on_message(self, phase, message)
        else:
            self.role.on_message(phase, message)

    def action(self, phase):
        if phase == CONSEIL:
            Moderateur.action(self, phase)
        else:
            self.role.action(phase)

    def on_request(self, request, phase):
        if phase == CONSEIL:
            Moderateur.on_request(self, request, phase)
        else:
            self.role.on_request(request, phase)

    def on_death(self, phase, turn):
        self.role.on_death(phase, turn)
        if isrole(self.role, Dead):
            Moderateur.on_death(self, phase, turn)

    def win(self):
        if self.role.win():
            return True
        else:
            return Moderateur.win(self)

    def name(self):
        return "Moderateur "+self.role.name()

class ModerateurTyrannique(Moderateur):
    def __init__(self, player, room):
        Moderateur.__init__(self, player, room)
        self.ban = False

    def action(self, phase):
        Moderateur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.ban = False
            req = "S2:Bannir:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer) and not isrole(player.role, Moderateur) and (not isrole(player.role, Fantome) or  player.role.speak):
                    req+=":"+player.pseudo
                    self.forumeurs.append(player)
            self.player.send("R",req)

    def on_request(self, request, phase):
        Moderateur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and not self.ban:
            n=int(request)
            if n!=-1:
                self.room.send_to_all_players("A",self.player.pseudo + " a décidé d'abuser de ces pouvoirs de modérateur afin de bannir " + self.forumeurs[n].pseudo + " qui était " + self.forumeurs[n].role.name() + "!")
                self.forumeurs[n].role.on_death(phase, self.room.turn)
                self.ban = True

    def name(self):
        return "Moderateur Tyranique"

    def description(self):
        return "Vous êtes un Moderateur Tyrannique, chaque nuit, aprés le conseil vous pouvez bannir un forumeur supplémentaire cependant votre pseudo sera révélé !"

    def value(self):
        return 50

class Kickeur(Moderateur):
    def __init__(self, player, room):
        Moderateur.__init__(self, player, room)
        self.kick = None

    def action(self, phase):
        Moderateur.action(self, phase)
        if phase == APRES_CONSEIL:
            req = "S2:Kicker:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer) and not isrole(player.role, Moderateur):
                    req+=":"+player.pseudo
                    self.forumeurs.append(player)
            self.player.send("R",req)
        if phase == CONSEIL and self.kick != None:
            self.kick.role.can_speak = True
            self.kick = None

    def on_request(self, request, phase):
        Moderateur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and self.kick == None:
            n=int(request)
            if n!=-1:
                self.kick = self.forumeurs[n]
                self.player.send("A","Vous avez kické "+self.kick.pseudo)
                self.kick.send("A","Vous avez été kické, vous ne pouvez pas parler durant ce tour.")
                self.kick.role.can_speak = False

    def name(self):
        return "Kickeur abusif"

    def description(self):
        return "Vous êtes un kickeur abusif, chaque nuit, aprés le conseil vous pouvez kickez un forumeur, celui-ci ne pourra pas parler durant la journée."

    def value(self):
        return 55

class SuceBoule(AlivePlayer):
    def __init__(self, player, room):
        AlivePlayer.__init__(self, player, room)

    def action(self, phase):
        AlivePlayer.action(self, phase)
        if phase == BEGIN:
            ch = "Les moderateurs sont "
            for player in self.room.players:
                if isrole(player.role, Moderateur):
                    ch += player.pseudo + "   "
            self.player.send("A", ch)

    def win(self):
        for player in self.room.players:
            if isrole(player.role, Forumeur) and not isrole(player.role, SummerFag):
                return False
        self.room.send_to_all_players("G", "<h2>Les Modérateurs ont gagné !</h2>")
        for player in self.room.players:
            if (isrole(player.role, Moderateur) or isrole(player.role, SuceBoule)) or (isrole(player.role, Dead) and (isrole(player.role.role, Moderateur) or isrole(player.role.role, SuceBoule))):
                player.role.victory = True
        return True

    def name(self):
        return "Suce Boule"

    def description(self):
        return "Vous êtres un suce boule des moderateurs, votre but est de gagner avec eux. Vous êtes considéré comme simple forumeur au yeux du stalker et du kikoo-jap."

    def value(self):
        return 17


#########################################
#                                       #
#                                       #
#               AUTRES                  #
#                                       #
#                                       #
#########################################



class Troll(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.trolol = False

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == BEGIN:
            for player in self.room.players:
                if isrole(player.role, Pigeon):
                    player.send("A","Le troll est " + self.player.pseudo)
                    break

    def win(self):
        if self.trolol:
            self.victory = True
            for player in self.room.players:
                if isrole(player.role, Pigeon):
                    player.role.victory = True
                    break
        return self.trolol or Forumeur.win(self)

    def on_death(self, phase, turn):
        if turn == 1 and phase == DEBAT:
            self.room.send_to_all_players("G", "<h2>Le Troll a gagné !</h2>")
            self.trolol = True
        else:
            Forumeur.on_death(self, phase, turn)

    def name(self):
        return "Troll"

    def description(self):
        return "Vous êtes Troll, pour gagner vous devez vous faire éliminer au premier tour. Si vous n'y arrivez pas, vous devenez un simple forumeur."

    def value(self):
        return 8

    def victoryChance(self, fvalue, mvalue):
        Forumeur.victoryChance(self, fvalue, mvalue)
        self.vco = 1.0/len(self.room.players)
        for player in self.room.players:
            if isrole(player.role, Pigeon):
                self.vco *= 3

class Pigeon(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def name(self):
        return "Pigeon"

    def description(self):
        return "Vous êtes un pigeon, pour gagner, vous devez faire éliminer le troll au premier tour. Si vous n'y arrivez pas, vous devener un simple forumeur."

    def value(self):
        return 8

    def victoryChance(self, fvalue, mvalue):
        Forumeur.victoryChance(self, fvalue, mvalue)
        self.vco = 3.0/len(self.room.players)


class AW(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.charm = []
        self.player_to_charm = []
        self.nb_charme = 0

    def action(self, phase):
        Forumeur.action(self, phase)
        self.charm[:] = [player for player in self.charm if isrole(player.role, AlivePlayer)]
        if phase == DEBAT:
            mess = "Les joueurs charmé sont "
            for player in self.charm:
                mess += player.pseudo + ", "
            mess = mess[:-2]+"!"
            for player in self.charm:
                player.send("A", mess)
            self.player.send("A", mess)
        elif phase == CONSEIL:
            self.nb_charme = 0
            self.player_to_charm = [player for player in self.room.players if player != self.player and  player.role.name() != "Dead" and player not in self.charm]
            req = "S2:Charmer:personne"
            for player in self.player_to_charm:
                req += ":"+player.pseudo
            self.player.send("R",req)
        elif phase == BEGIN:
            for player in self.room.players:
                if isrole(player.role, WhiteKnight):
                    player.send("A","L'AW qui a besoin de votre aide est " + self.player.pseudo)
                    break

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == CONSEIL and self.nb_charme<2:
            nb = int(request)
            self.nb_charme += 1
            if nb != -1:
                pl = self.player_to_charm.pop(nb)
                if(isrole(pl.role, Alpha)):
                    self.player.send("A",pl.pseudo + " est un forumeur alpha, vous n'arrivez pas à le charmer.")
                    self.nb_charme -= 1
                    return
                self.charm.append(pl)
                self.player.send("A","Vous avez charmé " + pl.pseudo + " !")
                pl.send("A","Vous avez été charmé par l'AW !")
            if self.nb_charme < 2:
                req = "S2:Charmer:personne"
                for player in self.player_to_charm:
                    req += ":"+player.pseudo
                self.player.send("R", req)

    def win(self):
        for player in self.room.players:
            if player != self.player and isrole(player.role, AlivePlayer) and player not in self.charm:
                return False
        self.victory = True
        for player in self.room.players:
            if isrole(player.role, WhiteKnight) or isrole(player.role, Dead) and isrole(player.role.role, WhiteKnight):
                player.role.victory = True
        self.room.send_to_all_players("G","<h2>L'AW a gagné ! </h2>")
        return True

    def name(self):
        return "AW"

    def description(self):
        return "Vous êtes une AW, votre but est d'enchanter tout les autres joueurs et de rester en vie."

    def victoryChance(self, fvalue, mvalue):
        Forumeur.victoryChance(self, fvalue, mvalue)
        self.vco = 0.95**len(self.room.players)
        for player in self.room.players:
            if isrole(player.role, WhiteKnight):
                self.vco += 0.1
            elif isrole(player.role, Alpha):
                self.vco -= 0.1

class WhiteKnight(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)

    def win(self):
        for player in self.room.players:
            if player != self.player and (isrole(player.role, AlivePlayer) and not isrole(player.role, SummerFag)):
                return False
        self.room.send_to_all_players("G","<h2>Le White Knight a gagné ! </h2>")
        self.victory = True
        return True

    def name(self):
        return "White Knight"

    def description(self):
        return "Vous êtes un White Knight, votre but est de gagner avec l'AW. Protegez la."

    def value(self):
        return 2

class SummerFag(AlivePlayer):
    def __init__(self, player, room):
        AlivePlayer.__init__(self, player, room)
        self.victory = True
        self.live = True

    def win(self):
        for player in self.room.players:
            if player != self.player and isrole(player.role, AlivePlayer):
                return False
        self.room.send_to_all_players("G","<h2>Le Summer fag a gagné !</h2>")
        return True

    def name(self):
        return "Summer Fag"

    def description(self):
        return "Vous êtes un Summer Fag, votre but est de rester vivant jusqu'à la fin de la partie."

    def victoryChance(self, fvalue, mvalue):
        self.vc = 0.95**len(self.room.players)


class ChefPetitBras(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.turn = 0
        self.rplayers = []

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            self.turn -= 1
            if self.turn <= 0:
                req = "S2:Recruter:personne"
                self.rplayers = [player for player in self.room.players if isrole(player.role, AlivePlayer) and not isrole(player.role, PetitBras)]
                for player in self.rplayers:
                    req += ":"+player.pseudo
                self.player.send("R", req)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and self.turn <= 0:
            n = int(request)
            if n != -1:
                pl = self.rplayers[n]
                if(isrole(pl.role, Alpha)):
                    self.player.send("A", pl.pseudo + " est un forumeur alpha, votre propagande ne l'interesse pas !")
                    return
                self.player.send("A", pl.pseudo + " qui est " + pl.role.name() + " a rejoint votre cause.")
                pl.role = PetitBras(pl, self.room, pl.role)
                self.turn = 2

    def win(self):
        pass

    def name(self):
        return ""

    def description(self):
        return "Vous êtes un petit bras. Tout les 2 tours, vous pourrez convertir un joueur à votre faction. Celui-ci garde ses pouvoirs et devra gagner avec vous. Si tout les joueurs vivants sont converti, vous avez gagné !"

class PetitBras(AlivePlayer):
    def __init__(self, player, room, role = None):
        if role == None:
            self.role = ChefPetitBras(player, room)
        else:
            self.role = role
            player.send("A","Vous êtes devenu un petit bras, votre but est maintenant de gagner avec eux !")
        AlivePlayer.__init__(self, player, room)

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if name not in ["role","player","room"]:
            self.role.__dict__[name] = value

    def __getattr__(self, name):
        if name in ["role","player","room"]:
            return self.__dict__[name]
        return self.role.__dict__[name]
        

    def on_message(self, phase, message):
        self.role.on_message(phase, message)
        if phase == CONSEIL:
            self.room.send_to_players(15, "<b>"+self.player.pseudo + "</b> : " + message, lambda pl: isrole(pl.role, PetitBras))

    def action(self, phase):
        self.role.action(phase)

    def on_request(self, request, phase):
        self.role.on_request(request, phase)

    def on_death(self, phase, turn):
        self.role.on_death(phase, turn)
        if isrole(self.role, Dead):
            AlivePlayer.on_death(self, phase, turn)

    def win(self):
        pwin = True
        for player in self.room.players:
            if isrole(player.role, AlivePlayer) and not (isrole(player.role, PetitBras) or isrole(player.role, SummerFag)):
                pwin = False
                break
        if pwin:
            self.room.send_to_all_players("G","<h2> Les petits bras ont gagnés ! </h2>")
            for player in self.room.players:
                if isrole(player.role, PetitBras) or (isrole(player.role, Dead) and isrole(player.role.role, PetitBras)):
                    player.role.victory = True
            return True
        if self.role.win():
            return True

    def name(self):
        return "Petit Bras "+self.role.name()

    def description(self):
        return self.role.description()

    def victoryChance(self, fvalue, mvalue):
        self.vco = 0.95**len(self.room.players)




class Complotiste(Forumeur):
    def __init__(self, player, room):
        Forumeur.__init__(self, player, room)
        self.choice = None
        self.elim = False

    def action(self, phase):
        Forumeur.action(self, phase)
        if phase == APRES_CONSEIL:
            req = "S2:Choisir:personne"
            self.rplayers = [player for player in self.room.players if isrole(player.role, AlivePlayer) and player != self.player]
            for player in self.rplayers:
                req += ":"+player.pseudo
            self.player.send("R", req)
        elif phase == DEBAT:
            if self.choice != None:
                if isrole(self.choice.role, Dead):
                    self.player.send("A","Votre choix a été annulé !")
                    self.choice = None
                else:
                    self.room.send_to_all_players("A","Le complotiste a vu un reptilien ! Ne l'eliminez pas !")
        elif phase == CONSEIL:
            if self.choice != None:
                if isrole(self.choice.role, Dead):
                    self.elim = True
                    self.room.send_to_all_players("A","Le reptilien a été éliminé !")
                else:
                    self.room.send_to_all_players("A",self.player.pseudo + " qui était le complotiste a été retrouvé suicidé de trois balles dans le dos !")
                    self.on_death(phase, self.room.turn)

    def on_request(self, request, phase):
        Forumeur.on_request(self, request, phase)
        if phase == APRES_CONSEIL and self.choice == None:
            print(request)
            try:
                n = int(request)
                if n != -1:
                    self.choice = self.rplayers[n]
                    print self.choice.pseudo
                    self.player.send("A","Vous devez eliminez "+self.choice.pseudo+ " ce tour ci !")
            except:
                print "erreur complotiste"

    def win(self):
        if self.elim or len([pl for pl in self.room.players if isrole(pl.role, AlivePlayer) and not isrole(pl.role, SummerFag)]) == 1:
            self.room.send_to_all_players("G", "<h2> Le complotiste a gagné ! </h2>")
            self.victory = True
            return True
        return False

    def name(self):
        return "Complotiste"

    def description(self):
        return "Vous êtes complotiste. Durant la partie vous allez pouvoir choisir une personne, votre but sera alors de la faire eliminer. Si vous y parvenez, vous gagnez sinon vous vous suicidez !"

    def victoryChance(self, fvalue, mvalue):
        self.vco = 0.1


class EnfantDuForum(AlivePlayer):
    def __init__(self, player, room):
        AlivePlayer.__init__(self, player, room)
        self.live = True

    def action(self, phase):
        AlivePlayer.action(self, phase)
        if phase == APRES_CONSEIL:
            req = "S2:Eliminer:personne"
            for player in self.room.players:
                if isrole(player.role, AlivePlayer):
                    req+=":"+player.pseudo
                    self.alive_players.append(player)
            self.player.send("R", req)


    def on_request(self, request, phase):
        AlivePlayer.on_request(self, request, phase)
        if phase == APRES_CONSEIL:
            n = int(request)
            if n!=-1:
                self.room.send_to_all_players("A","L'enfant du forum a décidé d'éliminer " + self.alive_players[n].pseudo + " qui était " + self.alive_players[n].role.name() + " .")
                self.alive_players[n].role.on_death(phase, self.room.turn)

    def win(self):
        if len([pl for pl in self.room.players if (isrole(pl.role, AlivePlayer) and not isrole(pl.role, SummerFag))]) == 1:
            self.room.send_to_all_players("G","<h2> L'enfant du forum a gagné ! </h2>")
            self.victory = True
            return True
        return False

    def name(self):
        return "Enfant du forum"

    def description(self):
        return "Vous êtes l'enfant du forum. Votre but est de gagner seul. Chaque nuit vous pourrez bannir un joueur et vous resisterez à un bannissement des modérateurs."

    def victoryChance(self, fvalue, mvalue):
        self.vco = 0.95**len(self.room.players)
