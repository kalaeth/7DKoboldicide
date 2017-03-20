#!/usr/bin/python
#
# libtcod python tutorial
#
 
import libtcodpy as libtcod
import math
import textwrap
import shelve
import random
from time import sleep
 
#actual size of the window
SCREEN_WIDTH = 60
SCREEN_HEIGHT = 30
 
#size of the map
VIEW_WIDTH = 50
VIEW_HEIGHT = 16

#size of the map portion shown on-screen
CAMERA_WIDTH = 50
CAMERA_HEIGHT = 22
MAP_WIDTH = 100
MAP_HEIGHT = 50
DEPTH = 10
MIN_SIZE = 15
FULL_ROOMS = False
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 11
PANEL_HEIGHT = 8
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 1
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

 
#experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

#combat speeds
PLAYER_SPEED = 1
DEFAULT_SPEED = 1
DEFAULT_ATTACK_SPEED = 1
 
FOV_ALGO = 1  #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 80
 
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
CHAR_MOUNTAIN = '#'
CHAR_STAIRS = '>'

class Dialog:
    def __init__(self,_char,_level,_value):
        self.characther = _char
        self.level = _level
        self.value = _value

    def _set_value(self, _value):
        self.value = _value

    def _get_value(self):
        return self.value

class Dialogs:
    def __init__(self):
        self.list = [];

    def get(self,_char, _level):
        rt_sentence = Dialog('X',0,'Leave me alone!')
        for sentence in self.list:
            if sentence.character == _char and sentence.level == _level:
                return sentence
            elif sentence.characther == _char and sentence.level > _level:
                rt_sentence = sentence 
        return rt_sentence

    def getValue(self,_char, _level):
        return self.get(_char,_level)._get_value()

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
                dd = _d.split(' ')
                if dd[0] == 'END':
                    break
                else:
                    self.addSetting(dd[0],dd[1],dd[2]);
 
class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None, terrain=CHAR_GRASS):
        self.blocked = blocked
 
        #all tiles start unexplored
        self.explored = False
    
        #by default, if a tile is blocked, it also blocks sight

        self.terrain = terrain
        if self.terrain in [CHAR_LAKE,CHAR_FOREST,CHAR_MOUNTAIN]:
        	self.blocked = True
        	self.block_sight = False
        elif self.terrain in [CHAR_DIRT, CHAR_GRASS, CHAR_ROAD , CHAR_LONG_GRASS, CHAR_STAIRS]:
        	self.blocked = False
        	self.block_sight = False
        elif self.terrain in [CHAR_TALL_GRASS]:
        	self.blocked = False
        	self.block_sight = True
        else:
	        if block_sight is None: block_sight = blocked
	        self.block_sight = block_sight

        self.color = libtcod.green
        if self.terrain == CHAR_MOUNTAIN or self.terrain == CHAR_DIRT:
            self.color = libtcod.light_sepia
        elif self.terrain == CHAR_LAKE:
            self.color = libtcod.blue
            self.block_sight = False
        elif self.terrain == CHAR_STAIRS:
            self.color = libtcod.light_yellow
        elif self.terrain == CHAR_TALL_GRASS:
        	self.color = libtcod.darker_green
        elif self.terrain == CHAR_LONG_GRASS:
            self.color = libtcod.dark_green

        elif self.terrain == CHAR_GRASS:
        	self.color = libtcod.green

    def _toString(self):
        return '{},{}'.format(self.terrain, self.color)

class Notif:
    
    #Notifation(x,y,time_to_live)
    def __init__(self,message,time_to_live = 50, x = 20, y = 10, color=libtcod.light_yellow):
        self.x = x
        self.message = message
        self.color= libtcod.light_yellow
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
                libtcod.console_print_ex(con, x, y, libtcod.BKGND_SCREEN,  libtcod.LEFT,self.message)

    def wipe(self,con):
        #erase the character that represents this object
        (x, y) = to_camera_coordinates(self.x, self.y)
        if x is not None:
            libtcod.console_put_char(con, x, y, ' ', libtcod.BKGND_NONE)

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
                libtcod.console_set_default_foreground(con, self.color)
                libtcod.console_put_char(con, x, y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        (x, y) = to_camera_coordinates(self.x, self.y)
        if x is not None:
            libtcod.console_put_char(con, x, y, ' ', libtcod.BKGND_NONE)

class PlayerFighter:
    #combat-related properties and methods (player).
    def __init__(self, hp, defense, power, xp, death_function=None,attack_speed=DEFAULT_ATTACK_SPEED,generation=3):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        self.ce_charge = 0
        self.attack_speed = attack_speed
        self.current_weapon = 0
        self.ammo = [20,0,0,0,0]
        self.generation = 3
        self.orientation = SOUTH
        self.purse = random.randint(0,50)

 
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
            roll_history += '[{}]'.format(roll)
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
        if self.hp > self.max_hp:
            self.hp = self.max_hp
					
    def degenerate(self):
		self.generation += 1
		
		#pick a degeneration_seed:
		if self.generation > 50:
			dgn_chance = 100
		else:
			dgn_chance = libtcod.random_get_int(0,self.generation*2,100)
		
		#if chance > 1d100, degenerates. else nothing.
		if dgn_chance >= libtcod.random_get_int(0,0,100):
			degen_type = libtcod.random_get_int(0,0,100)
			#really bad 5%
			if degen_type < 5:
				msgbox('you are horribly deformed!')
			#bad 15%
			elif degen_type < 20:
				msgbox('you are a bit deformed!')
			#somewhat bad 60%
			elif degen_type < 70:
				msgbox('you are a sligthly deformed!')
			#useless 20%
			elif degen_type < 90:
				msgbox('you are a ugly as fuck')
			#good 7%
			elif degen_type < 97:
				msgbox('Not all mutations are bad! ')
			#really good 3%
			else:
				msgbox('fuck yeah, tentacles!! ')
		else:
			msgbox('a perfect clone you are!')

class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, xp, death_function=None,attack_speed=DEFAULT_ATTACK_SPEED):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function
        self.ce_charge = 0
        self.current_weapon = 0
        self.attack_speed = attack_speed
        self.ammo = [100]
        self.purse = 0
 
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
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
 
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
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def talk(self,text):
        notifications.append(Notif(text,5,self.owner.x,self.owner.y-1))


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

            #print "moving to [{}][{}]".format(__x,__y)
            self.owner.move(__x, __y)

