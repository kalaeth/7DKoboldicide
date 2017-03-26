#!/usr/bin/python
#
# green over black presents
#                                  koboldicide!
#
# with special thanks to Jotaf for his tutorial
 
import libtcodpy as libtcod
import math
import textwrap
import shelve
import random
import os
import shutil
from time import sleep

#actual size of the window
SCREEN_WIDTH = 62
SCREEN_HEIGHT = 30
 
#size of the map
VIEW_WIDTH = 50
VIEW_HEIGHT = 16

#size of the map portion shown on-screen
CAMERA_WIDTH = 50
CAMERA_HEIGHT = 22
MAP_WIDTH = 100
MAP_HEIGHT = 80
DEPTH = 10
MIN_SIZE = 15
FULL_ROOMS = False
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 10
PANEL_HEIGHT = 6
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = 1
MSG_WIDTH = SCREEN_WIDTH  - 2
MSG_HEIGHT = PANEL_HEIGHT - 2
INVENTORY_WIDTH = 50
CHARACTER_SCREEN_WIDTH = 30
LEVEL_SCREEN_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 20
ROOM_MIN_SIZE = 10
MAX_ROOMS = 12
 
#compass
NORTH = '^'
SOUTH = 'v'
EAST = '>'
WEST = '<'


#health       0     1          2        3       4      5      6
HEALTH = ['dead','crippled','injured','weak','so-so','ok','good','great']
#health                        0                  1          2        3              4               5                 6
HEALTH_COLOR = [libtcod.darker_red, libtcod.dark_red, libtcod.red, libtcod.orange, libtcod.lime,libtcod.chartreuse, libtcod.green, libtcod.white]
#experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

#combat speeds
PLAYER_SPEED = 1
DEFAULT_SPEED = 1
DEFAULT_ATTACK_SPEED = 1
 
FOV_ALGO = 1  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 35
 
LIMIT_FPS = 20  #20 frames-per-second maximum
 
 
color_dark_wall = libtcod.Color(100, 100, 100)
color_light_wall = libtcod.Color(50, 50, 50)
color_dark_ground = libtcod.Color(150, 150, 150)
color_light_ground = libtcod.Color(190, 190, 190)
color_aim_unblocked = libtcod.Color(255,255,0)
color_aim_blocked = libtcod.Color(255,128,0)


#WORLDMAP
CHAR_LONG_GRASS = '`'
CHAR_TALL_GRASS = '"'
CHAR_GRASS = ','
CHAR_DIRT = '.'
CHAR_ROAD = '_'
CHAR_FOREST = 'T'
CHAR_LAKE = '~'
CHAR_ICE = ':'
CHAR_MOUNTAIN = '#'
CHAR_STAIRS = '<'
CHAR_DOOR = ']'
CHAR_SAND = 'S'

class Dungeon:
    def __init__(self,name,x,y):
        self.name = name
        self.x = x
        self.y = y

def get_dungeon_name(x,y):
    global dung_list

    for d in dung_list:
        if d.x == x and d.y == y:
            return d.name
    return 'no where'


class Dialog:
    def __init__(self,_char,_state,_value):
        self.character = _char
        self.state = _state
        self.value = _value

    def _set_value(self, _value):
        self.value = _value

    def _get_value(self):
        return self.value

class Dialogs:
    def __init__(self):
        self.list = [];

    def get(self,_char, _state):
        rt_sentence = Dialog('X','neutral','*grumpf*')
        for sentence in self.list:
            if sentence.character == _char and sentence.state == _state:
                return sentence
        return rt_sentence

    def getValue(self,_char, _state):
        return self.get(_char,_state)._get_value()

    def loadFromFile(self):
        _dialogs_ = []
        with open('story.dlg','r') as file_dialogs:
            for line in file_dialogs:
                if line.split(':')[0] != '#':
                    if line.split(':')[0] != 'END':
                        _dialogs_.append(line)
                    else:
                        break

        for _d in _dialogs_:
                dd = _d.split(':')
                if dd[0] == 'END':
                    break
                else:
                    #print dd[0] +':'+ dd[1] +':'+ dd[2]
                    self.list.append(Dialog(dd[0],dd[1],dd[2]));
 
class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None, terrain=CHAR_GRASS):
        self.blocked = blocked
 
        #all tiles start unexplored
        self.explored = False
    
        #by default, if a tile is blocked, it also blocks sight

        self.terrain = terrain
        if self.terrain in [CHAR_LAKE,CHAR_FOREST,CHAR_MOUNTAIN,CHAR_ICE]:
            self.blocked = True
            if self.terrain in [CHAR_FOREST, CHAR_MOUNTAIN]:
                self.block_sight = True
            else:
               self.block_sight = False
        elif self.terrain in [CHAR_DIRT, CHAR_GRASS, CHAR_ROAD , CHAR_LONG_GRASS, CHAR_STAIRS, CHAR_SAND]:
            self.blocked = False
            self.block_sight = False
        elif self.terrain in [CHAR_TALL_GRASS,CHAR_DOOR]:
            self.blocked = False
            self.block_sight = True
        else:
            if block_sight is None: block_sight = blocked
            self.block_sight = block_sight

        self.color = libtcod.green
        if self.terrain == CHAR_MOUNTAIN or self.terrain == CHAR_DIRT:
            self.color = libtcod.light_sepia
        elif self.terrain == CHAR_ICE:
            self.color = libtcod.light_cyan
        elif self.terrain == CHAR_LAKE:
            self.color = libtcod.blue
            self.block_sight = False
        elif self.terrain in [CHAR_STAIRS, CHAR_SAND]:
            self.color = libtcod.light_yellow
        elif self.terrain == CHAR_TALL_GRASS:
            self.color = libtcod.darker_green
        elif self.terrain in [CHAR_LONG_GRASS,CHAR_FOREST]:
            self.color = libtcod.dark_green
        elif self.terrain == CHAR_GRASS:
            self.color = libtcod.green
        elif self.terrain in ['-','_','|','[',']']:
            self.color = libtcod.dark_sepia
        elif self.terrain in ['X']:
            self.color = libtcod.light_flame

    def _toString(self):
        return '{},{}'.format(self.terrain, self.color)

class Notif:
    #Notifation(x,y,time_to_live)
    def __init__(self,message,time_to_live = 50, x = 20, y = 10, color=libtcod.light_yellow):
        self.x = x
        self.message = message
        self.color= color
        self.y = y
        self.time_to_live = time_to_live

    def _tick(self,con):
        self.time_to_live -= 1
        self.draw(con)
        if self.time_to_live == 0:
            self.wipe(con)
            return 'done'
        return 'ticked'

    def draw(self,con):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            (x, y) = to_camera_coordinates(self.x, self.y)
            if x is not None:
                #set the color and then draw the character that represents this object at its position
                libtcod.console_set_default_foreground(con, self.color)
                libtcod.console_set_default_background(con, libtcod.black)
                libtcod.console_print_ex(con, x, y, libtcod.BKGND_SET,  libtcod.LEFT,self.message)

    def wipe(self,con):
        #erase the character that represents this object
        (x, y) = to_camera_coordinates(self.x, self.y)
        if x is not None:
            if len(self.message) > 1:
                xoff = self.x
                for _x in range(x, x+len(self.message)):
                    if xoff >= MAP_WIDTH:
                       break
                    t = map[xoff][self.y].terrain
                    c = map[xoff][self.y].color
                    libtcod.console_set_default_foreground(con, c)
                
                    libtcod.console_put_char(con, _x, y, t, libtcod.BKGND_NONE)
                    xoff+=1
                render_all()
            else:
                t = map[self.x][self.y].terrain
                c = map[self.x][self.y].color
                libtcod.console_set_default_foreground(con, c)
                libtcod.console_put_char(con, x, y, t, libtcod.BKGND_NONE)

class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
 
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)
 
    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)
 
class Object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None,speed=DEFAULT_SPEED):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.speed = speed
        self.wait = 0
        self.always_visible = always_visible
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self

        self.equipment = equipment
        if self.equipment:  #let the Equipment component know who owns it
            self.equipment.owner = self

            #there must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        #move by the given amount, if the destination is not blocked
        if self.x + dx > MAP_WIDTH:
            dx = 0
        if self.y + dy > MAP_HEIGHT:
            dy = 0 

        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            self.wait = self.speed
        elif not is_blocked(self.x + dx, self.y):
            self.x += dx
            self.wait = self.speed
        elif not is_blocked(self.x, self.y +dy):
            self.y += dy
            self.wait = self.speed
    
    def move_astar(self, target):
        #Create a FOV map that has the dimensions of the map
        fov = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
 
        #Scan the current map each turn and set all the walls as unwalkable
        for y1 in range(MAP_HEIGHT):
            for x1 in range(MAP_WIDTH):
                libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)
 
        #Scan all the objects to see if there are objects that must be navigated around
        #Check also that the object isn't self or the target (so that the start and the end points are free)
        #The AI class handles the situation if self is next to the target so it will not use this A* function anyway   
        for obj in objects:
            if obj.blocks and obj != self and obj != target:
                #Set the tile as a wall so it must be navigated around
                libtcod.map_set_properties(fov, obj.x, obj.y, True, False)
 
        #Allocate a A* path
        #The 1.41 is the normal diagonal cost of moving, it can be set as 0.0 if diagonal moves are prohibited
        my_path = libtcod.path_new_using_map(fov, 1.41)
 
        #Compute the path between self's coordinates and the target's coordinates
        libtcod.path_compute(my_path, self.x, self.y, target.x, target.y)
 
        #Check if the path exists, and in this case, also the path is shorter than 25 tiles
        #The path size matters if you want the monster to use alternative longer paths (for example through other rooms) if for example the player is in a corridor
        #It makes sense to keep path size relatively low to keep the monsters from running around the map if there's an alternative path really far away        
        if not libtcod.path_is_empty(my_path) and libtcod.path_size(my_path) < 25:
            #Find the next coordinates in the computed full path
            x, y = libtcod.path_walk(my_path, True)
            if x or y:
                #Set self's coordinates to the next path tile
                self.x = x
                self.y = y
        else:
            #Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
            #it will still try to move towards the player (closer to the corridor opening)
            self.move_towards(target.x, target.y)  
 
        #Delete the path to free memory
        libtcod.path_delete(my_path)

    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        if dx != 0 or dy != 0:
            if dx > 1:
                dx = 1
            elif dx < -1:
                dx = -1
            if dy > 1:
                dy = 1
            elif dy < -1:
                dy = -1
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        #dx = int(round(dx / distance))
        #dy = int(round(dy / distance))
        self.move(dx, dy)
 
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)
 
    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
 
    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global objects
        objects.remove(self)
        objects.insert(0, self)
 
    def draw(self):
        #only show if it's visible to the player
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            (x, y) = to_camera_coordinates(self.x, self.y)
 
            if x is not None:
                #set the color and then draw the character that represents this object at its position
                if self.fighter:
                    _color_ = self.fighter.color
                else:
                    _color_ = self.color
                libtcod.console_set_default_foreground(con, _color_)
                libtcod.console_put_char(con, x, y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        (x, y) = to_camera_coordinates(self.x, self.y)
        if x is not None:
            t = map[self.x][self.y].terrain
            c = map[self.x][self.y].color
            libtcod.console_set_default_foreground(con, c)
            libtcod.console_put_char(con, x, y, t, libtcod.BKGND_NONE)

class Skill:
    def __init__(self,name,power=0,precedence=None):
        self.name = name
        self.power = power
        self.precedence = precedence

    def toString(self):
        st = ' {} '.format(self.name)
        if not self.precedence is None:
            st += self.precedence.toString()
            st += ' -> '
        #st += self.name
        return st

class PlayerFighter:
    #combat-related properties and methods (player).
    def __init__(self, hp, defense, power, xp, death_function=None,attack_speed=DEFAULT_ATTACK_SPEED,generation=3):
        self.base_max_hp = 5
        self.hp = hp
        if hp < 7:
            self.color = HEALTH_COLOR[hp]
        else:
            self.color = libtcod.white
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        
        self.attack_speed = attack_speed
        
        self.orientation = SOUTH
        self.purse = random.randint(25,35)
        
        #skl = random.randint(0,6)
        #if skl < 3:
        #s = Skill('sword',1)
        #else:
        #s = Skill('spear',1)
        

        self.skills = []
        #kl = random.randint(0,6)
        #elf.skills.append(s)
        #if skl > 3:
        #s2 = Skill('long',2,s)
        #self.skills.append(s2)

 
    @property
    def power(self):  #return actual power, by summing up the bonuses from all equipped items
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        
        return self.base_power + bonus
 
    @property
    def defense(self):  #return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus
 
    @property
    def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    def getTargetTile(self):
        if self.orientation == NORTH:
            return player.x, player.y -1
        elif self.orientation == SOUTH:
            return player.x, player.y +1
        elif self.orientation == EAST:
            return player.x + 1, player.y
        elif self.orientation == WEST:
            return player.x - 1, player.y

    def attack(self, target):
        #a simple formula for attack damage
        #roll power d10
        rolls = [random.randint(1,10)]
        hits = 0
        for i in range(0,self.power):
            rolls.append(random.randint(1,10))
        roll_history = ""
        for roll in rolls:
            roll_history += '[{}] '.format(roll)
            if roll == 10:
                hits+=2
            elif roll > target.fighter.defense:
                hits+=1
            elif roll == 1:
                hits-=1
        if hits < 0:
            hits = 0
        #message()
        damage = hits
        self.owner.wait = self.attack_speed
        if damage > 0:
            #make the target take some damage
            message(self.owner.name + ' hits ' + target.name + ' with ' + str(damage) + ' dmg. ' + "{}".format(roll_history))
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name + ' misses ' + target.name+ ". " + "{}".format(roll_history))
  
    def take_damage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
            if self.hp < 0:
                self.hp = 0
            elif self.hp < 7:
                self.color = HEALTH_COLOR[self.hp]
            else:
                self.color = libtcod.white

            
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
 
                if self.owner != player:  #yield experience to the player
                    player.fighter.xp += self.xp
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > 7:
            self.color = libtcod.white
        else:
            self.color = HEALTH_COLOR[self.hp]
        if self.hp > self.max_hp:
            self.hp = self.max_hp
                    
# AI 

class Body():
    def __init__(self, head):
        self.head = head
    
    def take_turn(self):
        global objects
        monster = self.owner
        for obj in objects:
            if obj.name == self.head.name:
                self.head = obj
                break;

        _dist = int(monster.distance_to(self.head))
        if _dist > 1:
            __x = 0
            __y = 0
            if self.head.x > self.owner.x:
                __x += 1
            elif self.head.x < self.owner.x:
                __x -= 1

            if self.head.y > self.owner.y:
                __y += 1
            elif self.head.y < self.owner.y:
                __y -= 1

            self.owner.move(__x, __y)

class DeadBody:
    global objects
    def __init__(self,monster,turns=20):
        self.monster = monster
        self.turns = turns

    def take_turn(self):
        if self.turns > 0:
            self.turns -= 1
        else:
            objects.remove(self.monster)

