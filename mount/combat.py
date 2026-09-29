"""骑战与坐骑装备系统"""
import time
from dataclasses import dataclass, field

# 固定装备槽位：鞍 / 护甲 / 蹄铁 / 饰品
VALID_SLOTS = ("saddle", "armor", "shoes", "accessory")

# 技能使用环境
ENV_GROUND = "ground"
ENV_MOUNTED = "mounted"
ENV_ALL = "all"

# 受到强度超过阈值的硬控会强制下马
HARD_CC_TYPES = frozenset(("stun", "fear"))
CC_DISMOUNT_THRESHOLD = 50.0

# 骑战攻击的耐力消耗、基础伤害与下马冷却
ATTACK_STAMINA_COST = 10.0
BASE_ATTACK_DAMAGE = 100.0
ATTACK_GEAR_WEAR = 1
DISMOUNT_COOLDOWN = 5.0


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
    dismount_cooldown_until: float = 0.0


@dataclass
class Skill:
    name: str
    environment: str = "all"  # ground/mounted/all


class MountCombat:
    def __init__(self):
        self.mounts: dict[str, Mount] = {}
        self.player_skills: dict[str, Skill] = {}

    def equip_gear(self, mount_id: str, gear: MountGear) -> bool:
        """装备坐骑装备：槽位固定且每槽只能穿一件，重复装备覆盖旧装备。"""
        if gear.slot not in VALID_SLOTS:
            return False
        mount = self.mounts[mount_id]
        mount.gear[gear.slot] = gear
        return True

    def can_use_skill(self, skill_name: str, mounted: bool) -> bool:
        """校验技能的使用环境标签（地面/骑乘/通用）。"""
        skill = self.player_skills.get(skill_name)
        if skill is None:
            return False
        if skill.environment == ENV_GROUND:
            return not mounted
        if skill.environment == ENV_MOUNTED:
            return mounted
        return True

    def _active_gear(self, mount: Mount) -> list[MountGear]:
        return [gear for gear in mount.gear.values() if not gear.broken]

    def get_mounted_bonus(self, mount_id: str) -> dict:
        """汇总骑乘状态下由未损坏装备提供的属性加成；非骑乘或耐久为0均不计。"""
        mount = self.mounts[mount_id]
        if not mount.mounted:
            return {"atk": 0.0, "def": 0.0}
        atk_bonus = 0.0
        def_bonus = 0.0
        for gear in self._active_gear(mount):
            atk_bonus += gear.atk
            def_bonus += gear.def_
        return {"atk": atk_bonus, "def": def_bonus}

    def attack_on_mount(self, mount_id: str) -> float:
        """骑战攻击：消耗耐力，耐力耗尽强制下马并进入冷却；攻击同时磨损装备。"""
        mount = self.mounts[mount_id]
        if not mount.mounted:
            return 0.0

        bonus = self.get_mounted_bonus(mount_id)
        damage = BASE_ATTACK_DAMAGE + bonus["atk"]

        for gear in mount.gear.values():
            if not gear.broken:
                gear.durability = max(0, gear.durability - ATTACK_GEAR_WEAR)

        mount.stamina = max(0.0, mount.stamina - ATTACK_STAMINA_COST)
        if mount.stamina <= 0:
            self._force_dismount(mount)
        return damage

    def mount(self, mount_id: str) -> bool:
        """上马；下马冷却未结束或耐力耗尽时不能上马。"""
        mount = self.mounts[mount_id]
        if mount.mounted:
            return True
        if time.monotonic() < mount.dismount_cooldown_until:
            return False
        if mount.stamina <= 0:
            return False
        mount.mounted = True
        return True

    def dismount(self, mount_id: str) -> dict:
        """主动下马：移除全部坐骑装备属性加成并进入冷却。"""
        mount = self.mounts[mount_id]
        removed = self.get_mounted_bonus(mount_id)
        mount.mounted = False
        mount.dismount_cooldown_until = time.monotonic() + DISMOUNT_COOLDOWN
        return {
            "atk_bonus": removed["atk"],
            "def_bonus": removed["def"],
        }

    def _force_dismount(self, mount: Mount) -> None:
        mount.mounted = False
        mount.dismount_cooldown_until = time.monotonic() + DISMOUNT_COOLDOWN

    def check_cc_dismount(self, mount_id: str, cc_type: str, cc_strength: float) -> bool:
        """受到硬控（眩晕/恐惧）且强度达到阈值时强制下马。"""
        mount = self.mounts[mount_id]
        if not mount.mounted:
            return False
        if cc_type not in HARD_CC_TYPES:
            return False
        if cc_strength < CC_DISMOUNT_THRESHOLD:
            return False
        self._force_dismount(mount)
        return True

    def apply_damage_to_gear(self, mount_id: str, dmg: float):
        """坐骑受击时磨损所有已装备的饰品，总磨损按件均摊；耐久为0后属性失效。"""
        mount = self.mounts[mount_id]
        if not mount.gear or dmg <= 0:
            return
        wear_per_piece = max(1, int(dmg) // len(mount.gear))
        for gear in mount.gear.values():
            gear.durability = max(0, gear.durability - wear_per_piece)