class BasicMonster:
        
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        ai = "{}@[{},{}]?".format(monster.name, monster.x, monster.y)
        _dist = int(monster.distance_to(player))

        #if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
        if _dist < 20:
            ai+=", I see you!"
            notifications.append(Notif('*',4,monster.x,monster.y-1))
            
            #move towards player if far away
            ai+=", _dist[{}]".format(_dist)
            if _dist > 15:
                ai+=", ?"
                notifications.append(Notif('?',4,monster.x,monster.y-1))
                self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            elif _dist > 1:
                ai+=", !"
                notifications.append(Notif('!',4,monster.x,monster.y-1,libtcod.red))
                monster.move_towards(player.x, player.y)
            #close enough, attack! (if the player is still alive.)
            else:
                ai+=", X"
                notifications.append(Notif('x',4,monster.x,monster.y-1,libtcod.light_red))
                monster.fighter.attack(player)
        else:
            ai+=", meh"
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
        #print ai

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
 
class Item:
    #an item that can be picked up and used.
    def __init__(self, use_function=None):
        self.use_function = use_function
 
    def pick_up(self):
        #add to the player's inventory and remove from the map
        inventory.append(self.owner)
        objects.remove(self.owner)
        message('You picked up a ' + self.owner.name + '!', libtcod.green)
        #special case: automatically equip, if the corresponding equipment slot is unused
        equipment = self.owner.equipment
        if equipment and get_equipped_in_slot(equipment.slot) is None:
            equipment.equip()
 
    def drop(self):
        #special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()
 
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
 
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
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus
 
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
            old_equipment.dequip()
 
        #equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
 
    def dequip(self):
        #dequip object and show a message about it
        if not self.is_equipped: return
        self.is_equipped = False
        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
 
class Weapon:
    #an object that can be shot
    def __init__(self, name, power_bonus=0, ammo=0, max_ammo=10, radius=0):
        self.name = name
        self.power_bonus = power_bonus
        #self.ammo = ammo
        self.max_ammo = max_ammo
        self.radius = radius

    #spends a shot and returns damage dealt
    def shoot(self):
        return self.power_bonus
  
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
            map[x][y] = Tile(True,terrain=CHAR_DIRT)
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
 
def place_thing(thing,_wid=-1,avoid=(0,0),has_stairs=True):
    if _wid == -1:
        _wid = MAP_WIDTH / 10
    global map, stairs
    _center = Tile(True,terrain=thing)
    startC = 1
    if thing in [CHAR_TALL_GRASS]:
    	startC += 2
    _x = random.randint(startC,MAP_WIDTH-_wid);
    _y = random.randint(startC,MAP_HEIGHT-_wid);
    while (map[_x][_y].terrain not in [CHAR_LONG_GRASS,CHAR_TALL_GRASS,CHAR_GRASS] ) and (_x,_y) != avoid :
        _x = random.randint(startC,MAP_WIDTH-_wid)
        _y = random.randint(startC,MAP_HEIGHT-_wid)
        print "x{} y{}".format(_x,_y)

    
    map[_x][_y] = _center
    s_thing =(_x,_y)
    print '{} center @[{},{}]'.format(thing,_x,_y)


    placed_entry = True
    if thing not in [CHAR_LONG_GRASS]: 
    	placed_entry = False
    for _xx in range(_x-_wid,_x+_wid):
        for _yy in range(_y-_wid,_y+_wid):
            if (abs(_xx - _x) > 1) and (abs(_yy - _y) > 1) and map[_xx][_yy].terrain == CHAR_LONG_GRASS:
                if random.randint(0,3) >= 2:
	                map[_xx][_yy] = Tile(True,terrain=thing)
                else:
	            	if not placed_entry and has_stairs:
						map[_xx][_yy] = Tile(False,terrain=CHAR_STAIRS)
						stairs = Object(_xx, _yy, '<', 'stairs', libtcod.white, always_visible=True)
						placed_entry = True
	            	elif map[_xx-1][_yy].terrain == CHAR_LONG_GRASS and map[_xx][_yy-1].terrain == CHAR_LONG_GRASS:
						map[_xx][_yy] = Tile(True,terrain=thing)	
            else:
                map[_xx][_yy] = Tile(True,terrain=thing)
    if not placed_entry and has_stairs:
        stairs = Object(_x-_wid, _y-_wid, '<', 'stairs', libtcod.white, always_visible=True)

    return s_thing


