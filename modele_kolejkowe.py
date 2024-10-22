import asyncio
import time
import numpy as np

class Consultant:
    def __init__(self, name: str, mu: float):
        self.name = name
        self.mu = mu  # Service rate (calls per unit time)

        self.handled_calls = 0
        self.break_duration = 0
        

    async def handle_call(self, client, wait_time):
        """Function which simulates handling a call."""
        self.handled_calls += 1
        service_time = np.random.exponential(self.mu)  # Call duration based on service rate (mu)
        print(f"{self.name} is handling {client} for {service_time:.2f} seconds "
              f"(Wait time: {wait_time:.2f} seconds)")
        await asyncio.sleep(service_time)
        await self.take_break()

    async def take_break(self):
        """Function which handles break time of consultant between calls."""
        self.break_duration = self.handled_calls * 0.5 # More calls handled = more break time
        print(f"{self.name} is taking a break for {self.break_duration:.2f} seconds")
        await asyncio.sleep(self.break_duration)


async def client_arrival(client_queue, lambda_, num_clients, max_queue_size, rejected_clients):
    """Function which simulates client arrivals using a Poisson process based on lambda (arrival rate)."""
    for i in range(1, num_clients + 1):
        inter_arrival_time = np.random.exponential(lambda_)  # Inter-arrival time based on lambda
        await asyncio.sleep(inter_arrival_time)
        if client_queue.qsize() < max_queue_size:
            arrival_time = time.time()
            await client_queue.put((f"Client-{i}", arrival_time))
            print(f"Client-{i} arrived and was queued after {inter_arrival_time:.2f} seconds")
        else:
            rejected_clients.append(f"Client-{i}") # Rejecting clients who exceeded queue size
            print(f"Client-{i} was rejected (queue is full)")


async def worker(consultant, client_queue, total_wait_time, processed_clients):
    """Handling calls by consultants"""
    while True:
        client, arrival_time = await client_queue.get()  # Get the next client and its arrival time
        wait_time = time.time() - arrival_time  # Calculate how long the client waited
        total_wait_time.append(wait_time)  # Track the waiting time for the client
        await consultant.handle_call(client, wait_time)
        processed_clients.append(client)  # Mark the client as processed
        client_queue.task_done()  # Mark the task as done


async def simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size):
    """Simulates the queueing process with metrics tracking."""
    client_queue = asyncio.Queue()  # The client queue
    total_wait_time = []  # To track waiting times of clients
    processed_clients = []  # Track processed clients
    rejected_clients = []  # Track rejected clients
    
    consultants = [Consultant(f"Consultant-{i}", mu) for i in range(num_consultants)]
    
    tasks = []
    for consultant in consultants:
        task = asyncio.create_task(worker(consultant, client_queue, total_wait_time, processed_clients))
        tasks.append(task)
    
    await client_arrival(client_queue, lambda_, num_clients, max_queue_size, rejected_clients)    
    await client_queue.join()

    for task in tasks:
        task.cancel()
    
    # Report statistics
    # total_clients = len(processed_clients) + len(rejected_clients)
    avg_wait_time = sum(total_wait_time) / len(total_wait_time) if total_wait_time else 0
    print("\n--- Simulation Complete ---")
    print(f"Total clients processed: {len(processed_clients)}")
    print(f"Total clients rejected: {len(rejected_clients)}")
    print(f"Average wait time: {avg_wait_time:.2f} seconds")
    print(f"Queue size limit: {max_queue_size}")
    print(f"Rejected clients: {rejected_clients}")


# Parameters for the simulation
lambda_ = 1.0  # Arrival rate: on average 1 client per second
mu = 0.6  # Service rate: on average 0.8 clients handled per second (mean service time = 1/μ)
num_clients = 30  # Number of clients
num_consultants = 3  # Number of consultants
max_queue_size = 5  # Maximum number of clients allowed in the queue

# Run the simulation
asyncio.run(simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size))
