from data.enemy import Enemy
from data.structures import DataArray

from data.enemy_formations import EnemyFormations
from data.enemy_packs import EnemyPacks
from data.enemy_zones import EnemyZones
from data.enemy_scripts import EnemyScripts
import data.bosses as bosses


class Enemies():
    DATA_START = 0xf0000
    DATA_END = 0xf2fff
    DATA_SIZE = 32

    NAMES_START = 0xfc050
    NAMES_END = 0xfd0cf
    NAME_SIZE = 10

    ITEMS_START = 0xf3000
    ITEMS_END = 0xf35ff
    ITEMS_SIZE = 4

    SPECIAL_NAMES_START = 0xfd0d0
    SPECIAL_NAMES_END = 0xfdfdf
    SPECIAL_NAMES_SIZE = 10

    DRAGON_COUNT = 8

    SRBEHEMOTH2_ID = 127
    INVINCIBLE_GUARDIAN_ID = 273

    def __init__(self, rom, args, items=[]):
        self.rom = rom
        self.args = args
        self.items = items

        self.enemy_data = DataArray(self.rom, self.DATA_START, self.DATA_END, self.DATA_SIZE)
        self.enemy_name_data = DataArray(self.rom, self.NAMES_START, self.NAMES_END, self.NAME_SIZE)
        self.enemy_item_data = DataArray(self.rom, self.ITEMS_START, self.ITEMS_END, self.ITEMS_SIZE)
        self.enemy_special_name_data = DataArray(self.rom, self.SPECIAL_NAMES_START, self.SPECIAL_NAMES_END,
                                                 self.SPECIAL_NAMES_SIZE)

        self.enemies = []
        self.bosses = []
        for enemy_index in range(len(self.enemy_data)):
            enemy = Enemy(enemy_index, self.enemy_data[enemy_index], self.enemy_name_data[enemy_index],
                          self.enemy_item_data[enemy_index], self.enemy_special_name_data[enemy_index])
            self.enemies.append(enemy)

            if enemy_index in bosses.enemy_name and enemy_index not in bosses.removed_enemy_name:
                self.bosses.append(enemy)

        self.formations = EnemyFormations(self.rom, self.args, self)
        self.packs = EnemyPacks(self.rom, self.args, self.formations)
        self.zones = EnemyZones(self.rom, self.args)
        self.scripts = EnemyScripts(self.rom, self.args, self)

        if self.args.doom_gaze_no_escape:
            # if doom gaze cannot escape, do not allow the party to escape from doom gaze
            # this prevents escaping from doom gaze in a shuffled/random place and getting a free check
            doom_gaze_id = self.get_enemy("Doom Gaze")
            self.enemies[doom_gaze_id].no_run = 1

    def __len__(self):
        return len(self.enemies)

    def get_random(self):
        import random
        random_enemy = random.choice(self.enemies[:255])
        return random_enemy.id

    def get_enemy(self, name):
        if name in bosses.name_enemy:
            return bosses.name_enemy[name]
        for enemy in self.enemies:
            if enemy.name == name:
                return enemy.id

    def get_name(self, enemy_id):
        if enemy_id in bosses.enemy_name:
            return bosses.enemy_name[enemy_id]
        return self.enemies[enemy_id].name

    def set_rare_steal(self, enemy_id, item_id):
        self.enemies[enemy_id].steal_rare = item_id

    def set_common_steal(self, enemy_id, item_id):
        self.enemies[enemy_id].steal_common = item_id

    def set_rare_drop(self, enemy_id, item_id):
        self.enemies[enemy_id].drop_rare = item_id

    def set_common_drop(self, enemy_id, item_id):
        self.enemies[enemy_id].drop_common = item_id

    def remove_fenix_downs(self):
        import random
        from data.item_names import name_id

        fenix_down = name_id["Fenix Down"]
        possible_replacements = ["Tonic", "Potion", "Tincture", "Antidote", "Echo Screen", "Eyedrop", "Green Cherry",
                                 "Revivify", "Soft", "Ether", "Sleeping Bag", "Tent", "Remedy", "Dried Meat"]
        possible_replacements = [name_id[item_name] for item_name in possible_replacements]

        for enemy in self.enemies:
            if enemy.steal_common == fenix_down:
                replacement = random.choice(possible_replacements)
                self.set_common_steal(enemy.id, replacement)

            if enemy.steal_rare == fenix_down:
                replacement = random.choice(possible_replacements)
                self.set_rare_steal(enemy.id, replacement)

            if enemy.drop_common == fenix_down:
                replacement = random.choice(possible_replacements)
                self.set_common_drop(enemy.id, replacement)

            if enemy.drop_rare == fenix_down:
                replacement = random.choice(possible_replacements)
                self.set_rare_drop(enemy.id, replacement)

    def apply_scaling(self):
        # lower vargas and whelk's hp
        vargas_id = self.get_enemy("Vargas")
        self.enemies[vargas_id].hp = self.enemies[vargas_id].hp // 2

        ultros3_id = self.get_enemy("Ultros 3")
        self.enemies[ultros3_id].hp = self.enemies[ultros3_id].hp // 2

        # increase hp of some early bosses (especially ones which are normally not fought with a full party)
        hp4x = ["Leader", "Marshal"]
        hp3x = ["Rizopas", "Piranha", "TunnelArmr"]
        hp2x = ["Ipooh", "GhostTrain", "Kefka (Narshe)", "Dadaluma", "Ifrit", "Shiva", "Number 024",
                "Number 128", "Left Blade", "Right Blade", "Left Crane", "Right Crane", "Nerapa"]

        if not self.args.balance_boss_stats:
            # double opera ultros' hp only if not already rebalanced
            # each form (location) has different hp pools so it is already challenging enough after the rebalance
            hp2x.append("Ultros 2")

        for boss_id, boss_name in bosses.enemy_name.items():
            enemy = self.enemies[boss_id]
            if boss_name in hp4x:
                enemy.hp *= 4
            elif boss_name in hp3x:
                enemy.hp *= 3
            elif boss_name in hp2x:
                enemy.hp *= 2

    def boss_experience(self):
        from data.bosses_custom_exp import custom_exp
        for enemy_id, exp in custom_exp.items():
            self.enemies[enemy_id].exp = exp * self.enemies[enemy_id].level

    def boss_rebalance_stats(self):
        stats = ["speed", "vigor", "defense", "magic_defense", "magic"]
        baseline_stats = [50, 60, 135, 155, 10]  # baseline values to rebalance around

        for enemy in self.bosses:
            for stat_index, stat in enumerate(stats):
                stat_value = getattr(enemy, stat)

                if stat_value < baseline_stats[stat_index]:
                    rebalanced_stat = int((baseline_stats[stat_index] + stat_value) / 2)
                else:
                    rebalanced_stat = stat_value

                setattr(enemy, stat, rebalanced_stat)
                print(f"DEBUG: Normalizing {enemy.name}'s {stat} to {rebalanced_stat} (was {stat_value})")

    def boss_rebalance_hpmp(self):
        # Exclude "child" bosses from HP rebalancing
        hp_mp_exclude = [321, 322, 320, 319, 325, 327, 269, 316, 317, 318, 333, 294, 352, 353, 354, 288, 289, 359, 326,
                         340]
        hp_mp_parents = {
            268: [321, 322],
            267: [319, 320],
            275: [325, 327],
            270: [269],
            283: [316, 317, 318],
            259: [333],
            291: [294, 352, 353, 354],
            287: [288, 289],
            290: [359]
        }

        baseline_hp = 650
        baseline_mp = 230

        # Create a reverse mapping of child to parent
        child_to_parent = {child: parent for parent, children in hp_mp_parents.items() for child in children}

        # Store rebalancing factors for parents
        parent_rebalancing = {}

        # First Pass: Process all non-excluded bosses and parents
        for enemy in self.bosses:
            if enemy.id not in hp_mp_exclude:
                # Normalize HP and MP for non-excluded enemies (including parents)
                if enemy.hp < (enemy.level * baseline_hp):
                    rebalanced_hp = int(((baseline_hp * enemy.level) + enemy.hp) / 2)
                else:
                    rebalanced_hp = enemy.hp

                if enemy.mp < (enemy.level * baseline_mp):
                    rebalanced_mp = int(((baseline_mp * enemy.level) + enemy.mp) / 2)
                else:
                    rebalanced_mp = enemy.mp

                # Store rebalancing factors for parent bosses
                if enemy.id in hp_mp_parents:
                    hp_multiplier = rebalanced_hp / enemy.hp if enemy.hp > 0 else 1
                    mp_multiplier = rebalanced_mp / enemy.mp if enemy.mp > 0 else 1
                    parent_rebalancing[enemy.id] = (rebalanced_hp, hp_multiplier, rebalanced_mp, mp_multiplier)
                    print(
                        f"Parent {enemy.name} (ID {enemy.id}) rebalancing: HP x{hp_multiplier}, MP x{mp_multiplier}")

                # Apply rebalanced values
                print(
                    f"DEBUG: {enemy.name}'s HP rebalanced to {rebalanced_hp} (was {enemy.hp}), MP rebalanced to {rebalanced_mp} (was {enemy.mp})")
                setattr(enemy, "hp", rebalanced_hp)
                setattr(enemy, "mp", rebalanced_mp)


        # Second Pass: Process child bosses based on their parent's rebalancing
        for enemy in self.bosses:
            if enemy.id in hp_mp_exclude:
                parent_id = child_to_parent.get(enemy.id)
                # Exception case for Ipooh (sets his HP to always be 50% of Vargas's HP)
                if enemy.id == 333:
                    if parent_id in parent_rebalancing:
                        parent_rebalanced_hp = parent_rebalancing[parent_id][0]
                        rebalanced_hp = int(parent_rebalanced_hp / 2)
                        rebalanced_mp = enemy.mp  # Keep MP as is
                        print(
                            f"Special Case: Child {enemy.name} (ID {enemy.id}) HP set to 50% of parent's (ID {parent_id}) HP")

                elif parent_id in parent_rebalancing:
                    _, hp_multiplier, _, mp_multiplier = parent_rebalancing[parent_id]
                    rebalanced_hp = int(enemy.hp * hp_multiplier)
                    rebalanced_mp = int(enemy.mp * mp_multiplier)
                    print(
                        f"Child {enemy.name} (ID {enemy.id}) inherits parent's (ID {parent_id}) rebalancing: HP x{hp_multiplier}, MP x{mp_multiplier}")
                else:
                    rebalanced_hp, rebalanced_mp = enemy.hp, enemy.mp
                    print(f"No HP adjustment applied on child enemy: {enemy.name} (ID {enemy.id})")

                # Apply rebalanced values
                setattr(enemy, "hp", rebalanced_hp)
                setattr(enemy, "mp", rebalanced_mp)
                print(f"DEBUG: {enemy.name}'s HP rebalanced to {rebalanced_hp}, MP rebalanced to {rebalanced_mp}")

    def boss_stats_randomize(self):
        import random

        # Exclude "child" bosses from HP distortion
        bosses_exclude = [321, 322, 320, 319, 325, 327, 269, 316, 317, 318, 333, 294, 352, 353, 354, 288, 289, 359, 326,
                         340]
        bosses_parents = {
            268: [321, 322],
            267: [319, 320],
            275: [325, 327],
            270: [269],
            283: [316, 317, 318],
            259: [333],
            291: [294, 352, 353, 354],
            287: [288, 289],
            290: [359]
        }

        # Map child IDs to their parent
        child_to_parent = {child: parent for parent, children in bosses_parents.items() for child in children}

        # Define stats to distort
        stats = ["speed", "vigor", "defense", "magic_defense", "magic"]

        # Store distortion factors for parent bosses
        distortion_factors = {}

        if self.args.boss_stats_random_percent_min != 100 or self.args.boss_stats_random_percent_max != 100:
            # First Pass: Distort stats for non-excluded and parent bosses
            for enemy in self.bosses:
                if enemy.id not in bosses_exclude:
                    distortion_factors[enemy.id] = {}
                    for stat in stats:
                        stat_value = getattr(enemy, stat)
                        if stat_value != 0:
                            # Apply random distortion
                            boss_stat_percent = random.randint(
                                self.args.boss_stats_random_percent_min,
                                self.args.boss_stats_random_percent_max
                            ) / 100.0
                            value = int(stat_value * boss_stat_percent)
                            distorted_stat = max(min(value, 255), 0)
                            setattr(enemy, stat, distorted_stat)

                            # Record the distortion factor
                            distortion_factors[enemy.id][stat] = boss_stat_percent
                            print(f"DEBUG: Distorting {enemy.name}'s {stat} to {distorted_stat} (was {stat_value})")

            # Second Pass: Apply parent distortion factors to child bosses
            for enemy in self.bosses:
                if enemy.id in child_to_parent:
                    parent_id = child_to_parent[enemy.id]
                    if parent_id in distortion_factors:
                        for stat in stats:
                            stat_value = getattr(enemy, stat)
                            if stat_value != 0:
                                # Apply parent's distortion factor
                                parent_factor = distortion_factors[parent_id].get(stat, 1.0)
                                value = int(stat_value * parent_factor)
                                distorted_stat = max(min(value, 255), 0)
                                setattr(enemy, stat, distorted_stat)
                                print(f"DEBUG: Child {enemy.name}'s {stat} distorted to {distorted_stat} "
                                      f"using parent's (ID {parent_id}) factor {parent_factor:.2f}")

        '''stats = ["speed", "vigor", "defense", "magic_defense", "magic"]
        bosses_exclude = ["Speck", "Piranha"]
        if self.args.boss_stats_random_percent_min != 100 or self.args.boss_stats_random_percent_max != 100:
            for enemy in self.bosses:
                for stat in stats:
                    stat_value = getattr(enemy, stat)
                    if stat_value != 0:
                        boss_stat_percent = random.randint(self.args.boss_stats_random_percent_min,
                                                           self.args.boss_stats_random_percent_max) / 100.0
                        value = int(stat_value * boss_stat_percent)
                        distorted_stat = max(min(value, 255), 0)
                        setattr(enemy, stat, distorted_stat)
                        print(f"DEBUG: Distorting {enemy.name}'s {stat} to {distorted_stat} (was {stat_value})")

            if enemy.name in hp_mp_exclude:
                print(f"No HP adjustment applied on enemy: {enemy.name}")
                distorted_hp = getattr(enemy, "hp")
            else:
                base_hp = getattr(enemy, "hp")
                distorted_hp = int(max(1, min(base_hp * random.randint(self.args.boss_distort_stats_percent_min,
                                                                   self.args.boss_distort_stats_percent_max) / 100.0,
                                          2 ** 16 - 1)))
                setattr(enemy, "hp", distorted_hp)
                print(f"DEBUG: Distorting {enemy.name}'s hp to {distorted_hp} (was {base_hp})")

            base_mp = getattr(enemy, "mp")
            distorted_mp = int(max(1, min(base_mp * random.randint(self.args.boss_distort_stats_percent_min,
                                                                   self.args.boss_distort_stats_percent_max) / 100.0,
                                          2 ** 16 - 1)))
            setattr(enemy, "mp", distorted_mp)
            print(f"DEBUG: Distorting {enemy.name}'s mp to {distorted_mp} (was {base_mp})")'''
    
    def boss_hpmp_randomize(self):
        import random
        
        # Exclude "child" bosses from HP distortion
        hp_mp_exclude = [321, 322, 320, 319, 325, 327, 269, 316, 317, 318, 333, 294, 352, 353, 354, 288, 289, 359, 326,
                         340]
        hp_mp_parents = {
            268: [321, 322],
            267: [319, 320],
            275: [325, 327],
            270: [269],
            283: [316, 317, 318],
            259: [333],
            291: [294, 352, 353, 354],
            287: [288, 289],
            290: [359]
        }

        # Create a reverse mapping of child to parent
        child_to_parent = {child: parent for parent, children in hp_mp_parents.items() for child in children}

        # Store distortion factors for parents
        parent_distortion = {}

        if self.args.boss_stats_random_percent_min != 100 or self.args.boss_stats_random_percent_max != 100:
            # First Pass: Process all non-excluded bosses and parents
            for enemy in self.bosses:
                if enemy.id not in hp_mp_exclude:
                    # Distort HP and MP for non-excluded enemies (including parents)
                    base_hp = getattr(enemy, "hp")
                    distorted_hp = int(max(1, min(base_hp * random.randint(self.args.boss_stats_random_percent_min,
                                                                           self.args.boss_stats_random_percent_max) / 100.0,
                                                  2 ** 16 - 1)))

                    base_mp = getattr(enemy, "mp")
                    distorted_mp = int(max(1, min(base_mp * random.randint(self.args.boss_stats_random_percent_min,
                                                                           self.args.boss_stats_random_percent_max) / 100.0,
                                                  2 ** 16 - 1)))

                    # Store distortion factors for parent bosses
                    if enemy.id in hp_mp_parents:
                        hp_multiplier = distorted_hp / enemy.hp if enemy.hp > 0 else 1
                        mp_multiplier = distorted_mp / enemy.mp if enemy.mp > 0 else 1
                        parent_distortion[enemy.id] = (distorted_hp, hp_multiplier, distorted_mp, mp_multiplier)
                        print(
                            f"Parent {enemy.name} (ID {enemy.id}) distortion: HP x{hp_multiplier}, MP x{mp_multiplier}")

                    # Apply distorted values
                    print(
                        f"DEBUG: {enemy.name}'s HP distorted to {distorted_hp} (was {enemy.hp}), MP distorted to {distorted_mp} (was {enemy.mp})")
                    setattr(enemy, "hp", distorted_hp)
                    setattr(enemy, "mp", distorted_mp)

            # Second Pass: Process child bosses based on their parent's distortion
            for enemy in self.bosses:
                if enemy.id in hp_mp_exclude:
                    parent_id = child_to_parent.get(enemy.id)
                    # Exception case for Ipooh (sets his HP to always be 50% of Vargas's HP)
                    if enemy.id == 333:
                        if parent_id in parent_distortion:
                            parent_distorted_hp = parent_distortion[parent_id][0]
                            distorted_hp = int(parent_distorted_hp / 2)
                            distorted_mp = enemy.mp  # Keep MP as is
                            print(
                                f"Special Case: Child {enemy.name} (ID {enemy.id}) HP set to 50% of parent's (ID {parent_id}) HP")

                    elif parent_id in parent_distortion:
                        _, hp_multiplier, _, mp_multiplier = parent_distortion[parent_id]
                        distorted_hp = int(enemy.hp * hp_multiplier)
                        distorted_mp = int(enemy.mp * mp_multiplier)
                        print(
                            f"Child {enemy.name} (ID {enemy.id}) inherits parent's (ID {parent_id}) distortion: HP x{hp_multiplier}, MP x{mp_multiplier}")
                    else:
                        distorted_hp, distorted_mp = enemy.hp, enemy.mp
                        print(f"No HP adjustment applied on child enemy: {enemy.name} (ID {enemy.id})")

                    # Apply distorted values
                    setattr(enemy, "hp", distorted_hp)
                    setattr(enemy, "mp", distorted_mp)
                    print(f"DEBUG: {enemy.name}'s HP distorted to {distorted_hp}, MP distorted to {distorted_mp}")

    def skip_shuffling_zone(self, maps, zone):
        if zone.MAP and zone.id >= maps.MAP_COUNT:
            return True  # do not shuffle map zones that do not correspond to a map

        if zone.MAP and not maps.properties[zone.id].enable_random_encounters:
            return True  # do not shuffle map zones with disabled random encounters

        return False

    def skip_shuffling_pack(self, pack, encounter_rate):
        from data.enemy_zone import EnemyZone

        if pack == 0 and encounter_rate == EnemyZone.NORMAL_ENCOUNTER_RATE:
            # 0 is used as a placeholder (leafer x1 and leafer x2, dark wind)
            # luckily the real ones outside narshe have lower encounter rates to differentiate them
            # except for the forest, does this cause problems?
            return True

        if pack == EnemyPacks.VELDT:
            return True

        if pack == EnemyPacks.ZONE_EATER:
            return True

        return False

    def skip_shuffling_formation(self, formation):
        if formation == EnemyFormations.PRESENTER:
            return True

        return False

    def shuffle_encounters(self, maps):
        import collections
        # find all packs that are randomly encountered in zones
        packs = collections.OrderedDict()
        for zone in self.zones.zones:
            if self.skip_shuffling_zone(maps, zone):
                continue

            for x in range(zone.PACK_COUNT):
                if self.skip_shuffling_pack(zone.packs[x], zone.encounter_rates[x]):
                    continue

                packs[self.packs.packs[zone.packs[x]]] = None

        # find all formations that are randomly encountered in packs
        formations = []
        for pack in packs:
            for y in range(pack.FORMATION_COUNT):
                if self.skip_shuffling_formation(pack.formations[y]):
                    continue

                if pack.extra_formations[y]:
                    # pack has extra formations (i.e. each formation is randomized with the subsequent 3 formations)
                    # unfortunately, this means there are more formations than packs to put them in, so some formations are lost
                    for x in range(4):
                        formations.append(pack.formations[y] + x)
                else:
                    formations.append(pack.formations[y])

        # shuffle the randomly encounterable formations
        import random
        random.shuffle(formations)

        for pack in packs:
            for y in range(pack.FORMATION_COUNT):
                if self.skip_shuffling_formation(pack.formations[y]):
                    continue

                pack.formations[y] = formations.pop()

        # NOTE: any remaining formations (due to extra_formations) are lost

    def chupon_encounters(self, maps):
        # find all packs that are randomly encountered in zones
        packs = []
        for zone in self.zones.zones:
            if self.skip_shuffling_zone(maps, zone):
                continue

            for x in range(zone.PACK_COUNT):
                if self.skip_shuffling_pack(zone.packs[x], zone.encounter_rates[x]):
                    continue

                packs.append(zone.packs[x])

        self.packs.chupon_packs(packs)

    def randomize_encounters(self, maps):
        # find all packs that are randomly encountered in zones
        packs = []
        boss_percent = self.args.random_encounters_random / 100.0
        for zone in self.zones.zones:
            if self.skip_shuffling_zone(maps, zone):
                continue

            for x in range(zone.PACK_COUNT):
                if self.skip_shuffling_pack(zone.packs[x], zone.encounter_rates[x]):
                    continue

                packs.append(zone.packs[x])

        self.packs.randomize_packs(packs, boss_percent)

    def randomize_loot(self):
        for enemy in self.enemies:
            self.set_common_steal(enemy.id, self.items.get_random())
            self.set_rare_steal(enemy.id, self.items.get_random())
            self.set_common_drop(enemy.id, self.items.get_random())
            self.set_rare_drop(enemy.id, self.items.get_random())

    def shuffle_steals_drops_random(self):
        import random
        from data.bosses import final_battle_enemy_name

        # Assemble the list of steals and drops
        steals_drops = []
        for enemy in self.enemies:
            if len(enemy.name) > 0:
                loot_list = [enemy.steal_common, enemy.steal_rare]
                if enemy.id not in final_battle_enemy_name.keys():
                    loot_list += [enemy.drop_common, enemy.drop_rare]
                steals_drops.extend(loot_list)

        # Randomize the requested number
        random_percent = self.args.shuffle_steals_drops_random_percent / 100.0
        number_random = int(random_percent * len(steals_drops))
        which_random = [a for a in range(len(steals_drops))]
        random.shuffle(which_random)
        for id in range(number_random):
            steals_drops[which_random[id]] = self.items.get_random()

        # Shuffle list & reassign to enemies
        random.shuffle(steals_drops)
        for enemy in self.enemies:
            if len(enemy.name) > 0:
                self.set_common_steal(enemy.id, steals_drops.pop(0))
                self.set_rare_steal(enemy.id, steals_drops.pop(0))
                if enemy.id not in final_battle_enemy_name.keys():
                    self.set_common_drop(enemy.id, steals_drops.pop(0))
                    self.set_rare_drop(enemy.id, steals_drops.pop(0))

    def set_escapable(self):
        import random

        escapable_percent = self.args.encounters_escapable_random / 100.0
        for enemy in self.enemies:
            if enemy.id in bosses.enemy_name or enemy.id == self.SRBEHEMOTH2_ID or enemy.id == self.INVINCIBLE_GUARDIAN_ID:
                continue

            enemy.no_run = random.random() >= escapable_percent

    def no_undead_bosses(self):
        boss_ids = list(bosses.enemy_name.keys())
        boss_ids.append(self.SRBEHEMOTH2_ID)

        for boss_id in boss_ids:
            self.enemies[boss_id].undead = False

    def scan_all(self):
        for enemy in self.enemies:
            enemy.no_scan = 0

    def mod(self, maps):
        '''if self.args.boss_rebalance_distort_stats:
            self.boss_rebalance_distort_stats()'''

        if self.args.shuffle_steals_drops:
            self.shuffle_steals_drops_random()

        if self.args.permadeath:
            self.remove_fenix_downs()

        self.apply_scaling()

        if self.args.balance_boss_stats:
            self.boss_rebalance_stats()
            self.boss_rebalance_hpmp()

        if self.args.boss_stats_random_percent:
            self.boss_stats_randomize()
            self.boss_hpmp_randomize()

        if self.args.boss_experience:
            self.boss_experience()

        if not self.args.encounters_escapable_original:
            self.set_escapable()

        if self.args.boss_no_undead:
            self.no_undead_bosses()

        if self.args.random_encounters_shuffle:
            self.shuffle_encounters(maps)
        elif self.args.random_encounters_chupon:
            self.chupon_encounters(maps)
        elif not self.args.random_encounters_original:
            self.randomize_encounters(maps)

        self.formations.mod()
        self.packs.mod()
        self.zones.mod()
        self.scripts.mod()

        if self.args.scan_all:
            self.scan_all()

        if self.args.debug:
            for enemy in self.enemies:
                enemy.debug_mod()

    def get_event_boss(self, original_boss_name):
        return self.packs.get_event_boss_replacement(original_boss_name)

    def print(self):
        for enemy in self.enemies:
            enemy.print()

    def write(self):
        for enemy_index in range(len(self.enemies)):
            self.enemy_data[enemy_index] = self.enemies[enemy_index].data()
            self.enemy_name_data[enemy_index] = self.enemies[enemy_index].name_data()
            self.enemy_item_data[enemy_index] = self.enemies[enemy_index].item_data()
            self.enemy_special_name_data[enemy_index] = self.enemies[enemy_index].special_name_data()

        self.enemy_data.write()
        self.enemy_name_data.write()
        self.enemy_item_data.write()
        self.enemy_special_name_data.write()

        self.formations.write()
        self.packs.write()
        self.zones.write()
        self.scripts.write()