def make_world_map(grassness=20):
    global map, objects, stairs

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
    place_thing(CHAR_TALL_GRASS,int(MAP_WIDTH/3),(0,0), False)
    c = place_thing(CHAR_MOUNTAIN,-1,(0,0));
    objects.append(stairs)
    c = place_thing(CHAR_FOREST,-1, c);
    objects.append(stairs)
    c = place_thing(CHAR_LAKE,-1 ,c);
    objects.append(stairs)
    c = place_thing(CHAR_DIRT,-1 , c);
    objects.append(stairs)

def make_map(terrain=CHAR_MOUNTAIN):
    global map, objects, stairs
 
    #the list of objects with just the player
    for ob in objects:
        if ob.name == "dot":
            new_obj = [ob]
            break
    objects = new_obj

    objects.append(player)
 
    #fill map with "blocked" tiles
    map = [[ Tile(True,terrain=terrain)
             for y in range(MAP_HEIGHT) ]
           for x in range(MAP_WIDTH) ]
    print "made a map! adding {} rooms".format(MAX_ROOMS)
    rooms = []
    num_rooms = 0
 
    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
 
        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
 
        if not failed:
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
                    print "adding tunnel h"
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    print "adding tunnel v"
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
 
            #add some contents to this room, such as monsters
            place_objects(new_room)
            
 
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
 
    #create stairs at the center of the last room
    stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()  #so it's drawn below the monsters

