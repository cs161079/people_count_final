"""
simulation.py

Provides Passenger, Simulation classes.
Author: Oulis Nikolaos
Date: 2025-06-25
"""
import os
import random
import threading
import time

from dotenv import load_dotenv
from dependency_injector import providers

from detection.models.route import Route, Stop
from detection.peopleCount import PeopleCount
from detection.rest import ResourceService
from utils.opsw_logger import OpswLogger
from typing import List


class Passenger:
    def __init__(self, name, destination):
        """
        Initializes a new Passenger object.

        Args:
            name (str): The passengers's name (Usually is random ID).
            destination (str): The stop that passenger get off.
        """
        self.name = name
        self.destination = destination
        self.__repr__()

    def __repr__(self):
        return f"{self.name} → {self.destination}"


class Simulation(PeopleCount):
    resourceSrv = providers.Singleton(ResourceService)
    resourceSrv().initialization()

    def __init__(self, thID, stops: List[Stop], stop_delay: int):
        """
        Initializes a new Simulation object. 
        Initialize current_stop_index with 0 and
        passengerArr with empty Array.

        Args:
            routeId (int): The route ID to get stop List from resource.
        """
        super(Simulation, self).__init__(thread_id=thID)
        self.threadId = thID 
        self.stops = stops
        self.stop_delay = stop_delay
        self.current_stop_index = 0
        self.passengersArr = []
        self.stop_event = threading.Event()
        self._finished = False

    def board_passenger(self, passenger):
        """
        Simulate Passengers boarding to bus.

        Args:
            passenger (object): An Instance of Passenger Object.
        """
        self.passengersArr.append(passenger)
        self.passengers = len(self.passengersArr)
        # print(f"🟢 Thread {self.thread_id} {passenger.name} boarded at {self.route[self.current_stop_index]['stop_descr']}")
        self.logger.logger.info(f"🟢 {passenger.name} boarded at {self.stops[self.current_stop_index].stop_descr}")

    def disembark_passengers(self):
        """
        Simulates passenger disembarkation from Bus
        """
        current_stop = self.stops[self.current_stop_index]
        remaining = []
        for p in self.passengersArr:
            if p.destination == current_stop:
                # print(f"🔴 Thread {self.thread_id} {p.name} got off at {current_stop['stop_descr']}")
                self.logger.logger.info(f"🔴 {p.name} got off at {current_stop.stop_descr}")
            else:
                remaining.append(p)
        self.passengersArr = remaining
        self.passengers = len(self.passengersArr)

    def move_to_next_stop(self):
        """
        Simulates Bus moving to next stop.
        """
        if self.current_stop_index < len(self.stops) - 1:
            self.current_stop_index += 1
            # print(f"\nThread {self.thread_id} 🚌 Bus arrived at {self.route[self.current_stop_index]['stop_descr']}")
            self.logger.logger.info(f"\n 🚌 Bus arrived at {self.stops[self.current_stop_index].stop_descr}")
            self.disembark_passengers()
        else:
            # print("\n✅ Route finished. No more stops.")
            self.logger.logger.info(f"\n Thread {self.thread_id}✅ Route finished. No more stops.")

    def _loadEnviromentInternal(self):
        # Θέλουμε μόνο την μεταβλητή Συστήματος delay 
        # χρόνος αναμονής μέχρι τη επόμενη στάση
        stopDelayStr = os.getenv("delay")
        if stopDelayStr != None:
            self.stop_delay = int(stopDelayStr)
        # routeIdStr = os.getenv("route.id")
        # if routeIdStr == None:
        #     raise Exception("Δεν έχει ορισθεί κωδικός διαδρομής λεοφωρείου.")
        # self.routeId = self.strToInt(routeIdStr)

    def run(self):
        """
        It does all the simulation of the bus's movement
        from stop to stop and the boarding and alighting of passengers from it.
        """
        try:

            # Αυτά δεν χρειάζονται θα κάνει το Request ο εξω.
            # last_post = time.time()
            # post_interval = 60  # seconds

            # Ούτε αυτό χρειάζεται θα το κάνει και αυτό ο έξω
            # δεν έχει καμία δουλειά να το κάνει αυτός
            # Από τις μεταβλητές συστήματος θα φωρτόνονται μόνο το Route_id και το 
            # delay ανάμεσα στις στάσεις.

            # self._loadEnviromentInternal()

            while (self.current_stop_index < len(self.stops) - 1) and not self.stop_event.is_set():
                current_stop = self.stops[self.current_stop_index]
                # print(f"\n🚏Thread {self.thread_id} Current stop: {current_stop['stop_descr']}")
                self.logger.logger.info(f"\n🚏 Current stop: {current_stop.stop_descr}")
                
                # Simulate random new passengers
                for _ in range(random.randint(0, 3)):
                    destination_index = random.randint(self.current_stop_index + 1, len(self.stops) - 1)
                    passenger = Passenger(
                        name=f"Passenger{random.randint(100,999)}",
                        destination=self.stops[destination_index]
                    )
                    self.board_passenger(passenger)

                # Check if it's time to post data on backend
                # if time.time() - last_post >= post_interval:
                #     thread = threading.Thread(target=self.updateCapacity)
                #     thread.start()
                #     # self.updateCapacity()
                #     last_post = time.time()
                # print(`f"Thread {self.thread_id} In {self.stop_delay} seconds bus move to next station."`)
                self.logger.logger.info(f"Thread {self.thread_id} In {self.stop_delay} seconds bus move to next station.")
                time.sleep(self.stop_delay)  # Simulate time at stop
                self.move_to_next_stop()
            # print(f"Thread {self.thread_id} Bus complete route. All Passengers got off in terminal")
            if self.stop_event.is_set():
                self.logger.logger.info(f"Thread {self.thread_id} Interrupted from user.")
            else:
                self.logger.logger.info(f"Thread {self.thread_id} Bus complete route. All Passengers got off in terminal")
        except Exception as e:
            self.logger.logger.error(e)
        self._finished = True