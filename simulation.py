import sys
import asyncio
import random
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger
from typing import AsyncGenerator

# Log formatting
def log_format(record):
    level = record["level"].name.rjust(4)
    source = record["extra"].get("source", "???")
    return f"{record['time']:YYYY-MM-DD HH:mm:ss} | {level} | [{source}] {record['message']}\n"

logger.remove()
logger.add(sys.stderr, format=log_format, level="INFO")


type Call = int
type RoutingFn = callable[[list["Responder"]], "Responder"]
type CallGenerator = callable[[], AsyncGenerator[Call, None]]

class Responder:
    def __init__(self, name: str, buffer_size: int, mu: float, break_threshold: int, break_time: float, data: dict) -> None:
        self.name = name
        self.queue = asyncio.Queue(maxsize=buffer_size)
        self.mean_handling_time = mu
        self.break_threshold = break_threshold
        self.break_time = break_time

        self.processed = 0
        self.rejected = 0
        self.calls_since_break = 0
        self.data = data  # Store data for visualization

    async def receive(self, call: Call) -> None:
        if self.queue.full():
            self.rejected += 1
            logger.info(f"❌ Rejected call {call:>3} (queue full)", source=self.name)
            return
        logger.debug(f"Queueing call {call}", source=self.name)
        await self.queue.put(call)

    async def simulate_handling_call(self) -> float:
        handling_time = np.random.exponential(self.mean_handling_time)
        await asyncio.sleep(handling_time)
        return handling_time

    async def take_break(self) -> None:
        logger.info(f"💤 {self.name} is taking a break for {self.break_time} seconds.", source=self.name)
        await asyncio.sleep(self.break_time)
        self.calls_since_break = 0

    async def run(self) -> None:
        while True:
            call = await self.queue.get()
            handling_time = await self.simulate_handling_call()

            self.processed += 1
            self.calls_since_break += 1
            self.queue.task_done()

            self.data[self.name]["queue_lengths"].append(self.queue.qsize())
            self.data[self.name]["handling_times"].append(handling_time)

            logger.info(f"✅ Handled call {call:>3} ({handling_time:.2f}s)", source=self.name)

            if self.calls_since_break >= self.break_threshold:
                await self.take_break()

def route_random(servers: list[Responder]) -> Responder:
    return random.choice(servers)

def route_shortest_queue(servers: list[Responder]) -> Responder:
    return min(servers, key=lambda s: s.queue.qsize())

def create_calls_generator_poisson(lambda_: float) -> CallGenerator:
    async def generator():
        call = 0
        while True:
            logger.debug(f"Created call {call}", source="GEN")
            yield call
            call += 1
            wait_time = np.random.exponential(1/lambda_)
            await asyncio.sleep(wait_time)
    return generator

async def assign_calls(
    responders: list[Responder],
    routing_fn: RoutingFn,
    call_generator: CallGenerator
) -> None:
    async for call in call_generator():
        responder = routing_fn(responders)  # Determine which responder to assign the call
        logger.debug(f"Assigning call {call} to {responder.name}", source="ASSIGN")
        await responder.receive(call)

async def simulate(
    num_responders: int,
    buffer_size: int,
    mu: float,
    break_threshold: int,
    break_time: float,
    routing_fn: RoutingFn,
    call_generator: CallGenerator,
    simulation_time: int,
) -> dict:
    print(f"\nStarting simulation with routing policy: {routing_fn.__name__}")

    data = {f"Responder-{i+1}": {"queue_lengths": [], "handling_times": []} for i in range(num_responders)}

    responders = [Responder(f"Responder-{i+1}", buffer_size, mu, break_threshold, break_time, data)
                  for i in range(num_responders)]

    processes = [
        assign_calls(responders, routing_fn, call_generator),
        *[responder.run() for responder in responders]
    ]
    tasks = [asyncio.create_task(process) for process in processes]

    await asyncio.sleep(simulation_time)

    for task in tasks:
        task.cancel()

    total_processed = sum(responder.processed for responder in responders)
    total_rejected = sum(responder.rejected for responder in responders)

    print(f"\nPolicy: {routing_fn.__name__}")
    print(f"Total calls handled: {total_processed}")
    print(f"Total calls rejected: {total_rejected}")
    print(f"Calls in queues: {sum(responder.queue.qsize() for responder in responders)}")

    return data  # Return the collected data for visualization

# Function to plot the collected data
def plot_simulation_data(data, policy_name):
    plt.figure(figsize=(10, 6))

    for responder_name, stats in data.items():
        plt.plot(stats["queue_lengths"], label=f"{responder_name} Queue Length")

    plt.title(f"Queue Length Over Time ({policy_name})")
    plt.xlabel("Time (arbitrary units)")
    plt.ylabel("Queue Length")
    plt.legend()
    plt.show()

async def main():
    params = dict(
        num_responders=3,
        buffer_size=10,
        mu=1.5,  # Average handling time in seconds
        break_threshold=5,  # Number of calls before a break
        break_time=10,  # Break time in seconds
        call_generator=create_calls_generator_poisson(lambda_=4),  # Average calls per second
        simulation_time=10,
    )

    # Simulate with random routing policy
    data_random = await simulate(**params, routing_fn=route_random)
    plot_simulation_data(data_random, "Random Routing")

    # Simulate with shortest queue routing policy
    data_shortest = await simulate(**params, routing_fn=route_shortest_queue)
    plot_simulation_data(data_shortest, "Shortest Queue Routing")

if __name__ == '__main__':
    asyncio.run(main())