def getMapFromFile():
    string_map = ['#######################################################'];

    portal = ['################################################################################',
        '################################################################################',
        '################################################################################',
        '################################################################################',
        '################################################################################',
        '######################################     #####################################',
        '####################################    x    ###################################',
        '###################################           ##################################',
        '##################################      _      #################################',
        '################################## |         | #################################',
        '##################################      u      #################################',
        '################################## |         | #################################',
        '##################################             #################################',
        '################################## |         | #################################',
        '##################################             #################################',
        '################################## |         | #################################',
        '##################################             #################################',
        '################################## |         | #################################',
        '##################################             #################################',
        '################################## ;         | #################################',
        '##################################             #################################',
        '######################################## #######################################',
        '######################################## #######################################',
        '######################################## #######################################',
        '######################################    i#####################################',
        '######################################  z     y#################################',
        '######################################     #####################################',
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

    for y in range(MAP_HEIGHT1):
        for x in range(MAP_WIDTH1):
            if smap[y][x] == 'x':
                new_x = x
                new_y = y
                map[x][y] = Tile(True,CHAR_DIRT)
            elif smap[y][x] == 'y':
                player.x = x
                player.y = y
            elif smap[y][x] != '#':
                map[x][y] = Tile(False,CHAR_TALL_GRASS)

    #create stairs at the center of the last room
    for ob in objects:
        if ob.name == "dot":
            new_obj = [ob]
            break
    objects = new_obj


    stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()  #so it's drawn below the monsters
    print "-----------made kustom"
       
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
 
def place_objects(room):
    #this is where we decide the chance of each monster or item appearing.
 
    #maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
 
    #chance of each monster
    monster_chances = {}
    monster_chances['soldier'] = 80  #only enemy up to level 3.
    monster_chances['imp'] = from_dungeon_level([[85, 2], [95, 5], [0, 7]])
    monster_chances['sergeant'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
 
    #maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])
 
    #chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['handgun'] = 35  
    item_chances['shotgun'] = from_dungeon_level([[25, 3]])
    item_chances['super shotgun'] =  from_dungeon_level([[25, 6]])
    item_chances['blue armour'] =   from_dungeon_level([[10, 2]])
    item_chances['red armour'] =     from_dungeon_level([[5, 4]])
    item_chances['green armour'] =    from_dungeon_level([[15, 8]])
 
 
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'soldier':
                #create a soldier
                fighter_component = Fighter(hp=10, defense=0, power=4, xp=35, death_function=monster_death)
                ai_component = BasicMonster()
        
                monster = Object(x, y, 'k', 'soldier', libtcod.desaturated_green,
                                 blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'sergeant':
                #create a sergeant
                fighter_component = Fighter(hp=6, defense=2, power=6, xp=65, death_function=monster_death)
                ai_component = BasicMonster()
 
                monster = Object(x, y, 'K', 'sergeant', libtcod.darker_green,
                                 blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'imp':
                #create a imp
                fighter_component = Fighter(hp=15, defense=4, power=3, xp=85, death_function=monster_death)
                ai_component = BasicMonster()
 
                monster = Object(x, y, 'K', 'imp', libtcod.darker_red,
                                 blocks=True, fighter=fighter_component, ai=ai_component)
 
            objects.append(monster)
 
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, max_items)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
           
            if choice == 'handgun':
                #create a handgun
                equipment_component = Equipment(slot='right hand', power_bonus=3)
                item = Object(x, y, 'h', 'handgun', libtcod.sky, equipment=equipment_component)
            elif choice == 'shotgun':
                #create a shotgun
                equipment_component = Equipment(slot='right hand', power_bonus=8)
                item = Object(x, y, 's', 'shotgun', libtcod.sky, equipment=equipment_component)
            elif choice == 'super shotgun':
                #create a super shotgun
                equipment_component = Equipment(slot='right hand', power_bonus=12)
                item = Object(x, y, 'S', 'super shotgun', libtcod.sky, equipment=equipment_component)
            elif choice == 'blue armour':
                #create a shield
                equipment_component = Equipment(slot='body', defense_bonus=5)
                item = Object(x, y, 'a', 'Armour', libtcod.blue, equipment=equipment_component)
            elif choice == 'red armour':
                #create a shield
                equipment_component = Equipment(slot='body', defense_bonus=15)
                item = Object(x, y, 'a', 'Armour', libtcod.red, equipment=equipment_component)
            elif choice == 'green armour':
                #create a shield
                equipment_component = Equipment(slot='body', defense_bonus=25)
                item = Object(x, y, 'a', 'Armour', libtcod.green, equipment=equipment_component)
 
            objects.append(item)
            item.send_to_back()  #items appear below other objects
            item.always_visible = True  #items are visible even out-of-FOV, if in an explored area

def nothing():
    """
        end 
            map 
                stuff   
                    """

class BulletAnimation():
    def __init__(self,startX,startY,endX,endY,type='bullet',frames=10):
        self.x = startX
        self.y = startY
        self.endX = endX
        self.endY = endY
        if type=='bullet':
            self.projectile = '.'
        elif type=='rocket':
            self.projectile = '*'
        else:
            self.projectile = ''
        self.frame = 0
        self.total_frames = frames
    
    def step(self):
        #first clean previous position:
        self.clear()
        #then get next position 
        libtcod.line_init(self.x,self.y,self.endX, self.endY)
        self.x, self.y = libtcod.line_step()
        if not is_blocked(self.x,self.y):
            #advance frame
            self.frame += 1
        else:
            game_animations.remove(self)

        if self.frame == self.total_frames:
            game_animations.remove(self)
            #game_animations.append(ExplosionAnim(self.x,self.y))
        else:
            self.draw()

    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            #set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, libtcod.white)
            libtcod.console_put_char(con, self.x, self.y, self.projectile, libtcod.BKGND_NONE)

    def clear(self):
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class ExplosionAnim():
    #              0                1               2           3          4
    colors = [libtcod.yellow,libtcod.red,libtcod.orange,libtcod.yellow,libtcod.yellow]
    def __init__(self, x, y, type='regular'):
        self.x = x
        self.y = y
        if type == 'regular':
            self.radius = 2
            self.max_frames = 3
        else:
            self.radius = 3
            self.max_frames = 4
        self.frame = 0
    
    def step(self):
        if self.frame < self.max_frames:
            if self.frame == 0:
                #draw only at x,y :
                self.draw(self.x,self.y,'*',ExplosionAnim.colors[self.frame])
            if self.frame >= 1:
                #draw at x,y ; x+1,y ; x-1, y ; x,y-1 ; x,y+1
                self.draw(self.x,self.y,'*', ExplosionAnim.colors[self.frame])
                self.draw(self.x-1,self.y,'*', ExplosionAnim.colors[self.frame-1])
                self.draw(self.x+1,self.y,'*', ExplosionAnim.colors[self.frame-1])
                self.draw(self.x,self.y-1,'*', ExplosionAnim.colors[self.frame-1])
                self.draw(self.x,self.y+1,'*', ExplosionAnim.colors[self.frame-1])
            if self.frame >= 2:
                #draw at x-1,y-1 ; x-1, y+1 ; x+1, y-1 ; x+1 , y+1
                self.draw(self.x-1,self.y-1,'*', ExplosionAnim.colors[self.frame])
                self.draw(self.x-1,self.y+1,'*', ExplosionAnim.colors[self.frame])
                self.draw(self.x+1,self.y+1,'*', ExplosionAnim.colors[self.frame])
                self.draw(self.x+1,self.y-1,'*', ExplosionAnim.colors[self.frame])
            
            self.frame += 1
        else:
            game_animations.remove(self)
            
    def draw(self,x,y,char,color):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(con, color)
            libtcod.console_put_char(con, x, y, char, libtcod.BKGND_NONE)   



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
        libtcod.console_blit(window, 0, 0, width, height, 0, x+x_offset, y+y_offset, 1.0, 0.7)
     
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
                text = ' @ '  + option_text + ' @ '
                #print text
            else:
                text = '    ' + option_text + '    '
            libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
            y += 1
            letter_index += 1
            line_num += 1
        
        #blit the contents of "window" to the root console
        x = 2 #SCREEN_WIDTH/2 - width/2
        #y = 4 #SCREEN_HEIGHT/2 - height/2
        libtcod.console_blit(window, 0, 0, width, height, 0, x+x_offset, y+y_offset, 1.0, 0.7)
     
        #present the root console to the player and wait for a key-press
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
        key = libtcod.console_wait_for_keypress(True)

        key_char = chr(key.c)
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_LEFT or key_char in ['w','W','A','a']:
            selection-=1
        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_RIGHT or key_char in ['s','S','D','d']:
            selection+=1
        elif key.vk == libtcod.KEY_ENTER or key_char in ['e','E','f','F']:
            return selection
        elif key.vk == libtcod.KEY_ESCAPE or key_char in ['q','Q','c','C']:
            return -1


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
 
    #now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
 
    #finally, some centered text with the values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                                 name + ':' + str(value) + '/' + str(maximum))
 
#def get_names_under_mouse():
def get_names(x,y):
    global mouse
    #return a string with the names of all objects under the mouse
 
    #(x, y) = (mouse.cx, mouse.cy)
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
             if obj.x == x and obj.y == y and obj.name != 'dot']
    if len(names) < 1:
    	names = map[x][y].terrain
 
    names = ', '.join(names)  #join the names, separated by commas
    return names.capitalize()

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


def get_square(width,height,i_x,i_y):


    str = '({},{})->({},{})'.format(i_x,i_y,i_x+width,i_y+height)
    count = [0,0,0,0,0,0,0,0]
    
    for y in range(i_y,i_y+height):
        for x in range(i_x,i_x+width):
            tile = map[x][y]
            if player.x == x and player.y == y:
                return 7
            if tile.terrain == CHAR_TALL_GRASS:
                count[0]+=1
            elif tile.terrain == CHAR_LONG_GRASS:
                count[1]+=1
            elif tile.terrain == CHAR_GRASS:
                count[2]+=1
            elif tile.terrain == CHAR_DIRT:
                count[3]+=1
            elif tile.terrain == CHAR_MOUNTAIN:
                count[4]+=1
            elif tile.terrain == CHAR_FOREST:
                count[5]+=1
            elif tile.terrain == CHAR_LAKE:
                count[6]+=1
    i = 0
    _max = 0


    while i < len(count):
        if count[i] > _max and i >= 3:
            _max = count[i]
        else:
            i+=1
    if _max != 0:
        t = count.index(_max)
    else:
        t = 3
    return t

def get_terrains(width,height):
    global map
    mmap = []
    #        ; ' , . # T ~ @
    _ter_ = [CHAR_TALL_GRASS,CHAR_LONG_GRASS,CHAR_GRASS,CHAR_DIRT,CHAR_MOUNTAIN,CHAR_FOREST,CHAR_LAKE,'@']
    mmap_x = 0
    mmap_y = 0

    while (mmap_y < MAP_HEIGHT):
        while(mmap_x < MAP_WIDTH):
            t = get_square(10,10,mmap_x,mmap_y)
            til = _ter_[t]  ##Tile(True,_ter_[t])
            mmap.append(til)
            mmap_x += 10
        mmap_y += 10
        mmap_x = 0
        
    return mmap

def mini_map(stop = True):
    width = int(MAP_WIDTH / 10)
    height = int(MAP_HEIGHT / 10)
    print "mapa : {}x{}, dividido em chunks de {} larg, {} alt".format(MAP_WIDTH,MAP_HEIGHT,width,height)

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
        elif t == CHAR_TALL_GRASS:
            color = libtcod.darker_green
        elif t == CHAR_LONG_GRASS:
            color = libtcod.dark_green
        elif t == '@':
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
    print st

    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH - (width + 1)
    y = 1
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
 
    #present the root console to the player and wait for a key-press
    if stop:
        libtcod.console_flush()
        key = libtcod.console_wait_for_keypress(True)
 
        if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
            libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)
 
    #convert the ASCII code to an index; if it corresponds to an option, return it

def render_all():
    global fov_map, color_dark_wall, color_light_wall
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

    mini_map(False)
        
 
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)
 
 
    #prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)
 
    #print the game messages, one line at a time
    y = 2
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT,line)
        y += 1
 
    #show the player's stats
    render_bar(BAR_WIDTH+10, 1, BAR_WIDTH, '+', player.fighter.hp, player.fighter.max_hp,
               libtcod.light_red, libtcod.darker_red)
    render_bar(1, 1, BAR_WIDTH, '$ ', player.fighter.purse, 200,
               libtcod.darker_green, libtcod.black)
    
    libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'floor '+str(dungeon_level))
    libtcod.console_print_ex(panel, BAR_WIDTH, 4, libtcod.BKGND_NONE, libtcod.LEFT, player.fighter.orientation)
 
    #display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names(dot_x,dot_y))
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
 
