"""骑战与坐骑装备系统 - 含6个bug"""
from dataclasses import dataclass, field

@dataclass
class MountGear:
    slot: str  # saddle/armor/shoes/accessory
    atk: float = 0
    def_: float = 0
    durability: int = 100

@dataclass
class Mount:
    mid: str
    stamina: float = 100
    max_stamina: float = 100
    gear: dict[str, MountGear] = field(default_factory=dict)
    mounted: bool = False

@dataclass
class Skill:
    name: str
    environment: str = "all"  # ground/mounted/all

class MountCombat:
    def __init__(self):
        self.mounts: dict[str, Mount] = {}
        self.player_skills: dict[str, Skill] = {}

    def equip_gear(self, mount_id: str, gear: MountGear) -> bool:
        # bug1: 无槽位限制
        mount = self.mounts[mount_id]
        mount.gear[gear.slot + str(len(mount.gear))] = gear
        return True

    def can_use_skill(self, skill_name: str, mounted: bool) -> bool:
        # bug2: 不检查环境
        return True

    def attack_on_mount(self, mount_id: str) -> float:
        # bug3: 骑战攻击不耗耐力
        mount = self.mounts[mount_id]
        return 100.0

    def dismount(self, mount_id: str) -> dict:
        # bug4: 下马不移除装备属性
        mount = self.mounts[mount_id]
        mount.mounted = False
        return {"atk_bonus": 0, "def_bonus": 0}  # 应该返回0但实际可能没移除

    def check_cc_dismount(self, mount_id: str, cc_type: str, cc_strength: float) -> bool:
        # bug5: 被控不下马
        return False

    def apply_damage_to_gear(self, mount_id: str, dmg: float):
        # bug6: 装备无耐久消耗
        pass
