import asyncio
import json
import random
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

# ================= 枚举与配置 =================
class Weather(Enum): SUNNY, RAINY, STORMY, SNOWY = range(4)
class TimeOfDay(Enum): MORNING, AFTERNOON, EVENING, NIGHT = range(4)

# ================= 记忆系统 =================
@dataclass
class Memory:
    content: str
    timestamp: float
    importance: float  # 0.0~1.0
    tags: List[str] = field(default_factory=list)

class MemoryBank:
    def __init__(self, cap_short=12, cap_long=150):
        self.short_term: List[str] = []
        self.long_term: List[Memory] = []
        self.cap_short = cap_short
        self.cap_long = cap_long

    def add_short(self, event: str):
        self.short_term.append(event)
        if len(self.short_term) > self.cap_short:
            self.short_term.pop(0)

    def add_long(self, content: str, importance: float, tags: List[str]):
        self.long_term.append(Memory(content, time.time(), importance, tags))
        self._consolidate()

    def _consolidate(self):
        now = time.time()
        for m in self.long_term:
            age_days = (now - m.timestamp) / 86400
            m.importance *= math.exp(-0.15 * age_days)  # 记忆衰减曲线
        self.long_term = [m for m in self.long_term if m.importance > 0.05]
        self.long_term.sort(key=lambda x: x.importance, reverse=True)
        if len(self.long_term) > self.cap_long:
            self.long_term = self.long_term[:self.cap_long]

    def get_context(self) -> str:
        recent = "\n".join(self.short_term[-6:])
        significant = "\n".join([f"- {m.content}" for m in self.long_term[:6]])
        return f"【近期经历】\n{recent}\n【深刻记忆】\n{significant}"

# ================= 关系与八卦网络 =================
class RelationshipMatrix:
    def __init__(self):
        self.relations: Dict[str, Dict[str, float]] = {}

    def get_score(self, a: str, b: str) -> float:
        return self.relations.get(a, {}).get(b, 0.0)

    def update(self, a: str, b: str, delta: float):
        self.relations.setdefault(a, {})
        self.relations[a][b] = max(-100.0, min(100.0, self.relations[a].get(b, 0.0) + delta))

    def process_gossip(self, speaker: str, listener: str, topic: str, sentiment: float) -> str:
        # 情感对齐：听众对说话者的好感度受八卦立场影响
        alignment = random.uniform(0.6, 1.4) * sentiment
        self.update(listener, speaker, alignment * 0.4)
        # 八卦失真传播
        distortion = random.choice(["", "（添油加醋）", "（半信半疑）", "（深信不疑）"])
        return f"{topic} {distortion}"

# ================= LLM 客户端（可无缝替换真实API） =================
class LLMClient:
    def __init__(self, model="gpt-4o-mini", rate_limit=20):
        self.model = model
        self.token_count = 0
        self.semaphore = asyncio.Semaphore(rate_limit)  # 防击穿限流

    async def generate(self, prompt: str, system: str) -> str:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(0.05, 0.2))  # 模拟网络延迟
            # 真实环境替换为 openai.AsyncOpenAI().chat.completions.create(...)
            input_tk = len(prompt.split()) + len(system.split())
            self.token_count += input_tk

            # 模拟结构化输出
            goals = ["去酒馆买醉", "去铁匠铺修武器", "在广场散布谣言", "回家睡觉", "寻找玩家复仇", "和邻居交换情报"]
            actions = ["move_to_location", "interact_npc", "use_object", "idle", "start_gossip"]
            plan = {
                "goal": random.choice(goals),
                "action_queue": random.sample(actions, k=random.randint(1, 3)),
                "reasoning": f"结合性格与近期事件，决定执行该目标"
            }
            res = json.dumps(plan, ensure_ascii=False)
            self.token_count += len(res.split())
            return res

# ================= NPC 智能体 =================
@dataclass
class NPCState:
    npc_id: str
    name: str
    personality: str
    location: str
    health: float = 100.0
    mood: str = "neutral"