def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )

def player_move_or_attack(dx, dy, move=True):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
        return True
    
    if move:
    	player.move(dx, dy)
    	fov_recompute = True

    return False
  
def menu(header, options, width,offset=0):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
 
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
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2 + offset
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
 
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
 
    index = arrow_menu(header, options, INVENTORY_WIDTH,0,0,0)
    #index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is -1 or len(inventory) == 0: return None
    return inventory[index].item
 
def msgbox(text, width=50):
    menu(text, [], width)  #use menu() as a sort of "message box"
 
def handle_keys():
    global key,isRealTime, mouse, oldxx,oldyy,oldPxx,oldPyy,notifications
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
        
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game
 
    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8 or chr(key.c) == 'w':
            player_move_or_attack(0, -1)
            #else:
            player.fighter.orientation = NORTH

        elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2 or chr(key.c) == 's':
            #if player.fighter.orientation == SOUTH:
            player_move_or_attack(0, 1)
            #else:
            player.fighter.orientation = SOUTH
        elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4 or chr(key.c) == 'a':
            #if player.fighter.orientation == WEST:
            player_move_or_attack(-1, 0)
            #else:
            player.fighter.orientation = WEST
        elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6 or chr(key.c) == 'd':
            #if player.fighter.orientation == EAST:
            player_move_or_attack(1, 0)
            #else:
            player.fighter.orientation = EAST
        elif key.vk == libtcod.KEY_HOME or key.vk == libtcod.KEY_KP7:
            player_move_or_attack(-1, -1)
        elif key.vk == libtcod.KEY_PAGEUP or key.vk == libtcod.KEY_KP9:
            player_move_or_attack(1, -1)
        elif key.vk == libtcod.KEY_END or key.vk == libtcod.KEY_KP1:
            player_move_or_attack(-1, 1)
        elif key.vk == libtcod.KEY_PAGEDOWN or key.vk == libtcod.KEY_KP3:
            player_move_or_attack(1, 1)
        elif key.vk == libtcod.KEY_KP5:
            pass  #do nothing ie wait for the monster to come to you
        else:
            #test for other keys
            key_char = chr(key.c)
 
            if key_char in ['e','E']:
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
                            print "money : [{}]".format(player.fighter.purse)
                        elif player.x == stairs.x and player.y == stairs.y:
                            next_level()
                        elif map[player.x][player.y].terrain in ['>','<',CHAR_STAIRS]:
                            t = CHAR_MOUNTAIN
                            for x in range(player.x-2,player.x+2):
                                for y in range(player.y-1,player.y+1):
                                    if map[x][y].terrain not in [CHAR_GRASS,CHAR_LONG_GRASS,CHAR_TALL_GRASS,'<','>']:
                                        t = map[x][y].terrain
                                        break     
                            next_level(True,t)
                            break
                    elif object.x == _x and object.y == _y:
                        if object.fighter:
                            object.fighter.talk(dialogs.getValue(object.char, 0))
                        elif object.item:
                            object.item.pick_up()
                            break
                        elif object.name == 'money':
                            player.fighter.purse += 1 
                            objects.remove(object)
                            print "money : [{}]".format(player.fighter.purse)
 
            if key_char == 'c':
                opt = 5
                while opt > 0:
                    opt = arrow_menu('--game menu--',['mini map','inventory','drop stuff','char info','quit'],22,0,2,2)
                    if opt == 0:
                        mini_map()
                        continue
                    elif opt == 1:
                        chosen_item = inventory_menu('use / equip \n select with action, cancel with menu.\n')
                        if chosen_item is not None:
                            chosen_item.use()
                    elif opt == 2:
                        chosen_item = inventory_menu('drop \n select with action, cancel with menu.\n')
                        if chosen_item is not None:
                            chosen_item.drop()
                    elif opt == 3:
                        level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                        msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
                           '\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
                           '\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
                    elif opt == 4:
                        opt = -1
                        return 'exit'

    
            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('use / equip \n select with action, cancel with menu.\n')
                if chosen_item is not None:
                    chosen_item.use()

            #if key_char == 'd':
                #show the inventory; if an item is selected, drop it
                #chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
                #if chosen_item is not None:
                #    chosen_item.drop()
 
            if key_char == 'q':
                fs = []
                for o in objects:
                    if (o.x == player.x or o.y == player.y) and o.fighter:
                        fs.append(o)
                #fire in the hole!
                _x = player.x
                _y = player.y
                if player.fighter.orientation == NORTH:
                    print 'shooting N'
                    for _y in range(player.y-1,0, -1):
                        for f in fs:
                            if f.x == _x and f.y == _y:
                                notifications.append(Notif('*',3,_x,_y))
                                f.fighter.take_damage(10)
                                break
                        notifications.append(Notif('|',3,player.x,_y))
                elif player.fighter.orientation == EAST:
                    print "shooting E"
                    for _x in range(player.x+1, MAP_WIDTH):
                        for f in fs:
                            if f.x == _x and f.y == _y:
                                notifications.append(Notif('*',3,_x,_y))
                                f.fighter.take_damage(10)
                                break
                        notifications.append(Notif('-',3,_x,player.y))
                elif player.fighter.orientation == SOUTH:
                    print "shooting S"
                    for _y in range(player.y+1, MAP_HEIGHT):
                        for f in fs:
                            if f.x == _x and f.y == _y:
                                notifications.append(Notif('*',3,_x,_y))
                                f.fighter.take_damage(10)
                                break

                        notifications.append(Notif('|',3,player.x,_y))
                elif player.fighter.orientation == WEST:
                    print "shooting W"
                    for _x in range(player.x-1,0,-1):
                        for f in fs:
                            if f.x == _x and f.y == _y:
                                notifications.append(Notif('*',3,_x,_y))
                                f.fighter.take_damage(10)
                                break

                        notifications.append(Notif('-',3,_x,player.y))
          
            if key_char == '<':
                #go down stairs, if the player is on them
                if map[player.x][player.y].type in ['>','<']:
                    next_level()
            if key_char == 'm':
                mini_map()
            if chr(key.c) == 'f' or chr(key.c) == 'F':
                if player.fighter.orientation == EAST:
                    notifications.append(Notif('/',2,player.x+1,player.y-1))
                    notifications.append(Notif('-',3,player.x+1,player.y))
                    notifications.append(Notif('\\',4,player.x+1,player.y+1))
                    if not player_move_or_attack(1, 0,False) and not player_move_or_attack(1, -1,False) and not player_move_or_attack(1, 1,False):
                        swing_sword(player.x+1,player.y-1)
                        swing_sword(player.x+1,player.y+1)
                        return 'attack'
                    else:
                        return 'nop'
                elif player.fighter.orientation == NORTH:
                    notifications.append(Notif('\\',2,player.x-1,player.y-1))
                    notifications.append(Notif('|',3,player.x,player.y-1))
                    notifications.append(Notif('/',4,player.x+1,player.y-1))
                    if not player_move_or_attack(1, -1,False) and not player_move_or_attack(-1, -1,False) and not player_move_or_attack(0, -1,False):
                        swing_sword(player.x-1,player.y-1)
                        swing_sword(player.x+1,player.y-1)
                        return 'attack'
                    else:
                        return 'nop'
                elif player.fighter.orientation == WEST:
                    notifications.append(Notif('\\',2,player.x-1,player.y-1))
                    notifications.append(Notif('-',3,player.x-1,player.y))
                    notifications.append(Notif('/',4,player.x-1,player.y+1))
                    if not player_move_or_attack(-1, 0,False) and not player_move_or_attack(-1, -1,False) and not player_move_or_attack(-1, 1,False):  
                        swing_sword(player.x-1,player.y-1)
                        swing_sword(player.x-1,player.y+1)
                        return 'attack'
                    else:
                        return 'nop'
                elif player.fighter.orientation == SOUTH:
                    notifications.append(Notif('/',2,player.x-1,player.y+1))
                    notifications.append(Notif('|',3,player.x,player.y+1))
                    notifications.append(Notif('\\',4,player.x+1,player.y+1))

                    if not player_move_or_attack(0, 1,False) and not player_move_or_attack(+1, 1,False) and not player_move_or_attack(-1, 1,False):
                        swing_sword(player.x-1,player.y+1)
                        swing_sword(player.x+1,player.y+1)
                        return 'attack'
                    else:
                        return 'nop'


 
            return 'didnt-take-turn'

