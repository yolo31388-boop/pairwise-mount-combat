"""骑战与坐骑装备系统"""
from dataclasses import dataclass, field

VALID_SLOTS = ("saddle", "armor", "shoes", "accessory")

MOUNT_ATTACK_STAMINA_COST = 10.0
MOUNT_ATTACK_GEAR_WEAR = 1
STAMINA_EXHAUST_COOLDOWN = 5.0

HARD_CC_TYPES = ("stun", "fear")
CC_DISMOUNT_THRESHOLD = 50.0


@dataclass
class MountGear:
    slot: str  # saddle/armor/shoes/accessory
    atk: float = 0
    def_: float = 0
    durability: int = 100

    @property
    def broken(self) -> bool:
        return self.durability <= 0


@dataclass
class Mount:
    mid: str
    stamina: float = 100
    max_stamina: float = 100
    gear: dict[str, MountGear] = field(default_factory=dict)
    mounted: bool = False
    remount_cooldown: float = 0.0


@dataclass
class Skill:
    name: str
    environment: str = "all"  # ground/mounted/all


class MountCombat:
    def __init__(self):
        self.mounts: dict[str, Mount] = {}
        self.player_skills: dict[str, Skill] = {}

    def equip_gear(self, mount_id: str, gear: MountGear) -> bool:
        # fix1: 固定槽位（鞍/护甲/蹄铁/饰品），每槽一件
        if gear.slot not in VALID_SLOTS:
            return False
        mount = self.mounts[mount_id]
        mount.gear[gear.slot] = gear
        return True

    def can_use_skill(self, skill_name: str, mounted: bool) -> bool:
        # fix2: 技能环境标签校验，环境不匹配不能放
        skill = self.player_skills.get(skill_name)
        if skill is None:
            return False
        if skill.environment == "all":
            return True
        if skill.environment == "mounted":
            return mounted
        if skill.environment == "ground":
            return not mounted
        return False

    def attack_on_mount(self, mount_id: str) -> float:
        # fix3: 骑战攻击耗耐力，耐力耗尽自动下马并进入冷却
        mount = self.mounts[mount_id]
        if not mount.mounted or mount.stamina < MOUNT_ATTACK_STAMINA_COST:
            return 0.0
        mount.stamina -= MOUNT_ATTACK_STAMINA_COST
        self._wear_gear(mount, MOUNT_ATTACK_GEAR_WEAR)
        if mount.stamina <= 0:
            mount.stamina = 0
            self._force_dismount(mount)
            mount.remount_cooldown = STAMINA_EXHAUST_COOLDOWN
        bonus = self.get_mounted_bonus(mount_id)
        return 100.0 + bonus["atk"]

    def dismount(self, mount_id: str) -> dict:
        # fix4: 下马完整移除坐骑属性加成（get_mounted_bonus 仅在骑乘时计算）
        mount = self.mounts[mount_id]
        mount.mounted = False
        return {"atk_bonus": 0, "def_bonus": 0}

    def get_mounted_bonus(self, mount_id: str) -> dict:
        # 上马时重新计算；耐久为0的装备属性失效
        mount = self.mounts[mount_id]
        bonus = {"atk": 0.0, "def": 0.0}
        if not mount.mounted:
            return bonus
        for gear in mount.gear.values():
            if gear.broken:
                continue
            bonus["atk"] += gear.atk
            bonus["def"] += gear.def_
        return bonus

    def check_cc_dismount(self, mount_id: str, cc_type: str, cc_strength: float) -> bool:
        # fix5: 硬控（眩晕/恐惧）且强度达到阈值时强制下马
        mount = self.mounts[mount_id]
        if not mount.mounted:
            return False
        if cc_type in HARD_CC_TYPES and cc_strength >= CC_DISMOUNT_THRESHOLD:
            self._force_dismount(mount)
            return True
        return False

    def apply_damage_to_gear(self, mount_id: str, dmg: float):
        # fix6: 骑战中受击消耗装备耐久，耐久0属性失效
        mount = self.mounts[mount_id]
        wear = max(1, int(dmg / 10))
        self._wear_gear(mount, wear)

    def _wear_gear(self, mount: Mount, wear: int):
        for gear in mount.gear.values():
            gear.durability = max(0, gear.durability - wear)

    def _force_dismount(self, mount: Mount):
        mount.mounted = False