class ShaiHulud:
    def __init__(self):
        self.turn = 0
        self.previous = self

    def take_turn(self):
        global objects
        print 'taking turn {}'.format(self.turn)
        monster = self.owner
        self.turn += 1
        if self.turn == 2:
            ai_component = Body(monster)
            fighter_component = Fighter(hp=6, defense=10, power=0, xp=5, death_function=monster_death)
            monster_body = Object(monster.x,monster.y-1, 'o', 'shai-hulud body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster_body)
            self.previous = monster_body
        elif self.turn == 3:
            fighter_component = Fighter(hp=6, defense=7, power=0, xp=5, death_function=monster_death)
            ai_component = Body(self.previous)
            monster_body = Object(monster.x,monster.y-2, 'o', 'shai-hulud body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster_body)
            self.previous = monster_body
        elif self.turn == 4:
            fighter_component = Fighter(hp=6, defense=7, power=0, xp=5, death_function=monster_death)
            ai_component = Body(self.previous)
            monster_body = Object(monster.x,monster.y-3, 'o', 'shai-hulud body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster_body)
            self.previous = monster_body
        elif self.turn == 5:
            fighter_component = Fighter(hp=6, defense=5, power=2, xp=5, death_function=monster_death)
            ai_component = Body(self.previous)
            monster_tail = Object(monster.x,monster.y-4, 'o', 'shai-hulud tail', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
            objects.append(monster_tail)
            self.previous = monster_tail
        elif self.turn >= 5:
            _dist = int(monster.distance_to(player))
            if _dist < 20:
                notifications.append(Notif('*',4,monster.x-1,monster.y-1))
                if _dist > 10:
                    notifications.append(Notif('?',4,monster.x-1,monster.y-1))
                    self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
                    if player.x != monster.x and player.y != monster.y:
                        monster.fighter.state = 'watchfull'
                elif _dist > 1:
                    notifications.append(Notif('!',4,monster.x-1,monster.y-1,libtcod.red))
                    monster.move_towards(player.x, player.y)
                #close enough, attack! (if the player is still alive.)
                else:
                    notifications.append(Notif('x',4,monster.x-1,monster.y-1,libtcod.light_red))
                    monster.fighter.attack(player)

        else:
            monster.move_towards(player.x, player.y)

class BasicMonster:
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        state = monster.fighter.state
        _dist = int(monster.distance_to(player))
        if state in ['aggressive']:
            ai = "{}@[{},{}]?".format(monster.name, monster.x, monster.y)

            #if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if _dist < 20:
                ai+=", I see you!"
                notifications.append(Notif('*',4,monster.x,monster.y-1))
                
                #move towards player if far away
                ai+=", _dist[{}]".format(_dist)
                if _dist > 10:
                    ai+=", ?"
                    notifications.append(Notif('?',4,monster.x,monster.y-1))
                    self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
                    if player.x != monster.x and player.y != monster.y:
                        monster.fighter.state = 'watchfull'
                elif _dist > 1:
                    ai+=", !"
                    notifications.append(Notif('!',4,monster.x,monster.y-1,libtcod.red))
                    monster.move_towards(player.x, player.y)
                #close enough, attack! (if the player is still alive.)
                else:
                    ai+=", X"
                    notifications.append(Notif('x',4,monster.x,monster.y-1,libtcod.light_red))
                    monster.fighter.attack(player)
        elif state in ['watchfull']:
            if _dist <= 5:
                notifications.append(Notif('!',4,monster.x,monster.y-1,libtcod.red))
                monster.move_towards(player.x, player.y)
                monster.fighter.state = 'aggressive'
        elif state in ['neutral']:
            if _dist <= 1:
                monster.fighter.talk('watch it..',color=libtcod.dark_yellow)
                monster.fighter.state = 'aggressive'
        elif state in ['friendly']:
            _dist = int(monster.distance_to(player))
            if _dist <= 1:
                monster.fighter.talk('hey friend!',color=libtcod.green)
        else:
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
        #print ai

class Squad:
    def __init__(self, leader):
        self.leader = leader
        self.followers = []

    def addFollower(follower):
        self.followers.append(follower)

class SquadMonster:
    def __init__(self,squad):
        self.squad = squad

    #AI for a basic monster.
    def take_turn(self):
        monster = self.owner
        state = monster.fighter.state
        _dist_lead = int(monster.distance_to(self.leader))
        _dist_play = int(monster.distance_to(player))

        if state in ['aggressive']:
            ai = "{}@[{},{}]?".format(monster.name, monster.x, monster.y)
            if _dist_player > 5:
                if _dist_lead > 2:
                    _lead = self.squad.leader.owner
                    monster.move_towards(_lead.x, _lead.y)
                else:
                    notifications.append(Notif('..',4,monster.x,monster.y-1))
            else:
                if _dist_player > 1:
                    ai+=", !"
                    notifications.append(Notif('!',4,monster.x,monster.y-1,libtcod.red))
                    monster.move_towards(player.x, player.y)
                #close enough, attack! (if the player is still alive.)
                else:
                    ai+=", X"
                    notifications.append(Notif('x',4,monster.x,monster.y-1,libtcod.light_red))
                    monster.fighter.attack(player)
        else:
            if _dist_lead > 2:
                _lead = self.squad.leader.owner
                monster.move_towards(_lead.x, _lead.y)
            else:
                notifications.append(Notif('..',4,monster.x,monster.y-1))
class Shopowner:
        
    #AI for a basic monster.
    def take_turn(self):
        #a shopkeper takes its turn.
        monster = self.owner
        state = monster.fighter.state

        _dist = int(monster.distance_to(player))
        #if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
        if _dist < 20:
            if state in ['aggressive']:
                notifications.append(Notif('*',4,monster.x,monster.y-1))
                if _dist <=1:
                     monster.fighter.attack(player)
                elif _dist > 1:
                    notifications.append(Notif('!',4,monster.x,monster.y-1,libtcod.red))
                    monster.move_towards(player.x, player.y)
            elif state in ['neutral','friendly']:
                profession = monster.name.split()[0]
                if profession in ['lumberjack']:
                    slogan = random.choice(['i sell axes','imma lumbjak','nd i\'m ok'])
                elif profession in ['blacksmith']:
                    slogan = random.choice(['get metal','metal suits!'])
                elif profession in ['leathersmith']:
                    slogan = random.choice(['leathers!','all leathers!'])
                elif profession in ['nurse']:
                    slogan = random.choice(['24h health','+'])
                elif profession in ['old','wise']:
                    slogan = random.choice(['ohm','zen','aum'])
                else:
                    slogan = random.choice(['...','..','.', ])

                monster.fighter.talk(slogan,color=libtcod.white)
        else:
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
        #print ai

    def sell_stuff(self):
        global player, lair_name
        inv = []
        shpowner = self.owner
        if shpowner.name.split()[0] in ['lumberjack']:
            #inv.append(addItem('work axe',-1,-1,False))
            opt = arrow_menu('wanna buy my axe? 20$',['yes I would!','no thanks,got one already'],35,10,4,2)
            if opt == 0:
                if player.fighter.purse >= 20:
                    player.fighter.purse -= 20
                    addItem('work axe',shpowner.x+1,shpowner.y)
                    #inventory.append(inv[0])
                    shpowner.fighter.talk(random.choice(['glad to be of service!','come back anytime!','there you go','the things i do for money...']))
                else:
                    shpowner.fighter.talk(random.choice(['no can do.','bring money next time!']))
        elif shpowner.name.split()[0] in ['blacksmith']:
            opt = arrow_menu('wanna be more metal??',['short sword - 20$','long sword - 30$','metal armour - 40$','no thanks,got one already'],35,10,4,2)
            if opt == 3:
                shpowner.fighter.talk(random.choice(['oh.. ok...','bye then']))
            elif opt in [0,1,2]:
                if opt == 0:
                    price = 20
                    #inv.append(addItem('short sword',-1,-1,False))
                    it = 'short sword'
                elif opt == 1:
                    #inv.append(addItem('long sword',-1,-1,False))
                    it = 'long sword'
                    price = 30
                elif opt == 2:
                    price = 40
                    #inv.append(addItem('metal armour',-1,-1,False))
                    it = 'metal armour'
                if player.fighter.purse >= price:
                    player.fighter.purse -= price
                    #inventory.append(inv[0])
                    addItem(it,shpowner.x+1,shpowner.y)
                    shpowner.fighter.talk(random.choice(['glad to be of service!','come back anytime!','there you go','the things i do for money...']))
                else:
                    shpowner.fighter.talk(random.choice(['no money, no armor','do i look like charity?']))      
        elif shpowner.name.split()[0] in ['leathersmith']:
            opt = arrow_menu('wanna buy leather stuff?',['leather hat - 5$','leather armour - 10$','no thanks,got one already'],25,10,4,2)
            if opt == 2:
                shpowner.fighter.talk(random.choice(['oh.. ok...','bye then']))
            elif opt in [0,1]:
                if opt == 0:
                    price = 5
                    #inv.append(addItem('leather hat',-1,-1,False))
                    it = 'leather hat'
                elif opt == 1:
                    price = 10
                    #inv.append(addItem('leather armour',-1,-1,False))
                    it = 'leather armour'
                if player.fighter.purse >= price:
                    player.fighter.purse -= price
                    #inventory.append(inv[0])
                    addItem(it,shpowner.x+1,shpowner.y)
                    shpowner.fighter.talk(random.choice(['glad to be of service!','come back anytime!','there you go','the things i do for money...']))
                else:
                    shpowner.fighter.talk(random.choice(['no money, no armor','do i look like charity?']))      
        elif shpowner.name.split()[0] in ['nurse']:
            opt = arrow_menu('{} asks if you wish to heal for $5'.format(shpowner.name),[random.choice(['yes, please!','here you go','do take visa?']),random.choice(['i\'ll pass, thanks','sorry, mom won\'t let me','let me come back to it later...'])],35,10,4,2)
            if opt == 0:
                if player.fighter.purse >= 5:
                    player.fighter.purse -= 5
                    player.fighter.hp = player.fighter.base_max_hp
                    if player.fighter.hp < 7:
                        player.fighter.color = HEALTH_COLOR[player.fighter.hp]
                    else:
                        player.fighter.color = libtcod.white
                    shpowner.fighter.talk(random.choice(['glad to be of service!','come back anytime!','there you go','the things i do for money...']))
                else:
                    shpowner.fighter.talk(random.choice(['i don\'t work for free', 'and how will you pay?','come back with money!']))       
        elif shpowner.name.split()[0] in ['old','wise']:
            if shpowner.name.split()[0] == 'wise':
                opt = 0
                while opt >= 0:
                    opt = arrow_menu('hello young man. i can tell you about :',['the kobolds','their goal','or you can leave me alone'],30)
                    if opt == 0:
                        msgbox('they stink, they are evil and they hurt you. but they are stupid. and each one is very weak.')
                    elif opt == 1:
                        msgbox('their queen, the dragon, has been feeding and will soon come out to kill us all. unless someone can get to the deepest caves in {} and kill her.'.format(lair_name))
                    else:
                        shpowner.fighter.talk('go avenge you family')
                        opt = -1
            else:
               shpowner.fighter.talk('go avenge you family')
            if player.fighter.max_hp < 7:
               player.fighter.base_max_hp += 1
            player.fighter.heal(19)
        elif shpowner.name.split()[0] in ['princess']:
            shpowner.fighter.talk('thank you for saving me!',libtcod.light_pink)
        else:
            shpowner.fighter.talk('can\'t help you, sorry')


class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=5):
        self.old_ai = old_ai
        self.num_turns = num_turns
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
 
        else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)



class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None,attack_speed=DEFAULT_ATTACK_SPEED,state='aggressive'):
        self.base_max_hp = hp
        self.hp = hp
        if self.hp < 7:
            self.color = HEALTH_COLOR[hp]
        else:
            self.color = libtcod.white
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        self.attack_speed = attack_speed
        self.ammo = [100]
        self.purse = 0
        self.state = state
 
    @property
    def power(self):  #return actual power, by summing up the bonuses from all equipped items
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus
 
    @property
    def defense(self):  #return actual defense, by summing up the bonuses from all equipped items
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus
 
    @property
    def max_hp(self):  #return actual max_hp, by summing up the bonuses from all equipped items
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus
 
    def set_state(self, state):
        self.state = state

    def attack(self, target):
        #a simple formula for attack damage
        #roll power d10
        rolls = [random.randint(1,10)]
        hits = 0
        for i in range(0,self.power):
            rolls.append(random.randint(1,10))
        roll_history = ""
        for roll in rolls:
            roll_history += '[{}]'.format(roll)
            if roll == 10:
                hits+=1
            elif roll > target.fighter.defense:
                hits+=1
            elif roll == 1:
                hits-=1

        
        damage = hits
        self.owner.wait = self.attack_speed
        if damage > 0:
            #make the target take some damage
            message(self.owner.name + ' hits ' + target.name + ' with ' + str(damage) + ' dmg. ' + "{}".format(roll_history))
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name + ' misses ' + target.name+ ". " + "{}".format(roll_history))
 
    def take_damage(self, damage):
        global objects
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
            if self.hp > 0:
                if self.hp > 6:
                    _hp = 7
                else:
                    _hp = self.hp
                self.color = HEALTH_COLOR[_hp]
            else:
                self.color = HEALTH_COLOR[0]
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
 
                if self.owner != player:  #yield experience to the player
                    player.fighter.xp += self.xp
        if self.state == 'friendly':
            self.state = 'watchfull'
        elif self.state not in ['friendly','aggressive']:
            print 'i am [{}]'.format(self.owner.name)
            if len(self.owner.name.split()) <= 1:
                return
            for m in objects:

                if len(m.name.split()) <= 1:
                    continue
                if m.name.split()[0] == self.owner.name.split()[0] or m.name.split()[1] == self.owner.name.split()[1]:
                    _dist = int(self.owner.distance_to(m))
                    if _dist < TORCH_RADIUS and m.fighter:
                        m.fighter.set_state('aggressive') 
            self.state = 'aggressive'
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        if self.hp < 7:
            self.color = HEALTH_COLOR[self.hp]
        else:
            self.color = libtcod.white

    def talk(self,text,color=libtcod.yellow):
        if color == libtcod.yellow:
            if self.state == 'friendly':
                color = libtcod.green
            elif self.state in ['neutral', 'watchfull']:
                color = libtcod.white
            elif self.state == 'aggressive':
                color = libtcod.red
        #if self.owner.x +1+ len(text) < MAP_WIDTH:
        x = self.owner.x + 1
        #else:
        #   x = MAP_WIDTH - len(text) - 2

        if self.owner.y >= 1:
            y = self.owner.y -1
        else:
            y = self.owner.y

        notifications.append(Notif(text,5,x,y,color))


 