def player_death(player):
    #the game ended!
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
    main_menu()

def monster_death(monster):
    global objects
    if random.randint(0,10) > 5:
        #transform it into a nasty corpse! it doesn't block, can't be
        #attacked and doesn't move
        message('+' + str(monster.fighter.xp) + 'xp.', libtcod.orange)
        monster.char = '%'
        monster.color = libtcod.dark_red
        monster.blocks = False
        monster.fighter = None
        monster.ai = None
        monster.name = 'remains of ' + monster.name
        #add new object of the tipe "ammo"
        monster.send_to_back()
    else:
        objects.remove(monster)

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
            
def shootAt(x,y,player):
    __wp = player.fighter.current_weapon
    if player.fighter.ammo[__wp] > 0:
        dmg = weapon_inv[player.fighter.current_weapon].shoot()
        player.fighter.ammo[player.fighter.current_weapon] -= 1
        libtcod.line_init(player.x, player.y, x, y)
        xx,yy=libtcod.line_step()
        while (not xx is None):
            for obj in objects:  #damage every fighter in range, including the player
                if obj.fighter and (obj.x == xx and obj.y == yy) :
                    message('The ' + obj.name + ' gets shot for ' + str(dmg) + ' hit points.', libtcod.orange)
                    obj.fighter.take_damage(dmg)
                return 1
            if is_blocked(xx,yy):
                break            
    else:
        message('out of ammo!', libtcod.light_red)
  
