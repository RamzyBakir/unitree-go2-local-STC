import logging
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from . import config

logger = logging.getLogger(__name__)


class RobotController:
    def __init__(self):
        self._client: SportClient | None = None
        self._connected = False

    def connect(self) -> bool:
        if config.MOCK_MODE:
            logger.info("Mock mode enabled — skipping DDS initialization")
            self._connected = True
            return True

        try:
            if config.NETWORK_INTERFACE:
                ChannelFactoryInitialize(0, config.NETWORK_INTERFACE)
            else:
                ChannelFactoryInitialize(0)

            self._client = SportClient()
            self._client.SetTimeout(config.ROBOT_TIMEOUT)
            self._client.Init()
            self._connected = True
            logger.info(
                "Connected to Go2 via DDS on interface '%s'",
                config.NETWORK_INTERFACE or "default",
            )
            return True
        except Exception as e:
            logger.error("Failed to connect to Go2: %s", e)
            self._connected = False
            return False

    @property
    def connected(self) -> bool:
        return self._connected

    def _call(self, method_name: str, *args, **kwargs):
        if config.MOCK_MODE:
            logger.info("[MOCK] Would call %s(%s %s)", method_name, args, kwargs)
            return 0

        if not self._connected or self._client is None:
            raise RuntimeError("Robot not connected")

        method = getattr(self._client, method_name)
        result = method(*args, **kwargs)
        if isinstance(result, tuple):
            return result[0]
        return result

    def damp(self):
        return self._call("Damp")

    def balance_stand(self):
        return self._call("BalanceStand")

    def stop_move(self):
        return self._call("StopMove")

    def stand_up(self):
        return self._call("StandUp")

    def stand_down(self):
        return self._call("StandDown")

    def recovery_stand(self):
        return self._call("RecoveryStand")

    def sit(self):
        return self._call("Sit")

    def rise_sit(self):
        return self._call("RiseSit")

    def hello(self):
        return self._call("Hello")

    def stretch(self):
        return self._call("Stretch")

    def heart(self):
        return self._call("Heart")

    def content(self):
        return self._call("Content")

    def dance1(self):
        return self._call("Dance1")

    def dance2(self):
        return self._call("Dance2")

    def scrape(self):
        return self._call("Scrape")

    def front_flip(self):
        return self._call("FrontFlip")

    def back_flip(self):
        return self._call("BackFlip")

    def left_flip(self):
        return self._call("LeftFlip")

    def front_jump(self):
        return self._call("FrontJump")

    def front_pounce(self):
        return self._call("FrontPounce")

    def hand_stand(self, flag: bool = True):
        return self._call("HandStand", flag)

    def move(self, vx: float, vy: float, vyaw: float):
        return self._call("Move", vx, vy, vyaw)

    def euler(self, roll: float, pitch: float, yaw: float):
        return self._call("Euler", roll, pitch, yaw)

    def speed_level(self, level: int):
        return self._call("SpeedLevel", level)

    def free_walk(self):
        return self._call("FreeWalk")

    def free_bound(self, flag: bool = True):
        return self._call("FreeBound", flag)

    def free_jump(self, flag: bool = True):
        return self._call("FreeJump", flag)

    def free_avoid(self, flag: bool = True):
        return self._call("FreeAvoid", flag)

    def walk_upright(self, flag: bool = True):
        return self._call("WalkUpright", flag)

    def cross_step(self, flag: bool = True):
        return self._call("CrossStep", flag)

    def classic_walk(self, flag: bool = True):
        return self._call("ClassicWalk", flag)

    def static_walk(self):
        return self._call("StaticWalk")

    def trot_run(self):
        return self._call("TrotRun")

    def economic_gait(self):
        return self._call("EconomicGait")