class Item:
    #an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
 
    def pick_up(self):
        global inventory

        #check if there are available slots:
        slt = get_available_slots()
        opts = 0
        print slt
        pick_up = False
        switch = 'none'


        equipment = self.owner.equipment
        if equipment and equipment.slot in slt:
            equipment.equip()
            pick_up = True
            switch = 'none'
        elif equipment and (equipment.slot.split(' ')[0] == 'right') and (get_equipped_in_slot('left hand') is None):
            equipment.slot = 'left hand'
            equipment.equip()
            pick_up = True
        elif equipment:
            opt_list = ['drop this']
            if equipment.slot not in ['right hand']:
                on_tis_slot = get_equipped_in_slot(equipment.slot)
                opt_list.append('switch with {} on {}'.format(on_tis_slot.owner.name,equipment.slot))
                opts = 1
            c_equip_r = get_equipped_in_slot('right hand')
            if c_equip_r is not None:
                opt_list.append('switch with {} on right hand'.format(c_equip_r.owner.name))
            else:
                opt_list.append('equip on right hand')
            c_equip_l = get_equipped_in_slot('left hand')
            if c_equip_l is not None:
                opt_list.append('switch with {} on left hand'.format(c_equip_l.owner.name))
            else:
                opt_list.append('equip on left hand')
            slos = get_available_slots()
            if 'bag 0' in slos or 'bag 1' in slos or 'bag 2' in slos:
                for i in range(0,get_equipped_by_name('bag').capacity):
                    if 'bag {}'.format(i) in slos:
                        opt_list.append('bag it at {}'.format(i))

                    
            opt = arrow_menu('- {} -'.format(self.owner.name),opt_list,50)
            #print 'opt : {}'.format(opt)
            if opt == 0:
                #print 'DROP TH BEAT!'
                pick_up = False
                switch = 'drop'
            elif opts == 1 and opt == 1:
                #print 'switching!'
                pick_up = True
                switch = equipment.slot
            elif opt == 1+opts:                             
                #print 'equip in R'
                pick_up = True
                if c_equip_r is not None:
                   switch = 'right'
            elif opt == 2+opts:
                #print 'equip in L'
                pick_up = True
                if c_equip_l is not None:
                   switch = 'left'
            else:
                pick_up = True
                switch = 'bag {}'.format(opt_list[opt].split(' ')[3])
                #print 'bag me @[{}] and call me a pretzel'.format(switch)

        if pick_up:
            #add to the player's inventory and remove from the map
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)
            if switch == 'right':
                c_equip_r.owner.item.drop()
                self.use()
            elif switch == 'left':
                c_equip_l.owner.item.drop()
                self.owner.equipment.slot = 'left hand'
                self.use()
            elif switch.split()[0] == 'bag':
                self.owner.equipment.slot = switch
                self.use()
            elif switch != 'none':
                self.use()
        else:
            message('you drop a {} on the floor'.format(self.owner.name))


 
    def drop(self,x=-1,y=-1):
        #special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()

        self.owner.equipment.slot == self.owner.equipment.old_slot
 
        if self.owner.name.split()[1] in ['bag','backpack']:
            for obj in inventory:
                if obj.equipment:
                    print 'droppping stuff! [' + obj.equipment.slot +"]"
                    if obj.equipment.slot in ['bag 0','bag 1','bag 2','backpack']:
                        obj.item.drop()
                        print 'dropped {}'.format(obj.name)




        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        if x == -1:
            self.owner.x = player.x
            self.owner.y = player.y
            message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
        else:
            self.owner.x = x
            self.owner.y = y
            message('You threw a ' + self.owner.name + '.', libtcod.yellow)

        self.owner.send_to_back()


    def use(self):
        #special case: if the object has the Equipment component, the "use" action is to equip/dequip
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return
 
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason
 
class Equipment:
    #an object that can be equipped, yielding bonuses. automatically adds the Item component.
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0,capacity=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
        self.capacity = capacity
        self.old_slot = slot
        self.slot = slot
        self.is_equipped = False
 
    def toggle_equip(self):  #toggle equip/dequip status
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()
 
    def equip(self):
        #if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            if self.slot in ['right hand']:
                self.slot = 'left hand'
                old_equipment = get_equipped_in_slot(self.slot)
                if old_equipment is not None:
                    old_equipment.dequip()
            else:
                old_equipment.dequip()
 
        #equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
 
    def dequip(self):
        #dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        if self.slot.split()[0] in ['bag','left']:
            self.slot = self.old_slot

        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
 
def get_available_slots():
    slots = ['right hand','left hand','head','body','back','neck']
    for obj in inventory:
        if obj.equipment and obj.equipment.is_equipped:
            if obj.name.split()[1] in ['backpack','bag'] or obj.name.split()[0] in ['bag']:
                for i in range(0, obj.equipment.capacity):
                    slots.append('{} {}'.format(obj.name.split()[1],i))
            if obj.equipment.slot in slots:
                slots.remove(obj.equipment.slot)
    return slots

def get_equipped_by_name(name):  #returns the equipment in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.is_equipped and obj.name.split()[1] == 'bag':
            return obj.equipment
    return None


  
def get_equipped_in_slot(slot):  #returns the equipment in a slot, or None if it's empty
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None
 
def get_all_equipped(obj):  #returns a list of equipped items
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return []  #other objects have no equipment
  
def is_blocked(x, y):
    #first test the map tile
    if x >= MAP_WIDTH -1 :
        return True
    if y >= MAP_HEIGHT - 1 :
        return True

    if map[x][y].blocked:
        return True
 
    #now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
 
    return False
 
def isFighter(x,y):
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            return True
    return False

def pointer_1():
    """
        MAP STUFF
    """

def create_room(room):
    global map
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y] = Tile(True,terrain='.')
            #map[x][y].block_sight = False
 
def create_h_tunnel(x1, x2, y):
    global map
    #horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y] = Tile(False,terrain=CHAR_DIRT)
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def create_v_tunnel(y1, y2, x):
    global map
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y] = Tile(False,terrain=CHAR_DIRT)
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def place_thing(thing,_wid=-1,has_stairs=True,sparse=2):
    if _wid == -1:
        _wid = int(MAP_WIDTH / 20)
        x_wid = _wid

    global map, stairs
    _center = Tile(True,terrain=thing)
    startC = _wid +1
    if thing in [CHAR_TALL_GRASS]:
        startC += 2
    if thing in [CHAR_SAND]:
        _startY = MAP_HEIGHT/2
        _endY = _startY + _wid
        _startY -= _wid
        x_wid = _wid
    elif thing in [CHAR_ICE]:
        _startY = 0
        x_wid = 20
        _endY = 1
    else:
        _startY = startC
        x_wid = _wid
        _endY = MAP_HEIGHT-1-_wid
    #print 'mwid[{}]mhei[{}] wid[{}]'.format(MAP_WIDTH,MAP_HEIGHT,_wid)
    _x = random.randint(startC,MAP_WIDTH-1-_wid)
    _y = random.randint(_startY,_endY)
    if sparse > 0:
        acceptable = [CHAR_LONG_GRASS,CHAR_TALL_GRASS,CHAR_GRASS]
    else:
        acceptable = [CHAR_LONG_GRASS,CHAR_GRASS]

    done = False
    while not done:
            _x = random.randint(startC,MAP_WIDTH)
            _y = random.randint(_startY,_endY)
            if _x+x_wid >= MAP_WIDTH or _y +_wid >= MAP_HEIGHT: # or _x-_wid < 0 or _y -_wid < 0:
                #print 'x{},y{} unnaceptable, sent them home.'.format(_x,_y)
                continue
            if thing in [CHAR_LONG_GRASS,CHAR_TALL_GRASS,CHAR_GRASS]:
                done = True

            done = True
            for __x in range(_x-x_wid,_x+x_wid):
                for __y in range(_y-_wid, _y+_wid):
                    if map [__x][__y].terrain not in acceptable:
                        done = False

            
    
    map[_x][_y] = _center
    s_thing =(_x,_y)

    placed_entry = True
    if thing not in [CHAR_LONG_GRASS]: 
        placed_entry = False

    for _xx in range(max(0,_x-x_wid),min(_x+x_wid,MAP_WIDTH)):
        for _yy in range(max(0,_y-_wid),min(_y+_wid,MAP_HEIGHT)):
            if map[_xx][_yy].terrain in acceptable:
                if random.randint(0,5) < sparse :
                    map[_xx][_yy] = Tile(True,terrain=thing)
                else:
                    if not placed_entry and has_stairs:
                        map[_xx][_yy] = Tile(False,terrain=CHAR_STAIRS)
                        stairs = Object(_xx, _yy, '<', 'stairs', libtcod.white, always_visible=True)
                        placed_entry = True
                    elif map[_xx-1][_yy].terrain in acceptable and map[_xx][_yy-1].terrain in acceptable:
                        map[_xx][_yy] = Tile(True,terrain=thing)    
            else:
                map[_xx][_yy] = Tile(True,terrain=thing)
    if not placed_entry and has_stairs:
        map[_xx][_yy] = Tile(False,terrain=CHAR_STAIRS)
        stairs = Object(_x-x_wid, _y-_wid, '<', 'stairs', libtcod.white, always_visible=True)

    return s_thing


def make_world_map(grassness=20,start=False):
    global map, objects, stairs, dung_list, lair_name

    dung_list = []
    name_list = []
    for i in range(0,25):
        n =  generateName(3)
        name_list.append(n)
    
    if (grassness > MAP_WIDTH / 6):
        grassness = int(MAP_WIDTH / 6)

    if len(objects) > 0:
        for ob in objects:
            if ob.name == "dot":
                new_obj = [ob]
                break
        objects = new_obj
        objects.append(player)
    else:
        objects = [player]

    map = [[Tile(False,terrain=CHAR_LONG_GRASS) for y in range(0,MAP_HEIGHT)] for x in range(0,MAP_WIDTH)]

    #place mountain
    place_thing(CHAR_TALL_GRASS,int(MAP_HEIGHT/3), False,5)

    place_thing(CHAR_MOUNTAIN,8,True,3);
    objects.append(stairs)
    n = random.choice(name_list)
    name_list.remove(n)
    n = '{} montain'.format(n)
    possible_lairs = [n]
    dung_list.append(Dungeon(n,stairs.x, stairs.y))

    place_thing(CHAR_FOREST,6,True,1);
    objects.append(stairs)
    n = random.choice(name_list)
    name_list.remove(n)
    dung_list.append(Dungeon('{}\'s forest'.format(n),stairs.x, stairs.y))

    place_thing(CHAR_LAKE,6,True,3);
    objects.append(stairs)
    n = random.choice(name_list)
    name_list.remove(n)
    n += random.choice([' city',' town',' ville'])
    dung_list.append(Dungeon('{} '.format(n),stairs.x, stairs.y))

    place_thing(CHAR_ICE,6,True,3);
    objects.append(stairs)
    n = 'north pole'
    dung_list.append(Dungeon('{} '.format(n),stairs.x, stairs.y))


    for _x in range(2,4):
        place_thing(CHAR_MOUNTAIN,3,True,3);
        objects.append(stairs)
        n = random.choice(name_list)
        name_list.remove(n)
        n = 'mount {}'.format(n)
        possible_lairs.append(n)
        dung_list.append(Dungeon(n,stairs.x, stairs.y))
        #print '({},{}) - {}'.format(n, stairs.x, stairs.y)

    for _x in range(1,3):
        place_thing(CHAR_FOREST,3,True,1);
        objects.append(stairs)
        n = random.choice(name_list)
        name_list.remove(n)
        dung_list.append(Dungeon('{} woods'.format(n),stairs.x, stairs.y))
    
    for _x in range(1,3):
        place_thing(CHAR_SAND,4+_x, True, 5);
        objects.append(stairs)
        n = random.choice(name_list)
        name_list.remove(n)
        possible_lairs.append(n)
        dung_list.append(Dungeon('{} desert'.format(n),stairs.x, stairs.y))

    
    c = place_thing(CHAR_DIRT,7, False, 6)
    player.x, player.y = c
    addItem('rock',player.x -4, player.y -4)
    addItem('rock',player.x +4, player.y -3)
    if start:
        map[player.x-2][player.y-2] = Tile(True,terrain='-')
        map[player.x-1][player.y-2] = Tile(True,terrain='X')
        map[player.x-3][player.y-2] = Tile(True,terrain='X')
        map[player.x-1][player.y-3] = Tile(True,terrain='.')
        map[player.x-2][player.y-3] = Tile(True,terrain='X')
        map[player.x-3][player.y-3] = Tile(True,terrain='|')
        map[player.x-1][player.y-4] = Tile(True,terrain='-')
        map[player.x-2][player.y-4] = Tile(True,terrain='-')
        map[player.x-3][player.y-4] = Tile(True,terrain='-')

    lair_name = random.choice(possible_lairs)
    #print 'dragon @[{}]'.format(lair_name)

def make_map(terrain=CHAR_MOUNTAIN, name = 'no name'):
    global map, objects, stairs, lair_name, dungeon_level
 
    #the list of objects with just the player
    for ob in objects:
        if ob.name == "dot":
            new_obj = [ob]
            break
    objects = new_obj
    objects.append(player)
 
    _stairs_ = True
    rooms = []
    num_rooms = 0
    min_rooms = 6
    max_rooms_here = MAX_ROOMS
    r_min = ROOM_MIN_SIZE
    r_max = ROOM_MAX_SIZE

    m_wid = MAP_WIDTH
    m_hei = MAP_HEIGHT
    margin = 2

    if name is None:
        name = 'some mountain'
    nm = name.split()[1]
    place_sage = False
    if terrain == CHAR_FOREST or nm in ['forest','woods']:
        max_rooms_here += MAX_ROOMS*15
        min_rooms = MAX_ROOMS
        place_sage = True
        r_max = 8
        r_min = 5
        _stairs_ = False        
        terrain = CHAR_FOREST
        print "sage?"
        if nm in ['forest']:
            print "wise"
            sage_type = 'wise man'
        else:
            print 'old'
            sage_type = 'old man'
        if nm == 'woods':
            margin = 25
    elif terrain == CHAR_LAKE or nm in ['city','town','ville']:
        m_wid = 100
        m_hei = 100
        margin = 25
        r_max = 20
        r_min = 10
        max_rooms_here = 6
        _stairs_ = False        
        terrain = CHAR_LAKE
        inabitants = ['lumberjack','leathersmith','nurse','farmer','blacksmith','nurse']
    elif terrain == CHAR_SAND:
        margin = 5
        r_max = 45
        r_min = 20
        min_rooms = 4
        max_rooms_here = 8
        _stairs_ = True

    elif terrain == CHAR_ICE:
        margin = 5
        r_max = 45
        r_min = 20
        min_rooms = 4
        max_rooms_here = 8
        _stairs_ = False

    if name != lair_name and dungeon_level > 2:
        _stairs_ = False
        margin = 20

    if name.split()[0] == 'mount':
        margin = 15
        r_min -= 3
        r_max -= 3



    #fill map with "blocked" tiles
    map = [[ Tile(True,terrain=terrain)
             for y in range(m_hei) ]
           for x in range(m_wid) ]
    
    #print '2 [{}]< min_rooms [{}]'.format(num_rooms,min_rooms)

    if terrain == CHAR_MOUNTAIN:
        max_rooms_here += MAX_ROOMS*6

    #print 'num_rooms [{}]< min_rooms [{}]'.format(num_rooms,min_rooms)
    iterations = 100
    while num_rooms < min_rooms and iterations > 0:
        for r in range(max_rooms_here):
            #random width and height
            w = libtcod.random_get_int(0, r_min, r_max)
            h = libtcod.random_get_int(0, r_min, r_max)
            #random position without going out of the boundaries of the map
            x = libtcod.random_get_int(0, margin, m_wid - w - margin)
            y = libtcod.random_get_int(0, margin, m_hei - h - margin)
     
            #"Rect" class makes rectangles easier to work with
            new_room = Rect(x, y, w, h)
            #print 'new_room [{}][{}][{}][{}]'.format(x, y, w, h)
            #run through the other rooms and see if they intersect with this one
            failed = False
            for other_room in rooms:
                if new_room.intersect(other_room):
                    failed = True
                    break
     
            if failed:
                iterations -= 1
            else:
                #this means there are no intersections, so this room is valid
                #"paint" it to the map's tiles
                create_room(new_room)
                #center coordinates of new room, will be useful later
                (new_x, new_y) = new_room.center()
                if num_rooms == 0:
                    #this is the first room, where the player starts at
                    player.x = new_x
                    player.y = new_y
                else:
                    #all rooms after the first:
                    #connect it to the previous room with a tunnel
                    #center coordinates of previous room
                    (prev_x, prev_y) = rooms[num_rooms-1].center()
                    #draw a coin (random number that is either 0 or 1)
                    if libtcod.random_get_int(0, 0, 1) == 1:
                        #first move horizontally, then vertically
                        create_h_tunnel(prev_x, new_x, prev_y)
                        create_v_tunnel(prev_y, new_y, new_x)
                    else:
                        #first move vertically, then horizontally
                        create_v_tunnel(prev_y, new_y, prev_x)
                        create_h_tunnel(prev_x, new_x, new_y)
                #add some contents to this room, such as monsters
                if terrain in [CHAR_LAKE]:
                    inabitants = place_homes(new_room,inabitants)
                else:
                    if num_rooms > 0:
                        place_objects(new_room)
                #finally, append the new room to the list
                rooms.append(new_room)
                num_rooms += 1
    
    if place_sage:
        _r_  = rooms[random.randint(2,num_rooms-1)]
        place_homes(_r_,[sage_type])
 
    #create stairs at the center of the last room
    if _stairs_:
        #stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
        map[new_x][new_y].terrain = '<'
        if terrain == CHAR_SAND:
            map[new_x][new_y-1].terrain = CHAR_MOUNTAIN
            map[new_x][new_y+1].terrain = CHAR_MOUNTAIN
            map[new_x+1][new_y-1].terrain = CHAR_MOUNTAIN
            map[new_x+1][new_y].terrain = CHAR_MOUNTAIN
            map[new_x+1][new_y+1].terrain = CHAR_MOUNTAIN
            map[new_x+2][new_y-1].terrain = CHAR_MOUNTAIN
            map[new_x+2][new_y].terrain = CHAR_MOUNTAIN
            map[new_x+2][new_y+1].terrain = CHAR_MOUNTAIN
        #objects.append(stairs)
        #stairs.send_to_back()  #so it's drawn below the monsters

    map[player.x][player.y].terrain = '>'
    map[player.x][player.y].color = libtcod.yellow

