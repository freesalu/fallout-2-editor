""" Save game editor for Fallout 2. Only tested on GoG.com version on OSX.

Make a backup of all your save files before running!
"""

import os
import mmap
import struct

class F2SaveFile(object):
    """Save file representation. Not perfect but it works on my machine!"""
    item_db = {}
    skills = {}
    perks = {}
    #Offsets/markers from http://falloutmods.wikia.com/wiki/SAVE.DAT_File_Format
    f5_marker = b'\x00\x00\x46\x50'
    neg_1 = 0xFFFFFFFF
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

    def __init__(self, path):
        self.save_file = open(os.path.join(path, 'SAVE.DAT'), 'r+b')
        # Create a memory map of the file.
        self.mm_save = mmap.mmap(self.save_file.fileno(), 0)
        # _load hex values for stats/skills/perks.
        self._load_items()
        self._load_skills()
        self._load_perks()
        self.stats = ['str', 'agi', 'per', 'end', 'luc', 'int', 'cha']
        # Find Function 5
        self.hex_map['f5']['offset'] = self._find_address(self.f5_marker)
        self.f5s = self._find_address(self.f5_marker)
        # Find Function 6
        self.hex_map['f6']['offset'] = self._find_f6()
        # And Function 9, based on where Function 6 is.
        f9_offset = 0x0178 + 0x4C + 0x10
        self.hex_map['f9']['offset'] = self.hex_map['f6']['offset'] + f9_offset

    def _fetch_value(self, offset, size):
        return self.mm_save[offset:offset+size]

    def _fetch_int(self, offset, size):
        return struct.unpack('>i', self._fetch_value(offset, size))[0]

    def get_value(self, fun, key):
        return self._fetch_value(self.hex_map[fun]['offset'] +
            self.hex_map[fun]['keys'][key][0], 
            self.hex_map[fun]['keys'][key][1])

    def get_int(self, fun, key):
        return struct.unpack('>i', self.get_value(fun, key))[0]

    def set_int(self, offs, val):
        self.mm_save[offs:offs+0x04] = struct.pack('>i', val)

    def set_function_int(self, fun, key, val):
        to_up = self.hex_map[fun]['offset'] + self.hex_map[fun]['keys'][key][0]
        self.set_int(to_up, val)

    def get_function_int(self, fun, key):
        to_up = self.hex_map[fun]['offset'] + self.hex_map[fun]['keys'][key][0]
        return struct.unpack('>i', self.mm_save[to_up:to_up+0x04])[0]

    def _load_skills(self):
        fname = os.path.join('data', 'f2skills.csv')
        with open(fname, 'r') as skill_file:
            for line in skill_file:
                offs, name = line.replace('\n', '').split(',')
                self.skills[name] = int(offs, 16)*0x04

    def _load_perks(self):
        fname = os.path.join('data', 'f2perks.csv')
        with open(fname, 'r') as perk_file:
            for line in perk_file:
                offs, name = line.replace('\n', '').split(',')
                self.perks[name] = int(offs, 16)*0x04

    def get_skill(self, name):
        if name not in self.skills:
            raise KeyError('No skill named "{0}"'.format(name))
        return self._fetch_int(self.hex_map['f6']['offset'] +
            self.hex_map['f6']['keys']['skills'][0] + self.skills[name], 0x04)

    def set_skill(self, name, value):
        if name not in self.skills:
            raise KeyError('No skill named "{0}"'.format(name))
        self.set_int(self.hex_map['f6']['offset'] + 
            self.hex_map['f6']['keys']['skills'][0] + 
            self.skills[name], value)

    def get_perk(self, name):
        if name not in self.perks:
            raise KeyError('No perk named "{0}"'.format(name))
        return self._fetch_int(self.hex_map['f9']['offset'] +
            self.perks[name], 0x04)

    def set_perk(self, name, val=1):
        if name not in self.perks:
            raise KeyError('No perk named "{0}"'.format(name))
        self.set_int(self.hex_map['f9']['offset'] + self.perks[name], val)

    def get_stat(self, name):
        if name not in self.stats:
            raise KeyError('No stat named "{0}"'.format(name))
        return self.get_int('f6', 'base_' + name)

    def set_stat(self, name, value):
        if name not in self.stats:
            raise KeyError('No stat named "{0}"'.format(name))
        self.set_function_int('f6', 'base_' + name, value)

    def print_skills(self):
        print "{:<15} {:<30}".format('Skill', 'Value')
        print 21*"-"
        for skill in sorted(self.skills.keys()):
            print "{:<15} {:<30}".format(skill, self.get_skill(skill))

    def print_perks(self):
        print "{:<40} {:<6}".format('Perk', 'Value')
        print 46*"-"
        for perk in sorted(self.perks.keys()):
            print "{:<40} {:<6}".format(perk, self.get_perk(perk))

    def print_stats(self):
        print "{:<15} {:<30}".format('Stat', 'Value')
        print 21*"-"
        for stat in sorted(self.stats):
            print "{:<15} {:<30}".format(stat, self.get_stat(stat))        

    def _load_items(self):
        fname = os.path.join('data', 'f2items.csv')
        with open(fname, 'r') as item_file:
            section = None
            for line in item_file:
                line = line.replace('\n', '').strip()
                if line == '':
                    continue
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

    def _find_f6(self):
        """ Region without a fixed start index. """
        items_start = 0x80 + self.f5s
        item_size = 0x58 + 0x04
        always_zero = [0x0C, 0x10, 0x40, 0x58]
        #always_neg_one = [0x34, 0x48]
        bad_item = False
        c_item_start = items_start - item_size
        while not bad_item:
            c_item_start += item_size
            obj_id = str(self._fetch_int(c_item_start + 0x30, 0x04))
            if obj_id not in self.item_db:
                raise ValueError('Found unknown item id. Editing this file will corrupt it.')
            #amt = self._fetch_int(c_item_start, 0x04)
            section = self.item_db[obj_id]['section']
            for addr in always_zero:
                c_val = self._fetch_int(c_item_start + addr, 0x04)
                if c_val != 0:
                    pass
                    bad_item = True
            if bad_item:
                break
            if section in ['weapons']:
                c_item_start += 0x04
            #TODO Add containers
            if not(section in ['armor', 'drugs']):
                c_item_start += 0x04
        return c_item_start + 0x04

    def _find_address(self, marker):
        return self.mm_save.find(marker)

    def print_info(self):
        print "Save Name: '{0}'\tCharacter: '{1}'".format(
            self.get_value('header', 'savename'), 
            self.get_value('header', 'name'))
