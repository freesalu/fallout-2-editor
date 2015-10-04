""" Save game editor for Fallout 2. Only tested on GoG.com version on OSX.

Make a backup of all your save files before running!
"""

import getpass
import os
import re
import mmap
import struct
import sys

class F2SaveFile(object):
    """Save file representation. Not perfect but it works on my machine!"""

    f5_marker = b'\x00\x00\x46\x50'
    neg_1 = 0xFFFFFFFF
    item_path = "f2items.csv"
    item_db = {}
    hex_map = {
        'header': {
            'offset':0x0,
            'keys': {
                'name':(0x1D, 0x20),
                'savename':(0x3D, 0x1E),
                'savetime':(0x5B, 0x02)
            }
        },
        'f5': {
            'offset':None,
            'keys': {
                'hp':(0x74, 0x04),
                'rad':(0x78, 0x04),
                'poison':(0x7C, 0x04),
                'level':(0x28, 0x04),
            }
        },
        'f6': {
            'offset':None,
            'keys':{
                'base_str':(0x08, 0x04),
                'base_per':(0x0C, 0x04),
                'base_end':(0x10, 0x04),
                'base_cha':(0x14, 0x04),
                'base_int':(0x18, 0x04),
                'base_agi':(0x1C, 0x04),
                'base_luc':(0x20, 0x04),
                'base_hp':(0x24, 0x04),
                'base_ap':(0x28, 0x04),
                'starting_age':(0x8C, 0x04),
                'female':(0x90, 0x04),
                'meele_dam':(0x34, 0x04),
                'base_ac':(0x2C, 0x04),
                'normal_thr':(0x4C, 0x04),
                'normal_res':(0x68, 0x04),
                'bonus_m':(0xC0, 0x04),
                'skills':(0x0120, 0x04)
            }
        },
        'f9' : {'offset':None}
    }
    skills = {}
    perks = {}

    def __init__(self, path):
        self.f = open(os.path.join(path, 'SAVE.DAT'), 'r+b')
        self.mm = mmap.mmap(self.f.fileno(), 0)
        self.load_items()
        self.load_skills()
        self.load_perks()
        self.stats = ['str', 'agi', 'per', 'end', 'luc', 'int', 'cha']
        self.hex_map['f5']['offset'] = self.find_address(self.f5_marker)
        self.f5s = self.find_address(self.f5_marker)
        self.hex_map['f6']['offset'] = self.find_F6()
        self.hex_map['f9']['offset'] = self.hex_map['f6']['offset'] + 0x0178 + 0x4C + 0x10

    def fetch_value(self, offset, size):
        return self.mm[offset:offset+size]

    def fetch_int(self, offset, size):
        return struct.unpack('>i', self.fetch_value(offset, size))[0]

    def get_value(self, fun, key):
        return self.fetch_value(self.hex_map[fun]['offset'] + self.hex_map[fun]['keys'][key][0], self.hex_map[fun]['keys'][key][1])

    def get_int(self, fun, key):
        return struct.unpack('>i', self.get_value(fun, key))[0]

    def set_int(self, offs, val):
        self.mm[offs:offs+0x04] = struct.pack('>i', val)

    def set_function_int(self, fun, key, val):
        to_up = self.hex_map[fun]['offset'] + self.hex_map[fun]['keys'][key][0]
        self.set_int(to_up, val)

    def get_function_int(self, fun, key):
        to_up = self.hex_map[fun]['offset'] + self.hex_map[fun]['keys'][key][0]
        return struct.unpack('>i', self.mm[to_up:to_up+0x04])[0]

    def load_skills(self):
        with open('f2skills.csv', 'r') as f:
            for line in f:
                offs, name = line.replace('\n', '').split(',')
                self.skills[name] = int(offs, 16)*0x04

    def load_perks(self):
        with open('f2perks.csv', 'r') as f:
            for line in f:
                offs, name = line.replace('\n', '').split(',')
                self.perks[name] = int(offs, 16)*0x04

    def get_skill(self, name):
        if name not in self.skills:
            print "Skill not found."
        return self.fetch_int(self.hex_map['f6']['offset']+self.hex_map['f6']['keys']['skills'][0] + self.skills[name], 0x04)

    def set_skill(self, name, value):
        if name not in self.skills:
            print "Skill not found."
            return
        self.set_int(self.hex_map['f6']['offset']+self.hex_map['f6']['keys']['skills'][0] + self.skills[name], value)

    def set_perk(self, name, val=1):
        self.set_int(self.hex_map['f9']['offset'] + self.perks[name], val)

    def get_perk(self, name):
        if name not in self.perks:
            print "Perk not found."
            return
        return self.fetch_int(self.hex_map['f9']['offset'] + self.perks[name], 0x04)

    def set_stat(self, stat, value):
        if stat not in self.stats:
            print "No such stat."
            return
        self.set_function_int('f6', 'base_'+stat, value)

    def get_stat(self, stat):
        if stat not in self.stats:
            print "No such stat."
            return
        return self.get_int('f6', 'base_'+stat)

    def print_skills(self):
        print "{:<15} {:<30}".format('Skill','Value')
        print 21*"-"
        for skill in sorted(self.skills.keys()):
            print "{:<15} {:<30}".format(skill, self.get_skill(skill))

    def print_perks(self):
        print "{:<40} {:<6}".format('Perk', 'Value')
        print 46*"-"
        for perk in sorted(self.perks.keys()):
            print "{:<40} {:<6}".format(perk, self.get_perk(perk))

    def print_stats(self):
        print "{:<15} {:<30}".format('Stat','Value')
        print 21*"-"
        for stat in sorted(self.stats):
            print "{:<15} {:<30}".format(stat, self.get_stat(stat))        

    def load_items(self):
        with open(self.item_path, 'r') as f:
            section = None
            for line in f:
                line = line.replace('\n', '').strip()
                if line == '': continue
                if line[0] == '[':
                    if section:
                        section = None
                    section = line[1:len(line)-1]
                    continue
                ps = line.split(',')
                if len(ps) % 2 != 0:
                    print "BAD LINE: {0}".format(line)
                    exit(1)
                for i in xrange(0, len(ps), 2):
                    self.item_db[ps[i]] = {'name':ps[i+1], "section":section}
        #print "Loaded {0} items.".format(len(self.item_db))

    def find_F6(self):
        """ Region without a fixed start index. """
        items_start = 0x80 + self.f5s
        item_size = 0x58 + 0x04
        always_zero = [0x0C, 0x10, 0x40, 0x58]
        always_neg_one = [0x34, 0x48]
        bad_item = False
        c = 0
        #print "Scanning items..."
        c_item_start = items_start - item_size
        while not bad_item:
            c_item_start += item_size
            obj_id = str(self.fetch_int(c_item_start + 0x30, 0x04))
            if obj_id not in self.item_db:
                print "<WARNING> Be careful! Unknown item found. Editing is likely to fail!"
                break

            amt = self.fetch_int(c_item_start, 0x04)
            section = self.item_db[obj_id]['section']
            for addr in always_zero:
                c_val = self.fetch_int(c_item_start + addr, 0x04)
                #print c_val
                if c_val != 0:
                    pass
                    bad_item = True
            if bad_item:
                break

            #print "{0} : [name: {1}\tamt: {2}\tsection: {3}]".format(obj_id, self.item_db[obj_id]['name'], amt, section)
            if section in ['weapons']:
                c_item_start += 0x04
            #TODO Add containers
            if not(section in ['armor', 'drugs']):
                c_item_start += 0x04
            c += 1
        #print "Found {0} items.".format(c)
        return c_item_start + 0x04

    def find_address(self, marker):
        return self.mm.find(marker)

    def print_info(self):
        print "Save Name: '{0}'\tCharacter: '{1}'".format(self.get_value('header', 'savename'), self.get_value('header', 'name'))