def getMapFromFile():
    string_map = ['#######################################################'];

    portal = ['################################################################################',
        '#########                                #######################################',
        '########   ############################# #######################################',
        '#######     ############################ ########################################',
        '####### x < ###########################     #####################################',
        '######## > ##########################         ###################################',
        '####################################           ##################################',
        '##################################               ################################',
        '#################################                 ###############################',
        '################################                   ##############################',
        '##########################                         #######################   ####',
        '######################                                 ###           ##### u ####',
        '#####################         #                    #    ##       ##   ####   ####',
        '#####################       ####                   ##   ##  ##   ##   ##### ######',
        '#####################      #####                   ##   ##  ##   ##   ##### ######',
        '#####################      #####                   ##    #  ##    #   ####  ######',
        '######################      ####                   ##       ##    #    ##   ######',
        '########################     ###                   ###      ###   ##       #######',
        '##########################                         ##################     #######',
        '############################                       ##############################',
        '#################################                 ###############################',
        '##################################               ################################',
        '####################################           ##################################',
        '#####################################         ###################################',
        '#######################################     #####################################',
        '########################################   ######################################',
        '########################################   ######################################',
        '####################   ---             #             --- ########################',
        '####################   |_[ @           #  #          ]_| ########################',
        '####################   ---                #          --- ########################',
        '########################################  #######################################',
        '######################################## #######################################',
        '######################################## #######################################',
        '######################################    i#####################################',
        '######################################  z     y#################################',
        '######################################     #####################################',
        '################################################################################',
        '################################################################################',
        '################################################################################',
        '################################################################################']
    string_map = portal

    return string_map

def make_customgenericmap(terrain = CHAR_MOUNTAIN):
    global map, objects, stairs
    smap = getMapFromFile()
    
    MAP_HEIGHT1 = len(smap)
    MAP_WIDTH1 = len(smap[0])
    map = [[Tile(True,terrain=terrain) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
    princess = False

    for ob in objects:
        if ob.name == "dot":
            new_obj = [ob]
            break
    objects = new_obj

    for y in range(MAP_HEIGHT1):
        for x in range(MAP_WIDTH1):
            t = smap[y][x]  
            if t == 'x':
                new_x = x
                new_y = y
                map[x][y] = Tile(False,CHAR_STAIRS)
            elif t == 'y':
                player.x = x
                player.y = y
            elif t == 'u':
                map[x][y] = Tile(False,CHAR_DIRT)
                addMonster('princess',x,y)
                princess = True
            elif t == '@':
                    map[x][y] = Tile(False,CHAR_DIRT)
                    addMonster('nurse',x,y)
            elif t != '#':
                map[x][y] = Tile(False,t)

    stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    map[new_x][new_y] = Tile(False, CHAR_STAIRS)
    objects.append(stairs)
    stairs.send_to_back()  #so it's drawn below the monsters
       
def make_bsp():
    global map, objects, stairs, bsp_rooms
 
    objects = [player]
 
    map = [[Tile(True,terrain=CHAR_FOREST) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
 
    #Empty global list for storing room coordinates
    bsp_rooms = []
 
    #New root node
    bsp = libtcod.bsp_new_with_size(0, 0, MAP_WIDTH, MAP_HEIGHT)
 
    #Split into nodes
    libtcod.bsp_split_recursive(bsp, 0, DEPTH, MIN_SIZE + 1, MIN_SIZE + 1, 1.5, 1.5)
 
    #Traverse the nodes and create rooms                            
    libtcod.bsp_traverse_inverted_level_order(bsp, traverse_node)
 
    #Random room for the stairs
    stairs_location = random.choice(bsp_rooms)
    bsp_rooms.remove(stairs_location)
    stairs = Object(stairs_location[0], stairs_location[1], '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()
 
    #Random room for the console
    console_location = random.choice(bsp_rooms)
    bsp_rooms.remove(console_location)
    console = Object(console_location[0], console_location[1], '#', 'console', libtcod.white, always_visible=True)
    objects.append(console)
    console.send_to_back()
    
    #Random room for player start
    player_room = random.choice(bsp_rooms)
    bsp_rooms.remove(player_room)
    player.x = player_room[0]
    player.y = player_room[1]
 
    #Add monsters and items
    for room in bsp_rooms:
        new_room = Rect(room[0], room[1], 2, 2)
        place_objects(new_room)
 
    initialize_fov()

def traverse_node(node, dat):
    global map, bsp_rooms
 
    #Create rooms
    if libtcod.bsp_is_leaf(node):
        minx = node.x + 1
        maxx = node.x + node.w - 1
        miny = node.y + 1
        maxy = node.y + node.h - 1
 
        if maxx == MAP_WIDTH - 1:
            maxx -= 1
        if maxy == MAP_HEIGHT - 1:
            maxy -= 1
 
        #If it's False the rooms sizes are random, else the rooms are filled to the node's size
        if FULL_ROOMS == False:
            minx = libtcod.random_get_int(None, minx, maxx - MIN_SIZE + 1)
            miny = libtcod.random_get_int(None, miny, maxy - MIN_SIZE + 1)
            maxx = libtcod.random_get_int(None, minx + MIN_SIZE - 2, maxx)
            maxy = libtcod.random_get_int(None, miny + MIN_SIZE - 2, maxy)
 
        node.x = minx
        node.y = miny
        node.w = maxx-minx + 1
        node.h = maxy-miny + 1
 
        #Dig room
        for x in range(minx, maxx + 1):
            for y in range(miny, maxy + 1):
                map[x][y].blocked = False
                map[x][y].block_sight = False
 
        #Add center coordinates to the list of rooms
        bsp_rooms.append(((minx + maxx) / 2, (miny + maxy) / 2))
 
    #Create corridors    
    else:
        left = libtcod.bsp_left(node)
        right = libtcod.bsp_right(node)
        node.x = min(left.x, right.x)
        node.y = min(left.y, right.y)
        node.w = max(left.x + left.w, right.x + right.w) - node.x
        node.h = max(left.y + left.h, right.y + right.h) - node.y
        if node.horizontal:
            if left.x + left.w - 1 < right.x or right.x + right.w - 1 < left.x:
                x1 = libtcod.random_get_int(None, left.x, left.x + left.w - 1)
                x2 = libtcod.random_get_int(None, right.x, right.x + right.w - 1)
                y = libtcod.random_get_int(None, left.y + left.h, right.y)
                vline_up(map, x1, y - 1)
                hline(map, x1, y, x2)
                vline_down(map, x2, y + 1)
 
            else:
                minx = max(left.x, right.x)
                maxx = min(left.x + left.w - 1, right.x + right.w - 1)
                x = libtcod.random_get_int(None, minx, maxx)
                vline_down(map, x, right.y)
                vline_up(map, x, right.y - 1)
 
        else:
            if left.y + left.h - 1 < right.y or right.y + right.h - 1 < left.y:
                y1 = libtcod.random_get_int(None, left.y, left.y + left.h - 1)
                y2 = libtcod.random_get_int(None, right.y, right.y + right.h - 1)
                x = libtcod.random_get_int(None, left.x + left.w, right.x)
                hline_left(map, x - 1, y1)
                vline(map, x, y1, y2)
                hline_right(map, x + 1, y2)
            else:
                miny = max(left.y, right.y)
                maxy = min(left.y + left.h - 1, right.y + right.h - 1)
                y = libtcod.random_get_int(None, miny, maxy)
                hline_left(map, right.x - 1, y)
                hline_right(map, right.x, y)
 
    return True

def vline(map, x, y1, y2):
    if y1 > y2:
        y1,y2 = y2,y1
 
    for y in range(y1,y2+1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def vline_up(map, x, y):
    while y >= 0 and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        y -= 1
 
def vline_down(map, x, y):
    while y < MAP_HEIGHT and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        y += 1
 
def hline(map, x1, y, x2):
    if x1 > x2:
        x1,x2 = x2,x1
    for x in range(x1,x2+1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def hline_left(map, x, y):
    while x >= 0 and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        x -= 1
 
def hline_right(map, x, y):
    while x < MAP_WIDTH and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        x += 1

def random_choice_index(chances):  #choose one option from list of chances, returning its index
    #the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))
 
    #go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w
 
        #see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1
 
def random_choice(chances_dict):
    #choose one option from dictionary of chances, returning its key
    chances = chances_dict.values()
    strings = chances_dict.keys()
 
    return strings[random_choice_index(chances)]
 
def from_dungeon_level(table):
    #returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0

def place_homes(room, inabitants):
    x,y = room.center() # = libtcod.random_get_int(0, room.x1+5, room.x1+10)
    #y = libtcod.random_get_int(0, room.y1+5, room.y2-5)
    npc = random.choice(inabitants)
    inabitants.remove(npc)
    
    if npc not in ['old man','wise man']:
        map[x-2][y-2] = Tile(True,terrain='-')
        map[x-1][y-2] = Tile(True,terrain='-')
        map[x-3][y-2] = Tile(True,terrain='-')
        map[x-3][y-3] = Tile(True,terrain='|')
        map[x-2][y-3] = Tile(True,terrain='_')
        map[x-1][y-3] = Tile(True,terrain=']')
        map[x-1][y-4] = Tile(True,terrain='-')
        map[x-2][y-4] = Tile(True,terrain='-')
        map[x-3][y-4] = Tile(True,terrain='-')
    else:
        map[x-2][y-2] = Tile(True,terrain='_')
        map[x-1][y-2] = Tile(True,terrain='_')
        map[x-3][y-2] = Tile(True,terrain='_')
        map[x-3][y-3] = Tile(True,terrain='_')
        map[x-2][y-3] = Tile(True,terrain='_')
        map[x-1][y-3] = Tile(True,terrain='_')
        map[x-1][y-4] = Tile(True,terrain='_')
        map[x-2][y-4] = Tile(True,terrain='_')
        map[x-3][y-4] = Tile(True,terrain='_')

    addMonster(npc, x-1, y-3)
    if random.randint(1,30) > 15:
        objects.append(Object(x-2, y-3, '$', 'money', libtcod.yellow, always_visible=True))

    return inabitants

def place_objects(room):
    #this is where we decide the chance of each monster or item appearing.
 
    #maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
 
    #chance of each monster
    monster_chances = {}
    monster_chances['kobold low_level'] = 25 
    monster_chances['kobold mid_level'] = 20
    monster_chances['kobold high_level'] = 15
 
    #maximum number of items per room
    max_items = 1
 
    #chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    items = ['wooden stick']
    if dungeon_name.split()[1] in ['pole']:
        monster_chances['kobold low_level'] = 0 
        monster_chances['kobold mid_level'] = 0
        monster_chances['kobold high_level'] = 0
        monster_chances['walrus warrior'] = 95
    if dungeon_name.split()[1] in ['woods']:
        items.append('bag')
    if dungeon_name.split()[1] in ['woods','forest']:
        monster_chances['kobold low_level'] = 5 
        monster_chances['kobold mid_level'] = 15
        monster_chances['kobold high_level'] = 5
        monster_chances['wolf animal'] = 25
    if dungeon_name.split()[1] in ['desert']:
        items.append('rock')
        monster_chances['kobold low_level'] = 0 
        monster_chances['kobold mid_level'] = 0
        monster_chances['kobold high_level'] = 0
        if dungeon_level == 1:
            monster_chances['anangu hunter'] = 5
            monster_chances['desert worm'] = 95
        else:
            monster_chances['anangu hunter'] = 95
    if dungeon_name not in lair_name and dungeon_level > 2:
        monster_chances['kobold champion'] = 5
 
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 2, 6)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            addMonster(choice,x,y,'aggressive')

    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, 1) # max_items)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random.choice(items)
            addItem(choice,x,y)

def addItem(name,x=-1,y=-1,player=True):
    if name == 'wooden spear':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '|', 'wooden spear', libtcod.dark_sepia, equipment=equipment_component)
    elif name == 'wooden stick':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '/', 'wooden stick', libtcod.light_sepia, equipment=equipment_component)
    elif name == 'leather whip':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '\\', 'leather whip', libtcod.light_sepia, equipment=equipment_component)
    elif name == 'work axe':
        equipment_component = Equipment(slot='right hand', power_bonus=2)
        item = Object(x, y, 'P', 'work axe', libtcod.silver, equipment=equipment_component)
    elif name == 'war axe':
        equipment_component = Equipment(slot='right hand', power_bonus=3)
        item = Object(x, y, 'P', 'war axe', libtcod.white, equipment=equipment_component)
    elif name == 'wooden boomerang':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '(', 'wooden boomerang', libtcod.light_sepia, equipment=equipment_component)
    elif name == 'short sword':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '-', 'short sword', libtcod.dark_grey, equipment=equipment_component)
    elif name == 'combat knife':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '-', 'combat knife', libtcod.light_grey, equipment=equipment_component)
    elif name == 'crysknife':
        equipment_component = Equipment(slot='right hand', power_bonus=3)
        item = Object(x, y, '-', 'crys knife', libtcod.white, equipment=equipment_component)
    elif name == 'pocket knife':
        equipment_component = Equipment(slot='right hand', power_bonus=1)
        item = Object(x, y, '-', 'pocket knife', libtcod.light_grey, equipment=equipment_component)
    elif name == 'long sword':
        equipment_component = Equipment(slot='right hand', power_bonus=2)
        item = Object(x, y, '-', 'long sword', libtcod.silver, equipment=equipment_component)
    elif name == 'rock':
        if random.randint(1,2) == 2:
            equipment_component = Equipment(slot='right hand', power_bonus=1)
            item = Object(x, y, '*', 'small rock', libtcod.silver, equipment=equipment_component)
        else:
            equipment_component = Equipment(slot='right hand', power_bonus=2)
            item = Object(x, y, '*', 'large rock', libtcod.silver, equipment=equipment_component)
    elif name == 'shirt':
        equipment_component = Equipment(slot='body', defense_bonus=0)
        st = random.choice(['hawaiian ','business ','white t-','manowar t-','ulver t-','abba t-','radiohead t-','old t-','pink ','sleeveless ','colorful poncho','clean toga','dirty rags'])
        if st not in ['colorful poncho','clean toga','dirty rags']:
            st = '{}shirt'.format(st)
        item = Object(x, y, 't', st, libtcod.white, equipment=equipment_component)
    elif name == 'leather armour':
        equipment_component = Equipment(slot='body', defense_bonus=2)
        item = Object(x, y, 'a', 'leather armour', libtcod.sepia, equipment=equipment_component)
    elif name == 'still suit':
        equipment_component = Equipment(slot='body', defense_bonus=2, power_bonus=1)
        item = Object(x, y, 's', 'still suit', libtcod.sepia, equipment=equipment_component)
    elif name == 'metal armour':
        equipment_component = Equipment(slot='body', defense_bonus=3)
        item = Object(x, y, 'a', 'metal armour', libtcod.silver, equipment=equipment_component)
    elif name == 'bag':
        equipment_component = Equipment(slot='right hand', capacity=3)
        item = Object(x, y, '#', 'plastic bag', libtcod.white, equipment=equipment_component)
    elif name == 'backpack':
        if random.randint(0,3) > 2:
            equipment_component = Equipment(slot='back', capacity=5)
            item = Object(x, y, '#', 'fancy backpack', libtcod.white, equipment=equipment_component)
        else:
            equipment_component = Equipment(slot='back', capacity=4)
            item = Object(x, y, '#', 'ugly backpack', libtcod.white, equipment=equipment_component)
    elif name == 'hat':
        nm = random.choice(['trucker ','cowboy ','sombrero ','clown ','flower ','party ','bandanna '])
        if nm in ['flower ','party ','bandanna ']:
            equipment_component = Equipment(slot='head',defense_bonus=0)
        else:
            equipment_component = Equipment(slot='head',defense_bonus=1)
        item = Object(x, y, '^', '{}hat'.format(nm), libtcod.white, equipment=equipment_component)
    elif name == 'elm':
        equipment_component = Equipment(slot='head',defense_bonus=2)
        item = Object(x, y, '^', 'metal elm', libtcod.white, equipment=equipment_component)
    elif name == 'leather hat':
        equipment_component = Equipment(slot='head')
        item = Object(x, y, '^', 'leather hat', libtcod.white, equipment=equipment_component)
    else:
        equipment_component = Equipment(slot='neck', defense_bonus=0)
        item = Object(x,y,'*','fashion statement colar', libtcod.yellow, equipment=equipment_component)

    if player:
        objects.append(item)
        item.send_to_back()  #items appear below other objects
        item.always_visible = True  #items are visible even out-of-FOV, if in an explored areas
    else:
        return item