class NPCAgent:
    def __init__(self, state: NPCState, llm: LLMClient, rel_matrix: RelationshipMatrix):
        self.state = state
        self.memory = MemoryBank()
        self.llm = llm
        self.relations = rel_matrix
        self.action_queue: List[str] = []
        self.current_goal: str = "idle"
        self.is_alive = True

    def perceive_environment(self, env_state: dict) -> str:
        return f"时间:{env_state['time']} | 天气:{env_state['weather']} | 位置:{self.state.location} | 附近NPC:{env_state.get('nearby_npcs', [])}"

    async def think_and_plan(self, env_state: dict):
        if not self.is_alive: return
        context = self.memory.get_context()
        perception = self.perceive_environment(env_state)
        sys_prompt = f"你是{self.state.name}，性格：{self.state.personality}。你是一个开放世界NPC，拥有自主目标与长期记忆。根据环境、记忆和性格，生成下一步目标与行动序列。必须输出严格JSON。"
        usr_prompt = f"环境感知:\n{perception}\n记忆上下文:\n{context}\n当前情绪: {self.state.mood}"

        try:
            raw = await self.llm.generate(usr_prompt, sys_prompt)
            plan = json.loads(raw)
            self.current_goal = plan["goal"]
            self.action_queue = plan["action_queue"]
            self.memory.add_short(f"🎯 确立目标: {self.current_goal}")
        except Exception:
            self.action_queue = ["idle"]
            self.current_goal = "fallback_idle"

    async def execute_action(self, env_state: dict):
        if not self.action_queue:
            await self.think_and_plan(env_state)
            return

        action = self.action_queue.pop(0)
        locations = ["酒馆", "广场", "铁匠铺", "森林", "家", "市场", "教堂"]
        if action == "move_to_location":
            self.state.location = random.choice(locations)
            self.memory.add_short(f"📍 移动至 {self.state.location}")
        elif action in ("interact_npc", "start_gossip"):
            pass  # 由交互管理器触发
        elif action == "use_object":
            self.memory.add_short("🔧 使用环境物件")
        else:
            self.memory.add_short("🛋️ 休息/观察")

    async def interact(self, other: 'NPCAgent'):
        topics = ["玩家的暴行", "镇长贪污", "最近的怪天气", "物价飞涨", "森林里的异响"]
        topic = random.choice(topics)
        sentiment = random.uniform(-1.0, 1.0)
        distorted = self.relations.process_gossip(self.state.npc_id, other.state.npc_id, topic, sentiment)
        other.memory.add_long(f"听{self.state.name}说: {distorted}", importance=0.65, tags=["gossip"])
        self.memory.add_short(f"🗣️ 与{other.state.name}交换情报: {topic}")

        rel = self.relations.get_score(self.state.npc_id, other.state.npc_id)
        self.state.mood = "happy" if rel > 40 else "angry" if rel < -40 else "neutral"

# ================= 环境与模拟引擎 =================
class GameEnvironment:
    def __init__(self):
        self.time_hour = 8
        self.weather = Weather.SUNNY
        self.tick = 0

    def advance(self):
        self.tick += 1
        self.time_hour = (self.time_hour + 1) % 24
        if random.random() < 0.12:
            self.weather = random.choice(list(Weather))

    def get_state(self, npc_loc: str, all_npcs: List[NPCAgent]) -> dict:
        nearby = [n.state.npc_id for n in all_npcs if n.state.location == npc_loc and n.is_alive]
        t = self.time_hour
        tod = TimeOfDay.MORNING.name if 6<=t<12 else TimeOfDay.AFTERNOON.name if 12<=t<18 else TimeOfDay.EVENING.name if 18<=t<22 else TimeOfDay.NIGHT.name
        return {"time": tod, "weather": self.weather.name, "nearby_npcs": nearby}

class SimulationEngine:
    def __init__(self, num_npcs=50):
        self.llm = LLMClient(rate_limit=25)
        self.rel_matrix = RelationshipMatrix()
        self.env = GameEnvironment()
        self.npcs: List[NPCAgent] = []
        self._spawn_npcs(num_npcs)

    def _spawn_npcs(self, count: int):
        personalities = ["乐观的酒鬼", "阴郁的铁匠", "八卦的农妇", "谨慎的商人", "暴躁的佣兵", "神秘的学者", "虔诚的牧师"]
        locations = ["酒馆", "广场", "铁匠铺", "森林", "家", "市场", "教堂"]
        for i in range(count):
            state = NPCState(
                npc_id=f"npc_{i:02d}",
                name=f"村民{i}",
                personality=random.choice(personalities),
                location=random.choice(locations)
            )
            self.npcs.append(NPCAgent(state, self.llm, self.rel_matrix))

    async def run_tick(self):
        self.env.advance()
        # 1. 并行感知与规划
        plan_tasks = [npc.think_and_plan(self.env.get_state(npc.state.location, self.npcs)) for npc in self.npcs]
        await asyncio.gather(*plan_tasks, return_exceptions=True)

        # 2. 并行执行与社交
        exec_tasks = []
        for npc in self.npcs:
            env_st = self.env.get_state(npc.state.location, self.npcs)
            exec_tasks.append(npc.execute_action(env_st))
            if env_st["nearby_npcs"] and random.random() < 0.35:
                target_id = random.choice(env_st["nearby_npcs"])
                target = next((n for n in self.npcs if n.state.npc_id == target_id), None)
                if target and target != npc:
                    exec_tasks.append(npc.interact(target))
        await asyncio.gather(*exec_tasks, return_exceptions=True)

    async def simulate(self, total_ticks=100, log_interval=10):
        print(f"🚀 启动自主NPC行为引擎 | 规模: {len(self.npcs)} NPCs | 并发架构: asyncio")
        for t in range(total_ticks):
            await self.run_tick()
            if t % log_interval == 0:
                print(f"⏱️ Tick {t} | {self.env.time_hour}:00 | 天气:{self.env.weather.name} | Token累计:{self.llm.token_count}")
                sample = random.choice([n for n in self.npcs if n.is_alive])
                print(f"📜 [{sample.state.name}] 目标:{sample.current_goal} | 位置:{sample.state.location} | 情绪:{sample.state.mood}")
        daily_est = self.llm.token_count * (24 / max(total_ticks, 1))
        print(f"✅ 模拟结束。总Token:{self.llm.token_count} | 日均估算: ~{daily_est:.0f} (目标: 600万)")

if __name__ == "__main__":
    engine = SimulationEngine(num_npcs=50)
    asyncio.run(engine.simulate(total_ticks=60, log_interval=5))
