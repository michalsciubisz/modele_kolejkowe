import asyncio
import numpy as np
import matplotlib.pyplot as plt


type Call = int

class Consultant:
    def __init__(self, name: str, buffer_size: int, mu: float, break_threshold: int, data: dict) -> None:
        self.name = name 
        self.queue = asyncio.Queue(maxsize=buffer_size)
        self.mean_call_handling_time = mu
        self.break_threshold = break_threshold
        

        self.processed = 0
        self.rejected = 0
        self.calls_since_break = 0
        self.data = data

    async def receive(self, call: Call) -> None:
        """
        Function which handles receiving call. If there is slot in queue then add new call to queue, in other case reject the call.
        """
        if self.queue.full():
            self.rejected += 1
            return
        await self.queue.put(call) 

    async def sim_handling_call(self) -> float:
        """
        Function which randomly generate handling call time based on exponential distribution and mean call time.
        """
        handling_time = np.random.exponential(self.mean_call_handling_time)
        await asyncio.sleep(handling_time)
        return handling_time
    
    async def take_break(self) -> None:
        """
        Function which stops the responder for specific amount of time based on how much calls he have handled so far.
        """
        handled_calls = self.data[self.name]['handled_calls']
        break_time = max(5, min(10, 5 + (handled_calls // 5)))
        await asyncio.sleep(break_time)
        self.calls_since_break = 0
    

    async def run(self) -> None:
        """
        Function which handles calls and adds data for visualization.
        """
        while True:
            call = await self.queue.get()
            handling_time = await self.sim_handling_call()

            self.processed += 1
            self.calls_since_break += 1

            self.data[self.name]["queue_lengths"].append(self.queue.qsize())
            self.data[self.name]["handling_times"].append(handling_time)
            
            if "calls_handled" not in self.data:
                self.data[self.name]['hchandled_calls'] = 0
            self.data[self.name]['handled_calls'] += 1

            self.queue.task_done()

            if self.calls_since_break >= self.break_threshold:
                await self.take_break()