def generateName(_max_size = 6):
    _name = ''
    for _i_ in range(0,random.randint(2,_max_size)):
        _name += random.choice(['b','c','d','f','g','h','j','k','l','','m','n','p','r','s','t','v','','w','x','z'])
        _name += random.choice(['a','e','a','e','i','o','u','y'])
    
    return _name
def addMonster(name,x=-1,y=-1,state='none',returnM=False):
    if state == 'none':
        if name.split()[0] in ['low_level','kobold']:
            state = random.choice(['aggressive','watchfull'])
        elif name.split()[0] in ['worm','wolf','wallrus']:
            state = 'neutral'
            name = '{} animal'.format(name)
    personal_name = generateName()
    if x == -1:
        x = random.randint(0, MAP_WIDTH-1)
    if y == -1:
        y = random.randint(0,MAP_HEIGHT-1)
    if name == 'princess':
        fighter_component = Fighter(hp=7, defense=20, power=0, xp=0, death_function=monster_death, state='friendly')
        ai_component = Shopowner()
        monster = Object(x, y, '@', 'princess shmi', libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name == 'farmer':
        fighter_component = Fighter(hp=6, defense=8, power=1, xp=0, death_function=monster_death, state='friendly')
        ai_component = Shopowner()
        monster = Object(x, y, '@', 'farmer {}'.format(personal_name), libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name == 'walrus warrior':
        fighter_component = Fighter(hp=8, defense=2, power=2, xp=0, death_function=monster_death, state='friendly')
        ai_component = BasicMonster()
        monster = Object(x, y, 'W', 'walrus warrior {}'.format(personal_name), libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name in ['old man','wise man']:
        fighter_component = Fighter(hp=8, defense=9, power=9, xp=0, death_function=wolf_death, state='friendly')
        ai_component = Shopowner()
        monster = Object(x, y, '@', name, libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name in ['lumberjack','leathersmith','blacksmith','nurse']:
        fighter_component = Fighter(hp=6, defense=8, power=6, xp=0, death_function=monster_death, state='friendly')
        ai_component = Shopowner()
        monster = Object(x, y, '@', '{} {}'.format(name, personal_name), libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name.split()[1] in ['low_level'] and name.split()[0] in ['kobold']:
        #create a low level monster
        fighter_component = Fighter(hp=2, defense=3, power=1, xp=35, death_function=monster_death,state=state)
        ai_component = BasicMonster()
        monster = Object(x, y, 'k', 'kobold {}'.format(personal_name), libtcod.light_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name.split()[0] in ['mid_level'] and name.split()[0] in ['kobold']:
        #create a monster_mid_level
        fighter_component = Fighter(hp=4, defense=4, power=2, xp=65, death_function=monster_death,state=state)
        ai_component = BasicMonster()
        monster = Object(x, y, 'k', 'kobold {}'.format(personal_name), libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name.split()[1] in ['champion'] and name.split()[0] in ['kobold']:
        #create a kobold champion
        fighter_component = Fighter(hp=6, defense=5, power=5, xp=85, death_function=monster_death,state=state)
        ai_component = BasicMonster()
        monster = Object(x, y, 'K', 'kobold champion', libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name.split()[0] in ['high_level'] and name.split()[0] in ['kobold']:
        #create a high_level_monster
        fighter_component = Fighter(hp=5, defense=4, power=2, xp=85, death_function=monster_death,state=state)
        ai_component = BasicMonster()
        monster = Object(x, y, 'k', 'kobold {}'.format(personal_name), libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name.split()[0] == 'wolf':
        fighter_component = Fighter(hp=4, defense=2, power=4, xp=85, death_function=wolf_death,state='wandering')
        ai_component = BasicMonster()
        monster = Object(x, y, 'w', 'wolf', libtcod.silver, blocks=True, fighter=fighter_component, ai=ai_component)
    elif name == 'desert worm':
        fighter_component = Fighter(hp=2, defense=2, power=2, xp=3, death_function=monster_death_no_loot,state='wandering')
        ai_component = BasicMonster()
        monster = Object(x, y, '~', 'desert worm', libtcod.pink,blocks=True, fighter=fighter_component, ai=ai_component)
    elif name == 'anangu hunter':
        fighter_component = Fighter(hp=5, defense=1, power=6, xp=35, death_function=monster_death,state=random.choice(['wandering','friendly']))
        ai_component = BasicMonster()
        monster = Object(x, y, '@', 'anangu hunter', libtcod.white,blocks=True, fighter=fighter_component, ai=ai_component)
    else:
        fighter_component = Fighter(hp=1, defense=0, power=1, xp=3, death_function=monster_death_no_loot,state='wandering')
        ai_component = BasicMonster()
        monster = Object(x, y, '~', 'worm', libtcod.pink,blocks=True, fighter=fighter_component, ai=ai_component)

    if returnM:
        return monster
    objects.append(monster)
    
def add_dragon():
    global objects
    fighter_component = Fighter(hp=20, defense=9, power=8, xp=800, death_function=dragon_death)
    ai_component = BasicMonster()
    monster = Object(40, 10, 'O', 'dragon head', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=6, defense=10, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster)
    monster_body = Object(40,9, '*', 'dragon upper body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=6, defense=7, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_body2 = Object(40,8, '*', 'dragon mid body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=6, defense=7, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_body3 = Object(40,7, '*', 'dragon lower body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=6, defense=5, power=2, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_tail = Object(40,8, 'v', 'dragon tail', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    objects.append(monster)
    objects.append(monster_body)
    objects.append(monster_body2)
    objects.append(monster_body3)
    objects.append(monster_tail)


def addShaiHulud(x,y):
    global objects
    message('shai-hulud appears!', libtcod.light_red)
    y-=2
    fighter_component = Fighter(hp=30, defense=12, power=8, xp=800, death_function=monster_death)
    ai_component = ShaiHulud()
    monster = Object(x, y, 'O', 'shai-hulud head', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    objects.append(monster)



def nothing():
    """
        end 
            map 
                stuff   
                    """

#horizontal_menu
def horizontal_menu(header, options, width, value = 0, x_offset = 0, y_offset = 0, _max=0,_min=0):
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
    
 
    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    line_num = 0

    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    while True:
        y = header_height
        line_num = 0
        for option_text in options:
            text = ''  + option_text + ' - [{}] + '.format(value) 
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        line_num += 1
        
        #blit the contents of "window" to the root console
        x = 2 #SCREEN_WIDTH/2 - width/2
        #y = 4 #SCREEN_HEIGHT/2 - height/2
        libtcod.console_blit(window, 0, 0, width, height, 0, x+x_offset, y+y_offset, 1.0, 1.0)
     
        #present the root console to the player and wait for a key-press
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
        key = libtcod.console_wait_for_keypress(True)

        
        if key.vk == libtcod.KEY_DOWN:
            return value
        elif key.vk == KEY_JUMP:
            return value
        elif key.vk == libtcod.KEY_ENTER:
            return value
        elif key.vk == KEY_ACCEL:
            if value < _max or _max == 0:
                value+=1
        elif key.vk == KEY_BREAK:
            if value > _min:
                value-=1
        elif key.vk == libtcod.KEY_ESCAPE:
            return -1

#basic arrow menu
def arrow_menu(header, options, width, selection = 0, x_offset = 0, y_offset = 0):
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
    
 
    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    line_num = 0
    libtcod.console_set_default_background(window, libtcod.black)
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    while selection >= -1:
        if selection < 0 :
            selection = len(options)-1
        elif selection > len(options)-1:
            selection = 0

        y = header_height
        line_num = 0
        for option_text in options:
            if line_num == selection:
                libtcod.console_set_default_foreground(window, libtcod.yellow)
                text = '+--'  + option_text+'  '
                #print text
            else:
                libtcod.console_set_default_foreground(window, libtcod.silver)
                text = ' ' + option_text+'      '
            libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
            y += 1
            letter_index += 1
            line_num += 1
        
        #blit the contents of "window" to the root console
        x = 2 #SCREEN_WIDTH/2 - width/2
        #y = 4 #SCREEN_HEIGHT/2 - height/2
        libtcod.console_blit(window, 0, 0, width, height, 0, x+x_offset, y+y_offset, 1.0, 1.0)
     
        #present the root console to the player and wait for a key-press
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
        key = libtcod.console_wait_for_keypress(True)

        key_char = chr(key.c)
        if key.vk in [libtcod.KEY_UP,libtcod.KEY_LEFT,libtcod.KEY_KP8, libtcod.KEY_KP4] or key_char in ['w','W','A','a']:
            selection-=1
        elif key.vk in [libtcod.KEY_DOWN,libtcod.KEY_RIGHT,libtcod.KEY_KP2, libtcod.KEY_KP6] or key_char in ['s','S','D','d']:
            selection+=1
        elif key.vk in [libtcod.KEY_ENTER,libtcod.KEY_KP7] or key_char in ['e','E','f','F']:
            return selection
        elif key.vk in [libtcod.KEY_ESCAPE,libtcod.KEY_KP5,libtcod.KEY_KP1] or key_char in ['q','Q','c','C']:
            return -1


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    libtcod.console_set_default_background(panel_v, back_color)
    libtcod.console_rect(panel_v, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
 
    #now render the bar on top
    libtcod.console_set_default_background(panel_v, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel_v, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
 
    #finally, some centered text with the values
    libtcod.console_set_default_foreground(panel_v, libtcod.white)
    libtcod.console_print_ex(panel_v, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                                 name + ':' + str(value) + '/' + str(maximum))
 
#def get_names_under_mouse():
def get_terrain_name(terrain):
    if terrain == CHAR_DIRT:
        return 'floor'
    elif terrain == CHAR_SAND:
        return 'desert'
    elif terrain == CHAR_MOUNTAIN:
        return 'mountains'
    elif terrain == CHAR_GRASS:
        return 'low grass'
    elif terrain == CHAR_LONG_GRASS:
        return 'grass'
    elif terrain == CHAR_TALL_GRASS:
        return 'tall grass'
    elif terrain == CHAR_LAKE:
        return 'water'
    elif terrain == CHAR_ROAD:
        return 'roads'
    elif terrain in [CHAR_STAIRS,'<','>']:
        return 'stairs'
    elif terrain in ['|','-','[',']']:
        return 'house'
    elif terrain == CHAR_FOREST:
        return 'trees'
    else:
        return '[{}]'.format(terrain)

def get_names(x,y):
    global mouse
    #return a string with the names of all objects under the mouse
    
    #(x, y) = (mouse.cx, mouse.cy)
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV

    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and obj.name != 'dot' and obj.name != 'stairs']


    if dungeon_level == 0 and get_dungeon_name(x,y) != 'no where':
        return get_dungeon_name(x,y)
    elif len(names) < 1:
        return get_terrain_name(map[x][y].terrain)
    else:
        names.sort()
        nm_old = ''
        nm_cnt = 0
        out_names = []
        
        for nm in names:
            if nm == nm_old:
                nm_cnt+=1
            else:
                if nm_cnt > 1:
                    out_names.append('{} x{}'.format(nm_old,nm_cnt))
                else:
                    out_names.append('{}'.format(nm_old))
                nm_cnt = 1
                nm_old = nm
        if nm==nm_old:
            if nm_cnt > 1:
                out_names.append('{} x{}'.format(nm_old,nm_cnt))
            else:
                out_names.append('{}'.format(nm_old))
        out_names = ', '.join(out_names)
    return out_names

def move_camera(target_x, target_y):
    global camera_x, camera_y, fov_recompute
 
    #new camera coordinates (top-left corner of the screen relative to the map)
    x = target_x - CAMERA_WIDTH / 2  #coordinates so that the target is at the center of the screen
    y = target_y - CAMERA_HEIGHT / 2
 
    #make sure the camera doesn't see outside the map
    if x < 0: x = 0
    if y < 0: y = 0
    if x > MAP_WIDTH - CAMERA_WIDTH - 1: x = MAP_WIDTH - CAMERA_WIDTH - 1
    if y > MAP_HEIGHT - CAMERA_HEIGHT - 1: y = MAP_HEIGHT - CAMERA_HEIGHT - 1
 
    if x != camera_x or y != camera_y: fov_recompute = True
 
    (camera_x, camera_y) = (x, y)
 
def to_camera_coordinates(x, y):
    #convert coordinates on the map to coordinates on the screen
    (x, y) = (x - camera_x, y - camera_y)
 
    if (x < 0 or y < 0 or x >= CAMERA_WIDTH or y >= CAMERA_HEIGHT):
        return (None, None)  #if it's outside the view, return nothing
 
    return (x, y)

def get_square(width,height,i_x,i_y,is_dungeon=False):


    str = '({},{})->({},{})'.format(i_x,i_y,i_x+width,i_y+height)
#            0 1 2 3 4 5 6 7 8 9 0 1 2 3     
#              @ < > ; , ` . # T ~ '
    count = [0,0,0,0,0,0,0,0,0,0,0,0]
    
    for y in range(i_y,i_y+height):
        for x in range(i_x,i_x+width):
            tile = map[x][y]
            if player.x == x and player.y == y:
                return 1
            if is_dungeon and tile.terrain in ['<']:
                return 2
            elif is_dungeon and tile.terrain in ['>']:
                return 3
            if tile.terrain == CHAR_TALL_GRASS:
                count[4]+=1
            elif tile.terrain == CHAR_LONG_GRASS:
                count[5]+=1
            elif tile.terrain == CHAR_GRASS:
                count[6]+=1
            elif tile.terrain == CHAR_DIRT:
                count[7]+=1
            elif tile.terrain == CHAR_MOUNTAIN:
                count[8]+=1
            elif tile.terrain == CHAR_FOREST:
                count[9]+=1
            elif tile.terrain == CHAR_LAKE:
                count[10]+=1
            elif tile.terrain == CHAR_SAND:
                count[11]+=1
    i = 0
    _max = 0


    while i < len(count):
        if count[i] > _max and i >= 5:
            _max = count[i]
        else:
            i+=1
    if _max != 0:
        t = count.index(_max)
    else:
        t = count.index(max(count))
    return t

def get_terrains(width,height):
    global map, dungeon_level

    if dungeon_level > 0:
        is_dungeon = True
    else:
        is_dungeon = False
    mmap = []
    #        0 1 2 3 4 5 6 7 8 9 0 1 2 3     
    #          @ < > ; , ` . # T ~ S

    _ter_ = [' ','@','>','<',CHAR_TALL_GRASS,CHAR_LONG_GRASS,CHAR_GRASS,CHAR_DIRT,CHAR_MOUNTAIN,CHAR_FOREST,CHAR_LAKE,CHAR_SAND]
    mmap_x = 0
    mmap_y = 0

    while (mmap_y < MAP_HEIGHT):
        while(mmap_x < MAP_WIDTH):
            t = get_square(10,10,mmap_x,mmap_y,is_dungeon)
            til = _ter_[t]  ##Tile(True,_ter_[t])
            mmap.append(til)
            mmap_x += 10
        mmap_y += 10
        mmap_x = 0
        
    return mmap

def get_color(t):
        if t == CHAR_MOUNTAIN or t == CHAR_DIRT:
            color = libtcod.light_sepia
        elif t == CHAR_LAKE:
            color = libtcod.blue
        elif t in [CHAR_STAIRS,CHAR_SAND]:
            color = libtcod.light_yellow
        elif t == CHAR_TALL_GRASS or t == CHAR_FOREST:
            color = libtcod.darker_green
        elif t == CHAR_LONG_GRASS:
            color = libtcod.dark_green
        elif t == '@':
            color = libtcod.white
        else:
            color = libtcod.green
        return color

def mini_map(stop = True):
    width = int(MAP_WIDTH / 10)
    height = int(MAP_HEIGHT / 10)

    window = libtcod.console_new(width, height)
 
    #print all the options
    mmap = get_terrains(width, height)
    st=' '
    x = 0
    y = 0
    st=' '
    for t in mmap:
        if t == CHAR_MOUNTAIN or t == CHAR_DIRT:
            color = libtcod.light_sepia
        elif t == CHAR_LAKE:
            color = libtcod.blue
        elif t == CHAR_STAIRS:
            color = libtcod.light_yellow
        elif t == CHAR_TALL_GRASS or t == CHAR_FOREST:
            color = libtcod.darker_green
        elif t == CHAR_LONG_GRASS:
            color = libtcod.dark_green
        elif t == CHAR_SAND:
            color = libtcod.yellow
        elif t in ['@','<']:
            color = libtcod.white
        else:
            color = libtcod.green

        libtcod.console_set_default_foreground(window, color)
        libtcod.console_print_ex(window, x, y, libtcod.BKGND_DARKEN, libtcod.LEFT, t)
        st += '{}'.format(t)
        x+=1
        if x >= width:
            st+=' \n'
            x=0
            y+=1
    #print st

    #blit the contents of "window" to the root console
    x = int(SCREEN_WIDTH / 3)
    y = int(SCREEN_HEIGHT / 3)
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 1.0)
 
    #present the root console to the player and wait for a key-press
    if stop:
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
 
        if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)


def render_all():
    global fov_map, color_dark_wall, color_light_wall, dungeon_name
    global color_dark_ground, color_light_ground
    global game_animations,notifications
    global fov_recompute

    move_camera(player.x, player.y)

    
    if fov_recompute:
        #recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
        #go through all tiles, and set their background color according to the FOV
        for y in range(CAMERA_HEIGHT): 
            for x in range(CAMERA_WIDTH):
                (s_x, s_y) = (camera_x + x, camera_y + y)

                visible = libtcod.map_is_in_fov(fov_map, s_x, s_y)
                wall = map[s_x][s_y].block_sight
                if not visible:
                    #if it's not visible right now, the player can only see it if it's explored
                    if map[s_x][s_y].explored:
                        if wall:
                            #libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                            libtcod.console_set_default_foreground(con, map[s_x][s_y].color)
                            libtcod.console_put_char(con, x, y, map[s_x][s_y].terrain, libtcod.BKGND_NONE)
                        else:
                            libtcod.console_set_default_foreground(con, map[s_x][s_y].color)
                            libtcod.console_put_char(con, x, y, map[s_x][s_y].terrain, libtcod.BKGND_NONE)

                            #libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    #it's visible
                    if wall:
                        libtcod.console_set_default_foreground(con, map[s_x][s_y].color)
                        libtcod.console_put_char(con, x, y, map[s_x][s_y].terrain, libtcod.BKGND_NONE)
                        #libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET )
                    else:
                        libtcod.console_set_default_foreground(con, map[s_x][s_y].color)
                        libtcod.console_put_char(con, x, y, map[s_x][s_y].terrain, libtcod.BKGND_NONE)
                        #libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET )
                        #since it's visible, explore it
                    map[s_x][s_y].explored = True
 
    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for o in objects:
        if o.name == 'dot':
            dot_x = o.x
            dot_y = o.y
            o.draw()
    
    for object in objects:
        if object != player and not object.name == 'dot':
            object.draw()
    player.draw()

    for _a_ in notifications:
        if _a_._tick(con) == 'done':
            notifications.remove(_a_)

    for anim in game_animations:
    #    #sleep(0.1)
        anim.step()

 
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
 
    #prepare to render the GUI v panel
    libtcod.console_set_default_background(panel_v, libtcod.black)
    libtcod.console_clear(panel_v)

    width = int(MAP_WIDTH / 10)
    height = int(MAP_HEIGHT / 10)
    mmap = get_terrains(width, height)
    st=' '
    x = 0
    y = 0
    st=' '
    for t in mmap:
        color = get_color(t)
        libtcod.console_set_default_foreground(panel_v, color)
        libtcod.console_print_ex(panel_v, x+1, y, libtcod.BKGND_DARKEN, libtcod.LEFT, t)
        st += '{}'.format(t)
        x+=1
        if x >= width :
            st+=' \n'
            x=0
            y+=1

    #prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_set_default_foreground(panel_v, libtcod.white)
    libtcod.console_clear(panel)
 
    #print the game messages, one line at a time
    y = 2
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT,line)
        y += 1
 
    #libtcod.console_print_ex(panel, )
    libtcod.console_print_ex(panel_v, 1, 10, libtcod.BKGND_NONE, libtcod.LEFT, '----------')
    hp = player.fighter.hp
    if hp < 7:
        __color = HEALTH_COLOR[hp]
    else:
        __color = libtcod.white
    libtcod.console_set_default_foreground(panel_v, __color)
    libtcod.console_print_ex(panel_v, 1, 11, libtcod.BKGND_NONE, libtcod.LEFT, ' [{}]'.format(HEALTH[hp]))
    libtcod.console_set_default_foreground(panel_v, libtcod.white)
    libtcod.console_print_ex(panel_v, 1, 13, libtcod.BKGND_NONE, libtcod.LEFT, dungeon_name.split()[0])
    libtcod.console_print_ex(panel_v, 1, 14, libtcod.BKGND_NONE, libtcod.LEFT, dungeon_name.split()[1])

    libtcod.console_print_ex(panel_v, 1, 16, libtcod.BKGND_NONE, libtcod.LEFT, 'floor  ['+str(dungeon_level)+']')
    libtcod.console_print_ex(panel_v, 1, 17, libtcod.BKGND_NONE, libtcod.LEFT, 'compass['+player.fighter.orientation+']')
    libtcod.console_print_ex(panel_v, 1, 18, libtcod.BKGND_NONE, libtcod.LEFT, '$['+str(player.fighter.purse)+']')

    y = 20

    rhand = get_equipped_in_slot('right hand')
    if rhand is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'r[{}]'.format(rhand.owner.name.split(' ')[1]))
        y+=1
    lhand = get_equipped_in_slot('left hand')
    if lhand is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'l[{}]'.format(lhand.owner.name.split(' ')[1]))
        y+=1
    head = get_equipped_in_slot('head')
    if head is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'h[{}]'.format(head.owner.name.split(' ')[0]))
        y+=1
    neck = get_equipped_in_slot('neck')
    if neck is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'n[{}]'.format(neck.owner.name.split(' ')[1]))
        y+=1
    back = get_equipped_in_slot('back')
    if back is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'b[{}]'.format(back.owner.name.split(' ')[1]))
        y+=1
    body = get_equipped_in_slot('body')
    if body is not None:
        libtcod.console_print_ex(panel_v, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, 'b[{}]'.format(body.owner.name.split(' ')[1]))
    
    #libtcod.console_print_ex(panel_v, 1, 17, libtcod.BKGND_NONE, libtcod.LEFT, 'lHand[{}]'.format(get_equipped_in_slot('right hand'))
 
    #display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names(dot_x,dot_y))
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    libtcod.console_blit(panel_v, 0, 0, SCREEN_WIDTH - CAMERA_WIDTH, SCREEN_HEIGHT - PANEL_HEIGHT, 0, CAMERA_WIDTH, 0)
 
def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )

def player_move_or_attack(dx, dy, move=True,force=False):
    global fov_recompute, notifications
    
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
    if x >= MAP_WIDTH - 1:
        dx = -1
    elif x < 0:
        dx = 1
    if y >= MAP_HEIGHT - 1:
        dy = -1
    elif y < 0:
        dy = 1

    #try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            if object.fighter.state not in ['friendly','wandering'] or force:
                target = object
                break
            elif object.fighter.state in ['friendly','wandering']:
                st = random.choice(['yes?','watch it!','i like you too?','uuh, touch me','keep rubbing'])
                object.fighter.talk(st)

    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
        return True
    
    if move:
        player.move(dx, dy)
        fov_recompute = True

    return False
  
def menu(header, options, width,offset=0):
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
 
    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_set_default_background(window, libtcod.black)

    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_SET, libtcod.LEFT, header)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2 + offset
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 1.0)
 
    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)
 
    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None
 
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            text = item.name
            #show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)
 
    index = arrow_menu(header, options, INVENTORY_WIDTH,0,4,1)
    #index = menu(header, options, INVENTORY_WIDTH)
    render_all()
    #if an item was chosen, return it
    if index is -1 or len(inventory) == 0: return None
    return inventory[index].item
 
def msgbox(text, width=40):
    menu(text, [], width,offset=-3)  #use menu() as a sort of "message box"
 
def handle_keys():
    global key,isRealTime, mouse, oldxx,oldyy,oldPxx,oldPyy,notifications, inventory
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    if key.vk == libtcod.KEY_ESCAPE:
        if arrow_menu('really quit?',['YES','nah'],15,30,14) == 0:
            opt = -1
            return 'exit'
        else:
            return 'nop'

    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8 or chr(key.c) == 'w':
            player_move_or_attack(0, -1)
            player.fighter.orientation = NORTH
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2 or chr(key.c) == 's':
            player_move_or_attack(0, 1)
            player.fighter.orientation = SOUTH
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4 or chr(key.c) == 'a':
            player_move_or_attack(-1, 0)
            player.fighter.orientation = WEST
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6 or chr(key.c) == 'd':
            player_move_or_attack(1, 0)
            player.fighter.orientation = EAST
        elif key.vk == libtcod.KEY_KP5 or chr(key.c) == ' ':
            pass  #do nothing ie wait for the monster to come to you
        else:
            #test for other keys
            key_char = chr(key.c)
 
            if key_char in ['e','E'] or key.vk == libtcod.KEY_KP7:
                #pick up an item
                _x, _y = player.fighter.getTargetTile()
                for object in objects:  #look for an item in the player's tile
                    if object.x == player.x and object.y == player.y:
                        if object.item:
                            object.item.pick_up()
                            break
                        elif object.name == 'money':
                            player.fighter.purse += 1 
                            objects.remove(object)
                        #elif player.x == stairs.x and player.y == stairs.y:
                        #    next_level(dungeon_level,CHAR_MOUNTAIN,up=False)
                        elif map[player.x][player.y].terrain in ['>','<',CHAR_STAIRS]:
                            t = CHAR_MOUNTAIN
                            for x in range(player.x-2,player.x+2):
                                for y in range(player.y-2,player.y+2):
                                    if map[x][y].terrain not in [CHAR_GRASS,CHAR_LONG_GRASS,CHAR_TALL_GRASS,CHAR_DIRT,'<','>']:
                                        t = map[x][y].terrain
                                        break     
                            if map[player.x][player.y].terrain == '>':
                                if dungeon_level > 0:
                                    nm = dungeon_name
                                else:
                                    nm = get_dungeon_name(player.x,player.y)
                                next_level(dungeon_level,up=True,name=nm)
                            else:
                                if dungeon_level > 0:
                                    nm = dungeon_name
                                else:
                                    nm = get_dungeon_name(player.x,player.y)
                                next_level(dungeon_level,t,up=False,name=nm)
                                key.vk == libtcod.KEY_KP5
                            break
                    elif object.x == _x and object.y == _y:
                        if object.fighter:
                            if object.name.split()[0] in ['blacksmith','nurse','leathersmith','lumberjack','old','wise']:
                                object.ai.sell_stuff()
                            else:
                                object.fighter.talk(dialogs.getValue(object.char, object.fighter.state))
                        elif object.item:
                            object.item.pick_up()
                            break
                        elif object.name == 'money':
                            player.fighter.purse += 1 
                            objects.remove(object)
            if key_char in ['c','C'] or key.vk == libtcod.KEY_KP3 or key.vk == libtcod.KEY_ESCAPE:
                return in_game_menu()
            if key_char in ['q','Q'] or key.vk == libtcod.KEY_KP1:
                curr_weap = get_equipped_in_slot('right hand')
                weap_2 = get_equipped_in_slot('left hand')
                throwable = ['spear','bow','boomerang','stick','rock']
                if curr_weap is None or curr_weap is not None and curr_weap.owner.name.split(' ')[1] not in throwable:
                    if weap_2 is not None and weap_2.owner.name.split(' ')[1] in throwable:
                        curr_weap = weap_2
                if curr_weap is not None and curr_weap.owner.name.split(' ')[1] in throwable:
                    _boomerang_ = (curr_weap.owner.name.split(' ')[1] in ['boomerang'])
                    fs = []
                    for o in objects:
                        if (o.x == player.x or o.y == player.y) and o.fighter:
                             fs.append(o)
                    #fire in the hole!
                    _x = player.x
                    _y = player.y
                    _break = False

                    dmg = curr_weap.power_bonus 
                    if not _boomerang_:
                        dmg+=1
                    fit =  None
                    endx = 0
                    endy = 0 
                    if player.fighter.orientation == NORTH:
                        for _y in range(player.y-1,0, -1):
                            if map[player.x][_y].blocked or _break:
                                endx = _x
                                endy = _y+1
                                break
                            for f in fs:
                                if f.x == _x and f.y == _y:
                                    fit = f
                                    endx = _x
                                    endy = _y+1
                                    _break = True
                                    break
                            if _boomerang_:
                                notifications.append(Notif('(',2,player.x,_y))
                            else:
                                notifications.append(Notif('|',3,player.x,_y))
                        if _boomerang_:
                            for _y in range(endy,player.y):
                                notifications.append(Notif(')',3,_x,player.y))

                    elif player.fighter.orientation == EAST:
                        for _x in range(player.x+1, MAP_WIDTH):
                            if map[_x][player.y].blocked or _break:
                                endx = _x-1
                                endy = _y
                                break
                            for f in fs:
                                if f.x == _x and f.y == _y:
                                    fit = f
                                    endx = _x-1
                                    endy = _y
                                    _break = True
                                    break
                            if _boomerang_:
                                notifications.append(Notif('(',2,_x,player.y))
                            else:
                                notifications.append(Notif('-',3,_x,player.y))
                        if _boomerang_:
                            for _x in range(endx,player.x,-1):
                                notifications.append(Notif(')',3,_x,player.y))
                    elif player.fighter.orientation == SOUTH:
                        for _y in range(player.y+1, MAP_HEIGHT):
                            if map[player.x][_y].blocked or _break:
                                endx = _x
                                endy = _y-1
                                break
                            for f in fs:
                                if f.x == _x and f.y == _y:
                                    fit = f
                                    endx = _x
                                    endy = _y-1
                                    _break = True
                                    break
                            if _boomerang_:
                                notifications.append(Notif(')',2,player.x,_y))
                            else:
                                notifications.append(Notif('|',3,player.x,_y))

                        if _boomerang_:
                            for _y in range(endy,player.y,-1):
                                notifications.append(Notif('(',3,_x,player.y))
                    elif player.fighter.orientation == WEST:
                        for _x in range(player.x-1,0,-1):
                            if map[_x][player.y].blocked or _break:
                                endx = _x+1
                                endy = _y
                                break

                            for f in fs:
                                if f.x == _x and f.y == _y:
                                    fit = f
                                    endx = _x+1
                                    endy = _y
                                    _break = True
                                    break
                            if _boomerang_:
                                notifications.append(Notif(')',2,_x,player.y))
                            else:
                                notifications.append(Notif('-',3,_x,player.y))
                        if _boomerang_:
                            for _x in range(player.x,endx-1):
                                notifications.append(Notif('(',3,_x,player.y))
                    if not fit is None:
                        notifications.append(Notif('*',5,_x,_y))
                        if curr_weap.owner.name.split(' ')[1] in ['spear','stick','rock']:
                            message('you threw your {} at {} and dealt {}'.format(curr_weap.owner.name,f.name,dmg))
                            i_name = curr_weap.owner.name
                            for it in inventory:
                                if it.name == i_name:
                                    it.item.drop(endx,endy)
                                    break;
                        else:
                            message('you shot your {} at {} and dealt {}'.format(curr_weap.owner.name,f.name,dmg))
                        fit.fighter.take_damage(dmg)
                    else:
                        message('you threw your {} at nothing'.format(curr_weap.owner.name))
                        if curr_weap.owner.name.split(' ')[1] in ['spear','stick','rock']:
                            i_name = curr_weap.owner.name
                            for it in inventory:
                                if it.name == i_name:
                                    it.item.drop(endx,endy)
                                    break;

            if key_char in ['f','F'] or key.vk == libtcod.KEY_KP9:
                curr_weap = get_equipped_in_slot('right hand')
                weap_2 = get_equipped_in_slot('left hand')
                if curr_weap is not None and curr_weap.owner.name.split(' ')[1] == 'bag':
                    orien = player.fighter.orientation
                    strangle = False
                    for obj in objects:
                        tx,ty = player.fighter.getTargetTile()
                        if obj.fighter and obj.x == tx and obj.y == ty:
                            f = obj
                            strangle = True
                            dmg = player.fighter.power + 1
                            break
                    if not strangle:
                        return 'nop'
                    if orien == EAST:
                        if player_move_or_attack(1, 0,False,True):
                            message('you strangle {} with your {} and dealt {}'.format(f.name,curr_weap.owner.name,dmg))
                    elif orien == WEST:
                        if player_move_or_attack(-1, 0,False,True):
                            message('you strangle {} with your {} and dealt {}'.format(f.name,curr_weap.owner.name,dmg))
                    elif orien == NORTH:
                        if player_move_or_attack(0, -1,False,True):
                            message('you strangle {} with your {} and dealt {}'.format(f.name,curr_weap.owner.name,dmg))
                    elif orien == SOUTH:
                        if player_move_or_attack(0, 1,False,True):
                            message('you strangle {} with your {} and dealt {}'.format(f.name,curr_weap.owner.name,dmg))
                swingable = ['sword','axe','stick']
                pokable = ['spear','whip']
                if curr_weap is None and weap_2 is not None or (curr_weap is not None and curr_weap.owner.name.split(' ')[1] not in swingable and weap_2 is not None): 
                    if weap_2.owner.name.split(' ')[1] in swingable:
                        curr_weap = weap_2
                if curr_weap is not None and curr_weap.owner.name.split(' ')[1] in swingable:
                    if player.fighter.orientation == EAST:
                        notifications.append(Notif('/',2,player.x+1,player.y-1))
                        notifications.append(Notif('-',3,player.x+1,player.y))
                        notifications.append(Notif('\\',4,player.x+1,player.y+1))
                        if not player_move_or_attack(1, 0,False,True) and not player_move_or_attack(1, -1,False,True) and not player_move_or_attack(1, 1,False,True):
                            swing_sword(player.x+1,player.y-1)
                            swing_sword(player.x+1,player.y+1)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == NORTH:
                        notifications.append(Notif('\\',2,player.x-1,player.y-1))
                        notifications.append(Notif('|',3,player.x,player.y-1))
                        notifications.append(Notif('/',4,player.x+1,player.y-1))
                        if not player_move_or_attack(1, -1,False,True) and not player_move_or_attack(-1, -1,False,True) and not player_move_or_attack(0, -1,False,True):
                            swing_sword(player.x-1,player.y-1)
                            swing_sword(player.x+1,player.y-1)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == WEST:
                        notifications.append(Notif('\\',2,player.x-1,player.y-1))
                        notifications.append(Notif('-',3,player.x-1,player.y))
                        notifications.append(Notif('/',4,player.x-1,player.y+1))
                        if not player_move_or_attack(-1, 0,False,True) and not player_move_or_attack(-1, -1,False,True) and not player_move_or_attack(-1, 1,False,True):  
                            swing_sword(player.x-1,player.y-1)
                            swing_sword(player.x-1,player.y+1)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == SOUTH:
                        notifications.append(Notif('/',2,player.x-1,player.y+1))
                        notifications.append(Notif('|',3,player.x,player.y+1))
                        notifications.append(Notif('\\',4,player.x+1,player.y+1))
                        if not player_move_or_attack(0, 1,False,True) and not player_move_or_attack(+1, 1,False,True) and not player_move_or_attack(-1, 1,False,True):
                            swing_sword(player.x-1,player.y+1)
                            swing_sword(player.x+1,player.y+1)
                            return 'attack'
                        else:
                            return 'nop'
                elif (curr_weap is not None and curr_weap.owner.name.split(' ')[1] in pokable and weap_2 is not None and weap_2.owner.name.split()[1] in swingable) or (curr_weap is None and weap_2 is not None and weap_2.owner.name.split(' ')[1] in pokable):
                    if player.fighter.orientation == EAST:
                        notifications.append(Notif('-',3,player.x+1,player.y))
                        if not player_move_or_attack(1, 0,False,True):
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == NORTH:
                        notifications.append(Notif('|',3,player.x,player.y-1))
                        if not player_move_or_attack(1, -1,False,True):
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == WEST:
                        notifications.append(Notif('-',3,player.x-1,player.y))
                        if not player_move_or_attack(-1, 0,False,True):  
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == SOUTH:
                        notifications.append(Notif('|',3,player.x,player.y+1))
                        if not player_move_or_attack(0, 1,False,True):
                            return 'attack'
                        else:
                            return 'nop'
                else:
                    if player.fighter.orientation == EAST:
                        if not player_move_or_attack(1, 0,False,True):
                            swing_sword(player.x+1,player.y)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == NORTH:
                        if not player_move_or_attack(0, -1,False,True):
                            swing_sword(player.x,player.y-1)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == WEST:
                        if not player_move_or_attack(-1, 0,False,True): 
                            swing_sword(player.x-1,player.y)
                            return 'attack'
                        else:
                            return 'nop'
                    elif player.fighter.orientation == SOUTH:
                        if not player_move_or_attack(0, 1,False,True):
                            swing_sword(player.x,player.y+1)
                            return 'attack'
                        else:
                            return 'nop'

            return 'didnt-take-turn'
    else:
        if key.vk == libtcod.KEY_ESCAPE:
            return

def in_game_menu():
    opt = 5
    while opt >= 0:
        render_all()
        opt = arrow_menu('--game menu--',['inventory','drop stuff','char info','back to game','quit'],15,0,-1,-3)
        if opt == 0:
            chosen_item = inventory_menu('use / equip \n select with action, cancel with menu.\n')
            if chosen_item is not None:
                chosen_item.use()
            continue
        elif opt == 1:
            chosen_item = inventory_menu('drop \n select with action, cancel with menu.\n')
            if chosen_item is not None:
                chosen_item.drop()
                continue
        elif opt == 2:
            msgbox('the koboldicider\n\nMaximum HP: ' + str(player.fighter.max_hp) + '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
        elif opt == 3:
            return 'nop'
        elif opt == 4:
            if arrow_menu('really quit?',['YES','nah'],15,30,14) == 0:
                opt = -1
                return 'exit'
            else:
                continue


def end_screen(player):
    rhand = get_equipped_in_slot('right hand')
    lhand = get_equipped_in_slot('left hand')
    head = get_equipped_in_slot('head')
    neck = get_equipped_in_slot('neck')
    body = get_equipped_in_slot('body')
    
    title = ''
    equip = 'nothing'
    if body is not None and body.owner.name == 'metal armour' and head is not None and head.owner.name == 'metal elm':
        title = 'iron-man'
    if body is None and head is None:
        title = 'nudist'
    elif body is not None and body.owner.name == 'colorful poncho' and head is not None and head.owner.name == 'sombrero hat':
        title = 'el mariachi'
    elif body is not None and body.owner.name == 'hawaiian shirt' and head is not None and head.owner.name == 'flower hat':
        title = 'hawai\'i maoli'
    elif body is not None and body.owner.name == 'still suit' and (rhand is not None and rhand.owner.name == 'crys knife' or lhand is not None and lhand.owner.name == 'crys knife'):
        title = 'fremen'
    elif body is not None and body.owner.name == 'hawaiian shirt' and (rhand is not None and rhand.owner.name == 'pocket knife' or lhand is not None and lhand.owner.name == 'pocket knife'):
        title = 'macgyver'
        equip = 'a paper clip'
    elif body is not None and body.owner.name == 'leather armour' and head is not None and head.owner.name == 'leather hat' and (rhand is not None and rhand.owner.name == 'leather whip' or lhand is not None and lhand.owner.name == 'leather whip'):
        title = 'kinky'
    elif head is not None and head.owner.name == 'cowboy hat' and (rhand is not None and rhand.owner.name == 'leather whip' or lhand is not None and lhand.owner.name == 'leather whip'):
        title = 'indiana jones'
    elif head is not None and head.owner.name == 'bandanna hat' and (rhand is not None and rhand.owner.name.split()[1] == 'knife' or lhand is not None and lhand.owner.name.split()[1] == 'knife') and body is not None and body.owner.name == 'sleeveless shirt':
        title = 'rambo'
        equip = 'bad-assery'

    if (rhand is not None and rhand.owner.name.split()[1] == 'rock' and lhand is not None and lhand.owner.name.split()[1] == 'stick') or (rhand is not None and rhand.owner.name.split()[1] =='stick' and lhand is not None and lhand.owner.name.split()[1] == 'rock'):
        equip = 'sticks & stones'
        if title != '':
            title += ', bone breaker'
        else:
            title += 'bone breaker'
    elif rhand is None and lhand is None:
        equip = 'only your fists'


    death_msg = 'good bye, {}, the koboldicider. you killed [{}] kobolds, '.format(title,kobolds_killed)
    if equip == 'nothing':
        equip = ''
        if rhand is not None:
            equip += 'on your right hand [{}],'.format(rhand.owner.name)
        if lhand is not None:
            equip += '\n on your left hand [{}],'.format(lhand.owner.name)
        if head is not None:
            equip += 'on your head [{}],'.format(head.owner.name)
        if neck is not None:
            equip += 'on your neck [{}],'.format(neck.owner.name)
        if body is not None:
            equip += 'on your body [{}],'.format(body.owner.name)
#    if rhand is None and lhand is None and head is None and body is None and neck is None:
#        death_msg += 'nothing but vengeance on your soul.'
#    else:
#        death_msg += 'and nothing but vengeance on your soul.'
    death_msg += 'had [{}] money and had {} equipped.'.format(player.fighter.purse, equip)
    message(death_msg)
    render_all()
    msgbox(death_msg)
    print ' [{}]'.format(death_msg)


def player_death(player):
    #the game ended!
    global game_state
    message('You died!', libtcod.red)
    end_screen(player)
    msgbox(' game over ')
    game_state = 'dead'
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
    render_all()
    libtcod.console_wait_for_keypress(True)
    return 'exit'



def dragon_death(monster):
    message('oh, wow, you won')
    message('the dragon lies dead at your feet!')

    render_all()
    msgbox("congratulations!")
    msgbox("you won!!")
    msgbox("you have become kobolicider, destroyer of kobolds.")
    msgbox(' you killed [{}] kobolds!'.format(kobolds_killed))

    return 'exit'


def monster_death(monster):
    global objects, kobolds_killed
    if monster.name.split(' ')[0] in ['kobold'] and monster.name.split(' ')[1] not in ['champion']:
        kobolds_killed+=1
        _drop_ = random.randint(0,30)
        if _drop_ <= 3:
            addItem('wooden spear',monster.x,monster.y)
        elif _drop_ <=5:
            addItem('short sword',monster.x,monster.y)
        elif _drop_ <= 7:
            addItem('leather armour',monster.x,monster.y)
        elif _drop_ <= 10:
            addItem('hat', monster.x,monster.y)
        elif _drop_ <= 20:
            objects.append(Object(monster.x, monster.y, '$', 'money', libtcod.yellow, always_visible=True))
    elif monster.name in ['kobold champion']:
        addItem('metal armour',monster.x, monster.y)
        addItem('elm',monster.x, monster.y)
        addItem('long sword',monster.x,monster.y)
    elif monster.name in ['anangu hunter']:
        if random.randint(1,3) == 3:
            addItem('wooden boomerang',monster.x, monster.y)
        else:
            addItem('wooden spear',monster.x,monster.y)
    elif monster.name.split()[0] in ['shai-hulud']:
        if monster.name.split()[1] == 'head':
            Object(monster.x, monster.y, '%', 'dead freman', libtcod.red, blocks=False, ai=DeadBody(monster))
            addItem('still suit',monster.x, monster.y)
            addItem('crysknife',monster.x, monster.y)
        else:
            for obj in objects:
                if obj.name == 'shai-hulud head':
                   obj.fighter.defense -= 1
                   obj.fighter.hp -= 2
    elif monster.name.split()[0] in ['dragon'] and not monster.name.split()[1] in ['head']:
        for obj in objects:
            if obj.name == 'dragon head':
               obj.fighter.defense -= 1
               obj.fighter.hp -= 1
        

    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    #message('+' + str(monster.fighter.xp) + 'xp.', libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = DeadBody(monster)

    monster.name = 'dead ' + monster.name.split()[0]
    #add new object of the tipe "ammo"
    monster.send_to_back()

def wolf_death(monster):
    #teh wofl howls! 
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = DeadBody(monster)
    for obj in objects:
        if obj.name == monster.name:
            obj.move_towards(player.x, player.y)
            if obj.fighter:
                obj.fighter.set_state('aggressive')

    message('the {} howls, beckonign his friends, while he dies'.format(monster.name))
    monster.name = 'dead ' + monster.name
    #add new object of the tipe "ammo"
    monster.send_to_back()

def monster_death_no_loot(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    if monster.name == 'desert worm':
        if random.randint(1,99) >= 77:
            addShaiHulud(monster.x,monster.y)
        else:
            addMonster('desert worm', monster.x-3, monster.y-3)
            addMonster('desert worm', monster.x-2, monster.y-3)
            addMonster('desert worm', monster.x-3, monster.y-1)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = DeadBody(monster)

    monster.name = 'dead ' + monster.name
    #add new object of the tipe "ammo"
    monster.send_to_back()
   
def target_tile(max_range=None):
    global key, mouse
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()
 
        (x, y) = (mouse.cx, mouse.cy)
 
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None)  #cancel if the player right-clicked or pressed Escape
 
        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)
 
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None
 
        #return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj
 
def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range
 
    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy

def save_floor(floorname='world'):

    print "saving [{}]".format(floorname)    

    file = shelve.open('./levels/'+floorname, 'n')
    file['map'] = map
    file['objects'] = objects
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['dungeon_level'] = dungeon_level
    file['player_pos'] = (player.x,player.y)
    file.close()
    if floorname == 'world':
        file['dung_names'] = dung_list


def load_floor(floorname='world'):
    global map, objects, stairs, dungeon_level,player, dung_list
    for ob in objects:
        if ob.name == "dot":
            new_obj = ob
            break

    print "loading [{}]".format(floorname)
    file = shelve.open('./levels/'+floorname)
    #file = shelve.open('/levels/'+floorname, 'r')

    map = file['map']
    objects = file['objects']
    #stairs = objects[file['stairs_index']]
    dungeon_level = file['dungeon_level']
    player.x, player.y = file['player_pos']

    if floorname == 'world':
        dung_list = file['dung_names'] 

    for ob in objects:
        if ob.name in ["dot","koboldicider"]:
            objects.remove(ob)
            break;
    objects.append(new_obj)
    objects.append(player)

def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    #file['player_index'] = objects.index(player)  #index of player in objects list
    #file['stairs_index'] = objects.index(stairs)  #same for the stairs
    file['inventory'] = inventory
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    file['dungeon_level'] = dungeon_level
    file.close()
 
def load_game():
    #open the previously saved shelve and load the game data
    global map, objects, player, stairs, inventory, game_msgs, game_state, dungeon_level,isRealTime, game_animations, dialogs
 
    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    #player = objects[file['player_index']]  #get index of player in objects list and access it
    #stairs = objects[file['stairs_index']]  #same for the stairs
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    dungeon_level = file['dungeon_level']
    file.close()
 
    isRealTime = False
    initialize_fov()
    game_animations = []
    dialogs = Dialogs()
    dialogs.loadFromFile()

def new_game():
    global player, inventory, game_msgs, game_state, dungeon_level, isRealTime, game_animations, objects, notifications, dungeon_name, kobolds_killed
 
    #create object representing the player
    fighter_component = PlayerFighter(hp=5, defense=5, power=2, xp=0, death_function=player_death)
    player = Object(0, 0, '@', 'koboldicider', libtcod.white, blocks=True, fighter=fighter_component)
    clothing = addItem('shirt',-1,-1,False)
    
    player.level = 1
    isRealTime = False
 
    #generate map (at this point it's not drawn to the screen)
    dungeon_level = 0
    dungeon_name = "world -----"
    #make_bsp() #commented make map
    objects = []
    make_world_map(6,True)
    initialize_fov()
    kobolds_killed = 0
    game_state = 'playing'
    inventory = []
    inventory.append(clothing)
    game_animations = []
    notifications = []


    #create the list of game messages and their colors, starts empty
    game_msgs = []
    save_game()

    addMonster('kobold low_level',player.x,player.y+5,'neutral')
    dogCorpse = Object(player.x,player.y+6,'%','remains of Fido', libtcod.dark_red, blocks=False)
    objects.append(dogCorpse)

    notifications.append(Notif('nham, tasty dog!',5,player.x+1,player.y+4))
    clothing.item.use()

    message('As you return from you errands, you find your house burning and a kobold eating your dog')
    message('the wise man in the forest will know what to do.')
    message('but first..')
 
def next_level(dl,terrain=CHAR_MOUNTAIN,up=False, name='world -----'):
    global dungeon_level, dungeon_name
    #advance to the next level
    dungeon_name = name
    objects.remove(player)
    print "going places! dl[{}] in [{}]".format(dungeon_level,name)
    if not up:
        if dl == 0:
            save_floor('world.dng')
            dungeon_name = name
            dungeon_level+=1
            try:
                load_floor('{}_{}F.dng'.format(name,dungeon_level))
            except:
                make_map(terrain,name=name)  #create a fresh new level!
            initialize_fov()
        elif dl < 3:
            save_floor('{}_{}F.dng'.format(name,dungeon_level))
            dungeon_level+=1
            make_map(CHAR_MOUNTAIN,name=name)  #create a fresh new level!
            initialize_fov()
        elif dl < 4:
            save_floor('{}_{}F.dng'.format(name,dungeon_level))
            make_map('|',name)
            dungeon_level+=1
            initialize_fov()
        elif dl < 5:
            save_floor('{}_{}F.dng'.format(name,dungeon_level))
            dungeon_level+=1
            lair = True
            make_customgenericmap('#')
            add_dragon()
            initialize_fov()
        else:
            load_floor('world.dng')
            initialize_fov()
            dungeon_level = 0
            message('oh, wow, you won')
    else:
        print "going up! dl[{}]".format(dungeon_level)

        if dl == 1:
            save_floor('{}_{}F.dng'.format(name,1))
            load_floor('world.dng')
            initialize_fov()
            dungeon_level = 0
        else:
            dungeon_level -= 1
            load_floor('{}_{}F.dng'.format(name,dungeon_level))
            initialize_fov()
    save_game()

    initialize_fov()
    if dungeon_level == 0:
        TORCH_RADIUS = 35
    else:
        TORCH_RADIUS = 12

def initialize_fov():
    global fov_recompute, fov_map,oldxx,oldyy
    oldxx = oldyy = 0
    fov_recompute = True
 
    #create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
 
    libtcod.console_clear(con)  #unexplored areas start black (which is the default background color)
 
def play_game():
    global key, mouse,isRealTime,game_animations,notifications, camera_x, camera_y, dialogs

    dot = Object(0,1,'.','dot', libtcod.white, blocks=False)
    objects.append(dot)

    (camera_x, camera_y) = (0, 0)
    dialogs = Dialogs()
    dialogs.loadFromFile()
    player_action = None
    #notifications = []
    mouse = libtcod.Mouse()
    key = libtcod.Key()
    #main loop
    while not libtcod.console_is_window_closed():
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        #render the screen
        render_all()
 
        libtcod.console_flush()
  
        #erase all objects at their old locations, before they move
        for object in objects:
            object.clear()
 
        #handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            end_screen(player)
            save_game()
            return;

        _x = player.x
        _oldx = dot.x 
        _oldy = dot.y
        _y = player.y 
        dot.x,dot.y = player.fighter.getTargetTile()
        if (dot.x != _oldx or dot.y != _oldy):
            initialize_fov()

        for obj in objects:
            if obj.x == player.x and obj.y == player.y:
                if obj.name in ['money']:
                    objects.remove(obj)
                    player.fighter.purse += 1
                    break

        if map[player.x][player.y].terrain == CHAR_TALL_GRASS:
           map[player.x][player.y] = Tile(False,terrain=CHAR_LONG_GRASS)
           drop = random.randint(1,420)
           if drop >= 418:
                addMonster('worm', _x,_y)
           elif drop >= 410:
                objects.append(Object(player.x, player.y, '$', 'money', libtcod.yellow, always_visible=True))
           initialize_fov()
           continue

        if player_action == 'attack':
            swing_sword(_x,_y)

        #let monsters take their turn
        if isRealTime:
            if game_state == 'playing':
               for object in objects:
                if object.ai:
                    if object.wait > 0:  #don't take a turn yet if still waiting
                        object.wait -= 1
                    else:
                        object.ai.take_turn()
        else:
            if game_state == 'playing' and player_action != 'didnt-take-turn':
                for object in objects:
                    if object.ai:
                        if object.wait > 0:  #don't take a turn yet if still waiting
                            object.wait -= 1
                        else:
                            object.ai.take_turn()

        if game_state == 'dead':
            return

def swing_sword(_x,_y):
    global objects
    if map[_x][_y].terrain in [CHAR_LONG_GRASS,CHAR_TALL_GRASS]:
        if map[_x][_y].terrain == CHAR_LONG_GRASS:
           map[_x][_y] = Tile(False,terrain=CHAR_GRASS)
        else:
           map[_x][_y] = Tile(False,terrain=CHAR_LONG_GRASS)
           
        drop = random.randint(1,42)
        if drop >= 37:
           objects.append(Object(_x, _y, '$', 'money', libtcod.yellow, always_visible=True))
        elif drop >= 33:
           addMonster('worm',_x,_y)
           initialize_fov()

    elif map[_x][_y].terrain in [CHAR_FOREST]:
        drop = random.randint(1,42)
        if drop >= 37:
           addItem('wooden stick',_x,_y)
        



def main_menu():
    libtcod.console_flush()
    libtcod.console_set_default_background(0, libtcod.black)
    libtcod.console_clear(0)

    img = libtcod.image_load('menu_background.png')
    libtcod.console_map_ascii_code_to_font('@', 2, 0)
    libtcod.console_map_ascii_code_to_font('O', 1, 0)
    #libtcod.console_map_ascii_code_to_font('+', 3, 0)
    libtcod.console_map_ascii_code_to_font('T', 6, 0)

    libtcod.image_blit_2x(img, 0, 0, 0)
    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
 
        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.white)
 
        #show options and wait for the player's choice
        #_continue = arrow_menu('continue ?',['   yes','    no'],12,0,12,12)
        #choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 25,10)
        libtcod.console_print_ex(0, 60, 10, libtcod.BKGND_NONE, libtcod.RIGHT, 'Koboldicider <--------')          
        choice = arrow_menu('welcome, koboldicider',['into the game!', 'please help?', 'i wanna quit.'],40,0,20,15)

 
        if choice == 0:  #new game
            new_game()
            play_game()
        if choice == 1:  #show help screen
            libtcod.console_set_default_background(0, libtcod.black)

            libtcod.console_print_ex(0, 60, 10, libtcod.BKGND_SET, libtcod.RIGHT, 'Koboldicider <--------')           
            libtcod.console_print_ex(0, 60, 12, libtcod.BKGND_SET, libtcod.RIGHT, 'move with [w,a,s,d] or kp[8,4,6,2] or [arrow keys]')         
            libtcod.console_print_ex(0, 60, 13, libtcod.BKGND_SET, libtcod.RIGHT, 'attack the square you are facing        [f or kp9]')         
            libtcod.console_print_ex(0, 60, 14, libtcod.BKGND_SET, libtcod.RIGHT, 'use, pick up, talk, go up/down          [e or kp7]')         
            libtcod.console_print_ex(0, 60, 15, libtcod.BKGND_SET, libtcod.RIGHT, 'throw a stick, spear or boomerang       [q or kp1]')         
            libtcod.console_print_ex(0, 60, 16, libtcod.BKGND_SET, libtcod.RIGHT, 'open in-game menu                       [c or kp3]')         
            libtcod.console_print_ex(0, 60, 17, libtcod.BKGND_SET, libtcod.RIGHT, 'wait a turn                         [space or kp5]')         
            libtcod.console_print_ex(0, 60, 18, libtcod.BKGND_SET, libtcod.RIGHT, '                     ----')          
        elif choice == 2:  #quit
            return 

 
libtcod.console_set_custom_font('16x16_sm_ascii.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, '7DKoboldicide', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
panel_v = libtcod.console_new(SCREEN_WIDTH - CAMERA_WIDTH, SCREEN_HEIGHT - PANEL_HEIGHT)


 
try:
    os.mkdir('levels')
except:
    shutil.rmtree('levels')
    os.mkdir('levels')
main_menu()
shutil.rmtree('levels')