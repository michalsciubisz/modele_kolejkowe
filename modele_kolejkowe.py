import asyncio
import csv
import time
import numpy as np
import json
import os

sim_start_time = time.time()
queue_from_time = []

class Consultant:
    def __init__(self, name: str, mu: float, logging):
        self.name = name
        self.mu = mu  # Service rate (calls per unit time)

        self.handled_calls = 0
        self.break_duration = 0
        self.time_on_breaks = 0
        self.time_on_calls = 0
        self.time_on_previous_call = 0
        self.logging = logging
        

    async def handle_call(self, client, wait_time):
        """Function which simulates handling a call."""
        self.handled_calls += 1
        service_time = np.random.exponential(self.mu)  # Call duration based on service rate (mu)
        if self.logging:
            print(f"{self.name} is handling {client} for {service_time:.2f} seconds "
                  f"(Wait time: {wait_time:.2f} seconds)")
        await asyncio.sleep(service_time)
        self.time_on_calls += service_time
        await self.take_break()
        self.time_on_previous_call = service_time

    async def take_break(self):
        """Function which handles break time of consultant between calls."""
        self.break_duration = max(self.time_on_previous_call/3, 1)  # At least 1 min break
        if self.logging:
            print(f"{self.name} is taking a break for {self.break_duration:.2f} seconds")
        await asyncio.sleep(self.break_duration)
        self.time_on_breaks += self.break_duration

    def to_dict(self):
        return {
            'handled_calls': self.handled_calls,
            'time_on_calls': self.time_on_calls,
            'time_on_breaks': self.time_on_breaks
        }


async def client_arrival(client_queue, lambda_, num_clients, max_queue_size, rejected_clients, logging):
    """Function which simulates client arrivals using a Poisson process based on lambda (arrival rate)."""
    for i in range(1, num_clients + 1):
        inter_arrival_time = np.random.exponential(lambda_)  # Inter-arrival time based on lambda
        await asyncio.sleep(inter_arrival_time)
        if client_queue.qsize() < max_queue_size:
            arrival_time = time.time()
            await client_queue.put((f"Client-{i}", arrival_time))
            if logging:
                print(f"Client-{i} arrived and was queued after {inter_arrival_time:.2f} seconds")
            else:
                queue_from_time.append((client_queue.qsize(), arrival_time-sim_start_time))
        else:
            rejected_clients.append(f"Client-{i}") # Rejecting clients who exceeded queue size
            if logging:
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
        queue_from_time.append((client_queue.qsize(), time.time()-sim_start_time))


async def simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size, sim_name, logging=True):
    """Simulates the queueing process with metrics tracking."""
    client_queue = asyncio.Queue()  # The client queue
    total_wait_time = []  # To track waiting times of clients
    processed_clients = []  # Track processed clients
    rejected_clients = []  # Track rejected clients
    
    consultants = [Consultant(f"Consultant-{i}", mu, logging) for i in range(num_consultants)]
    
    tasks = []
    for consultant in consultants:
        task = asyncio.create_task(worker(consultant, client_queue, total_wait_time, processed_clients))
        tasks.append(task)
    
    await client_arrival(client_queue, lambda_, num_clients, max_queue_size, rejected_clients, logging)
    await client_queue.join()

    for task in tasks:
        task.cancel()
    
    # Report statistics
    # total_clients = len(processed_clients) + len(rejected_clients)
    avg_wait_time = sum(total_wait_time) / len(total_wait_time) if total_wait_time else 0
    if logging:
        print("\n--- Simulation Complete ---")
        print(f"Total clients processed: {len(processed_clients)}")
        print(f"Total clients rejected: {len(rejected_clients)}")
        print(f"Average wait time: {avg_wait_time:.2f} seconds")
        print(f"Queue size limit: {max_queue_size}")
        print(f"Rejected clients: {rejected_clients}")
    else:
        save_to_csv(queue_from_time, sim_name)
        data = {
            'total_clients_processed': len(processed_clients),
            'total_clients_rejected': len(rejected_clients),
            'average_wait_time': avg_wait_time,
            'queue_size_limit': max_queue_size,
            'rejected_clients': rejected_clients,
            'consultants': [consultant.to_dict() for consultant in consultants]
        }
        save_to_json(data, sim_name)

def save_to_csv(data, file_name):
    headers = ["Queue_size", "Time"]
    if not os.path.exists("results"):
        os.makedirs("results")
    path = os.path.join("results", file_name+".csv")
    with open(path, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(headers)
        for value, time in data:
            writer.writerow([value, time])

def save_to_json(data, file_name):
    if not os.path.exists("results"):
        os.makedirs("results")
    path = os.path.join("results", file_name+".json")
    with open(path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_parameters_from_file(path):
    with open(path, 'r') as file:
        return json.load(file)

def run_all_simulations():
    parameters = load_parameters_from_file("parameters.json")
    if len(parameters.items()) == 0:
        # Parameters for the simulation
        lambda_ = 1.0  # Arrival rate: on average 1 client per second
        mu = 0.6  # Service rate: on average 0.8 clients handled per second (mean service time = 1/μ)
        num_clients = 30  # Number of clients
        num_consultants = 3  # Number of consultants
        max_queue_size = 5  # Maximum number of clients allowed in the queue
        asyncio.run(simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size, "default"))
    else:
        live_logging = True
        for sim_name, params in parameters.items():
            if sim_name == "live_logging":
                live_logging = params
            else:
                lambda_ = params['lambda']
                mu = params['mu']
                num_clients = params['num_clients']
                num_consultants = params['num_consultants']
                max_queue_size = params['max_queue_size']
                asyncio.run(simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size, sim_name, live_logging))

# Run the simulation

# asyncio.run(simulate_queue(lambda_, mu, num_clients, num_consultants, max_queue_size))
run_all_simulations()