def save_game():
    #open a new empty shelve (possibly overwriting an old one) to write the game data
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index'] = objects.index(player)  #index of player in objects list
    file['stairs_index'] = objects.index(stairs)  #same for the stairs
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
    player = objects[file['player_index']]  #get index of player in objects list and access it
    stairs = objects[file['stairs_index']]  #same for the stairs
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    dungeon_level = file['dungeon_level']
    game_animations = []
    file.close()
 
    isRealTime = False
    initialize_fov()
    dialogs = Dialogs()
    dialogs.loadFromFile()

 
def new_game():
    global player, inventory, weapon_inv, game_msgs, game_state, dungeon_level, isRealTime, game_animations, objects
 
    #create object representing the player
    fighter_component = PlayerFighter(hp=10, defense=1, power=2, xp=0, death_function=player_death)
    player = Object(0, 0, '@', 'koboldicider', libtcod.white, blocks=True, fighter=fighter_component)
    
    player.level = 1
    isRealTime = False
 
    #generate map (at this point it's not drawn to the screen)
    dungeon_level = 1
    #make_bsp() #commented make map
    objects = []
    make_world_map(6)
    initialize_fov()
 
    game_state = 'playing'
    inventory = []
    game_animations = []
    weapon_inv = []

    #create the list of game messages and their colors, starts empty
    game_msgs = []
    save_game()
    fighter_component = Fighter(hp=5, defense=5, power=3, xp=85, death_function=monster_death)
    ai_component = BasicMonster()

    monster = Object(random.randint(3,MAP_WIDTH), random.randint(3,MAP_HEIGHT), 'O', 'kobold farmer', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    objects.append(monster)

    #initial equipment: a dagger
    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = Object(0, 0, '-', 'knife', libtcod.sky, equipment=equipment_component)
    inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True
 
def next_level(dungeon = False,terrain=CHAR_MOUNTAIN):
    #advance to the next level
    global dungeon_level
    message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2)  #heal the player by 50%
    lair = False
    dungeon_level += 1
    if dungeon:
        r = random.randint(0,3)
        if  r >= 2:
            make_customgenericmap(terrain)
            lair = True
        else:
            make_map(terrain)  #create a fresh new level!
        initialize_fov()
    else:
        make_world_map(dungeon_level*2)
    #save_game() #save game!
    

    if not lair:
        fighter_component = Fighter(hp=5, defense=3, power=5, xp=85, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(random.randint(3,20), random.randint(3,20), 'O', 'kobold', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(monster)
    else:
        add_dragon()

    


    initialize_fov()
 
def add_dragon():
    global objects
    fighter_component = Fighter(hp=50, defense=9, power=8, xp=800, death_function=monster_death)
    ai_component = BasicMonster()
    monster = Object(40, 10, 'O', 'dragon head', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=50, defense=7, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster)
    monster_body = Object(40,9, '+', 'dragon upper body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=50, defense=7, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_body2 = Object(40,8, '+', 'dragon mid body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=50, defense=7, power=0, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_body3 = Object(40,7, '+', 'dragon lower body', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    fighter_component = Fighter(hp=50, defense=7, power=2, xp=5, death_function=monster_death)
    ai_component = Body(monster_body)
    monster_tail = Object(40,8, '*', 'dragon tail', libtcod.darker_red,blocks=True, fighter=fighter_component, ai=ai_component)
    objects.append(monster)
    objects.append(monster_body)
    objects.append(monster_body2)
    objects.append(monster_body3)
    objects.append(monster_tail)

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
    player_action = None
    notifications = []
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
            save_game()
            break

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
           drop = random.randint(1,42)
           if drop >= 37:
                objects.append(Object(player.x, player.y, '$', 'money', libtcod.yellow, always_visible=True))
           elif drop >= 33:
                fighter_component = Fighter(hp=2, defense=1, power=1, xp=3, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(_x, _y, '~', 'worm', libtcod.pink,
                                 blocks=True, fighter=fighter_component, ai=ai_component)
                objects.append(monster)
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
           fighter_component = Fighter(hp=2, defense=1, power=1, xp=3, death_function=monster_death)
           ai_component = BasicMonster()
           monster = Object(_x, _y, '-', 'worm', libtcod.desaturated_red,blocks=True, fighter=fighter_component, ai=ai_component)
           initialize_fov()


def main_menu():
    #img = libtcod.image_load('menu_background.png')
    libtcod.console_map_ascii_code_to_font('@', 2, 0)
    libtcod.console_map_ascii_code_to_font('O', 1, 0)
    libtcod.console_map_ascii_code_to_font('+', 3, 0)
    libtcod.console_map_ascii_code_to_font('T', 6, 0)

    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
        #libtcod.image_blit_2x(img, 0, 0, 0)
 
        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.black)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2+10, SCREEN_HEIGHT-10, libtcod.BKGND_NONE, libtcod.CENTER,
                                 'kobolicide - test version')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2+10, SCREEN_HEIGHT-12, libtcod.BKGND_NONE, libtcod.CENTER, 'gr33n 0v3r b14ck')
 
        #show options and wait for the player's choice
        #_continue = arrow_menu('continue ?',['   yes','    no'],12,0,12,12)
        #choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 25,10)
        choice = arrow_menu('koboldicide test version',['Play a new game', 'Continue last game', 'Quit'],40,0,3,10)
 
        if choice == 0:  #new game
            new_game()
            play_game()
        if choice == 1:  #load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2:  #quit
            break
 
libtcod.console_set_custom_font('16x16_sm_ascii.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'kobolicide - teste version v-1', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
 
main_menu()