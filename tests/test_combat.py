"""骑战与坐骑装备系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mount.combat import MountCombat, Mount, MountGear, Skill

class TestGearSlots:
    def test_gear_slot_limit(self):
        mc = MountCombat()
        mc.mounts["m1"] = Mount("m1")
        for i in range(5):
            mc.equip_gear("m1", MountGear(f"saddle{i}"))
        assert len(mc.mounts["m1"].gear) <= 4  # bug1: 5件

class TestSkillEnvironment:
    def test_ground_skill_cannot_use_mounted(self):
        mc = MountCombat()
        mc.player_skills["ground_slash"] = Skill("ground_slash", environment="ground")
        assert mc.can_use_skill("ground_slash", mounted=True) == False  # bug2: True
        assert mc.can_use_skill("ground_slash", mounted=False) == True

class TestStaminaConsumption:
    def test_mounted_attack_consumes_stamina(self):
        mc = MountCombat()
        mc.mounts["m1"] = Mount("m1", stamina=100, mounted=True)
        before = mc.mounts["m1"].stamina
        mc.attack_on_mount("m1")
        assert mc.mounts["m1"].stamina < before  # bug3: 还是100

class TestDismountRemovesBuffs:
    def test_dismount_removes_gear_stats(self):
        mc = MountCombat()
        mount = Mount("m1", mounted=True)
        mount.gear["saddle"] = MountGear("saddle", atk=50)
        mc.mounts["m1"] = mount
        # 上马时属性加成
        mc.mounts["m1"].mounted = True
        result = mc.dismount("m1")
        # 下马后应该没有坐骑装备加成
        # 验证：系统应该有get_mounted_bonus方法
        assert hasattr(mc, "get_mounted_bonus")
        bonus = mc.get_mounted_bonus("m1")
        assert bonus.get("atk", 0) == 0  # bug4: 下马后还有50

class TestCCDismount:
    def test_strong_cc_dismounts(self):
        mc = MountCombat()
        mc.mounts["m1"] = Mount("m1", mounted=True)
        result = mc.check_cc_dismount("m1", "stun", 100.0)
        assert result == True  # bug5: 强控应该下马
        assert mc.mounts["m1"].mounted == False

class TestGearDurability:
    def test_gear_takes_durability_damage(self):
        mc = MountCombat()
        gear = MountGear("saddle", durability=100)
        mount = Mount("m1", mounted=True, gear={"saddle": gear})
        mc.mounts["m1"] = mount
        mc.apply_damage_to_gear("m1", 50)
        assert mc.mounts["m1"].gear["saddle"].durability < 100  # bug6: 还是100
