from datetime import timedelta, timezone, datetime
import os
from typing import List
import zoneinfo
import cv2
from dotenv import load_dotenv
from detection.models.line import Line
from detection.models.route import Route, Stop
from detection.peopleCount import PeopleCount
from detection.rest import ResourceService
from utils.opsw_logger import OpswLogger
from dependency_injector import providers
from detection.simulation import Simulation
import threading
import time
import sched
from InquirerPy import inquirer
from detection.rest import Schedule

class Container:
    logger = logger = providers.Singleton(OpswLogger)
    logger().initialization()
    resourceSrv = providers.Singleton(ResourceService)
    resourceSrv().initialization()
    threadsArray: list[PeopleCount] = []
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler_stop_event = threading.Event()
    line_code = -1
    route_code = -1
    direction = -1
    run_ones = False

    def _initialize_enviroment(self):
        load_dotenv()

        busIDStr = os.getenv("bus.id")
        if busIDStr == None:
            raise Exception("No bus ID has been set.")
        self.bus_id = int(busIDStr)

        busCapStr = os.getenv("bus.capacity")
        if busCapStr == None:
            raise Exception("No bus capacity has been set.")
        self.bus_capacity = int(busCapStr)

        delayStr = os.getenv("deamon.delay")
        if delayStr == None:
            # raise Exception("No deamon delay has been set.")
            self.deamon_delay = 10
        else:
            self.deamon_delay = int(delayStr)

        self.mode = os.getenv("mode")
        runOnesStr = os.getenv("run_ones")
        if runOnesStr != None:
            self.run_ones = bool(runOnesStr)


    def run(self):
        # Αρχικοποιήση μεταβλητών από enviroment variables
        self._initialize_enviroment()
        # Αρχικοποιήση του Logger
        self.logger().initialization()
        # Έλεγχος του Mode που θα δουλέψει simulation ή production
        if self.mode == "s":
            self._simulation_master()
        else:
            self.realTask()

    def _fixSchedule(self, schedules: list[Schedule]) -> list[Schedule]:
        result: list[Schedule] = []
        now = datetime.now().time()
        result = sorted(
            [s for s in schedules if s.start_time > now],
            key=lambda x: x.start_time
        )   
        return result
    
    def _simulation_master(self):
        # Ανάκτηση πληροφοριών για την διαδρομή για να ξέρει πως θα κάνει το Simulation
        route = self.resourceSrv().getRouteDetails(self.route_code)
        # Ανάκτηση δρομολογίων στην περίπτωση που θέλουμε να κάνει Simulation για όλα τα δρομολόγια
        # από αμέσω επόμενο μέχρι το τελευταίο.
        scheduleTimes = self.resourceSrv().getScheduleProgram(self.line_code, self.direction)
        timeNow = datetime.now().time()
        future_times = [t for t in scheduleTimes if t.start_time > timeNow]
        # Στην περίπτωση που κάνει μόνο μία εκτέλεση
        if self.run_ones:
            oneSchedule = future_times[0]
            print(f" Θα εκτελέσουμε αναπαράσταση κίνησης λεοφωρείου για την διαδρομη {route.code} {route.descr} μία φορά.")

            # Αυτές είναι ώρες έναρξης και λήξης του δρομολογίου
            start_time = oneSchedule.start_time   # type: datetime.time
            end_time   = oneSchedule.end_time     # type: datetime.time

            # Ημερομηνία για το τώρα
            tz = zoneinfo.ZoneInfo("Europe/Athens")
            today = datetime.now(tz)
            # today = datetime.today().date()
            print(f" {today.isoformat() }")

            # Δημιουργούμε ημερομηνίες έναρξης λήξης με την σημερινή ημερομηνία και ώρα από το δρομολόγιο
            start_dt = datetime.combine(today, start_time)
            end_dt   = datetime.combine(today, end_time)

            print(f" {start_dt.isoformat() } -> {end_dt.isoformat()}")

            # Στην περίπτωση που η ώρα λήξης είναι μικρότερη από την ώρα έναρξης τότε αυτό σημαίνει ότι η λήξης είναι
            # την επόμενη ημέρα. Οπότε προσθετουμε μία ημέρα στην ημερομηνία λήξης.
            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            difference = end_dt - start_dt
            print(difference.total_seconds(), "seconds")
            stop_delay = round(difference.total_seconds() / len(route.stops), 2)
            print(f"Διάστημα μεταξύ στάσεων {stop_delay} δευτερόλεπτα")

            # oneSchedule.start_time = datetime.now()
            # # Convert to datetime
            # start_dt = datetime.combine(today, oneSchedule.start_time)

            # # Add the timedelta
            # end_dt = start_dt + difference

            # # If you only want the time part back:
            # oneSchedule.end_time = end_dt.time()
            t = threading.Thread(target=self._simulationTask_internal_ones, args=(route.stops, stop_delay,
                                                                                  oneSchedule.sdc_code, start_dt,))
            t.start()
        # Στην περίπτωση που εκτελεί όλα τα δρομολόγια από την ώρα έναρξης του Simulation και μετά
        else:    
            sortedSchedule = self._fixSchedule(future_times)

            print(f" Θα εκτελέσουμε αναπαράσταση κίνησης λεωφορείου για την διαδρομη {route.code} {route.descr}")

            for schd in sortedSchedule:
                t = threading.Thread(target=self._simulationTask_internal, args=(route, schd))
                t.start()
                t.join()
    
    # def _simulationTask_internal_ones(self, stops: List[Stop], stop_delay: int,
    #                                   sdc_code: int, start_date: datetime):
    #     now = datetime.now()
    #     wait_seconds = (start_date - now).total_seconds()
    #     if wait_seconds > 0:
    #         print(f"Will wait for {wait_seconds / 60} minutes until the route starts!")
    #         time.sleep(wait_seconds)
    #     for i in range(1, 4):
    #         t = Simulation(i, stops, stop_delay)
    #         self.threadsArray.append(t)
    #         t.start()
    #         self.logger().logger.info(f"Simulation thread with ID {t.thread_id} created and started successfully.")

    #     # Start scheduler in separate thread
    #     scheduler_thread = threading.Thread(target=self._start_scheduler, args=(sdc_code, start_date))
    #     scheduler_thread.start()
    #     try:
    #         while True:
    #             if self.scheduler_stop_event.is_set():
    #                 break
    #             # time.sleep(0.5)
    #     except KeyboardInterrupt:
    #         print("❗ KeyboardInterrupt triggered.")
    #         self.scheduler_stop_event.set()
        
    #     # Shutdown logic
    #     self._stopAllThreads()
    #     # scheduler_stop_event.set()
    #     print("Stop Thread for Scheduler.")
    #     scheduler_thread.join()
    #     print("All threads have stopped.")

    def _simulationTask_internal_ones(self, stops: List[Stop], stop_delay: int,
                                  sdc_code: int, start_date: datetime):
        stop = self.scheduler_stop_event  # threading.Event
        scheduler_thread = None

        try:
            # 1) Interruptible wait until start time
            now = datetime.now()
            wait_seconds = max(0, (start_date - now).total_seconds())
            if wait_seconds > 0:
                print(f"Will wait for {wait_seconds/60:.1f} minutes until the route starts!")
                # returns early if 'stop' is set (e.g., on Ctrl+C below)
                stop.wait(timeout=wait_seconds)

            if stop.is_set():
                return  # interrupted before start

            # 2) Start worker threads
            for i in range(1, 4):
                t = Simulation(i, stops, stop_delay)
                t.daemon = True  # let process exit even if a worker misbehaves
                self.threadsArray.append(t)
                t.start()
                self.logger().logger.info(
                    f"Simulation thread with ID {t.thread_id} created and started successfully."
                )

            # 3) Start scheduler in separate thread (must check 'stop' inside!)
            scheduler_thread = threading.Thread(
                target=self._start_scheduler, args=(sdc_code, start_date), daemon=True
            )
            scheduler_thread.start()

            # 4) Park main thread without busy spinning; Ctrl+C lands here
            while not stop.wait(0.2):
                pass

        except KeyboardInterrupt:
            print("❗ Ctrl+C received. Shutting down…")
            stop.set()

        finally:
            # 5) Ask everything to stop and join with timeouts so we don't hang
            self._stopAllThreads()   # ensure your Simulation threads observe 'stop' or similar
            if scheduler_thread is not None:
                scheduler_thread.join(timeout=5)
                if scheduler_thread.is_alive():
                    print("Scheduler didn't exit in time; continuing shutdown (daemon thread).")

        # Join workers with short heartbeats so signals remain responsive
        for t in list(self.threadsArray):
            if t.is_alive():
                for _ in range(20):          # ~10s total
                    t.join(timeout=0.5)
                    if not t.is_alive():
                        break
        print("All threads have stopped.")

    def _simulationTask_internal(self, stops: List[Stop], stop_delay: int, schedule: Schedule):
        print("Thread ID (inside):", threading.get_ident())
        now = datetime.now()

        dt_start_time = datetime.combine(datetime.today(), schedule.start_time)

        wait_seconds = (dt_start_time - now).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        for i in range(1, 4):
                t = Simulation(i, stops, stop_delay)
                self.threadsArray.append(t)
                t.start()
                self.logger().logger.info(f"Simulation thread with ID {t.thread_id} created and started successfully.")

        # Start scheduler in separate thread
        scheduler_thread = threading.Thread(target=self._start_scheduler, args={schedule})
        scheduler_thread.start()

        try:
            while True:
                if self.scheduler_stop_event.is_set():
                    break
                # time.sleep(0.5)
        except KeyboardInterrupt:
            print("❗ KeyboardInterrupt triggered.")
            self.scheduler_stop_event.set()
        
        # Shutdown logic
        self._stopAllThreads()
        # scheduler_stop_event.set()
        print("Stop Thread for Scheduler.")
        scheduler_thread.join()
        print("All threads have stopped.")
    
    def enumerate_cameras(self, max_index=10):
        available = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
    
    # Είναι η μέθοδος για παραγωγικό περιβάλλον η οποία φτιάχνει 
    # τόσα thread όσα και οι κάμερες
    def realTask(self):
        for camera_info in self.enumerate_cameras(3):
            # print(f'{camera_info.index}: {camera_info.name}')
            t = PeopleCount(camera_info.index, camera_info.index)
            self.logger().logger.info(f"Simulation thread with ID {t.thread_id} created successfully.")
            self.threadsArray.append()
            t.start()
        # Start scheduler in separate thread
        scheduler_thread = threading.Thread(target=self._start_scheduler)
        scheduler_thread.start()

        try:
            while True:
                if self.scheduler_stop_event.is_set():
                    break
                # time.sleep(0.5)
        except KeyboardInterrupt:
            print("❗ KeyboardInterrupt triggered.")
            self.scheduler_stop_event.set()
        
        # Shutdown logic
        self._stopAllThreads()
        # scheduler_stop_event.set()
        print("Stop Thread for Scheduler.")
        scheduler_thread.join()
        print("All threads have stopped.")            

    def _start_scheduler(self, sdc_code: int, start_date: datetime):
        self.scheduler.enter(self.deamon_delay, 1, self._update_capacity, argument=(sdc_code, start_date,))
        self.scheduler.run()

    def _update_capacity(self, sdc_code: int, start_date: datetime):
        if all(th.thread_finished() for th in self.threadsArray):
            self.scheduler_stop_event.set()
            return
        totalCount = sum(th.getPassengers() for th in self.threadsArray)
        print("---------------------------------------")
        print(f"Total count from threads: {totalCount}")
        print("---------------------------------------")
        tz = zoneinfo.ZoneInfo("Europe/Athens")
        currentTime: time = datetime.now(tz)
        self.resourceSrv().postCapacity(self.route_code, self.bus_id, sdc_code, start_date,
                                        self.bus_capacity, totalCount, currentTime)

        self.scheduler.enter(self.deamon_delay, 1, self._update_capacity, argument=(sdc_code, start_date,))



    def _stopAllThreads(self):
        print("Stops all threads from thread Array.")
        # Stop all worker threads
        for t in self.threadsArray:
            t.stop()
        for t in self.threadsArray:
            t.join()

    def _try_again(self, resultRec, trySenu):
        return resultRec is None and (trySenu <= 3)
    
    def _promt_seacrh_line(self) -> int | None :
        lines = None
        try:
            while True: 
                line_search =input("Δώσατε κείμενο αναζήτησης: ") 
                lines: List[Line] = self.resourceSrv().getLineList(line_search)
                if lines is None:
                    print(f"Δεν βρέθηκαν αποτελέσματα με αυτό το κείμενο [{line_search}]")
                    continue
                for line in lines:
                    print(f"[{line.id}] {line.code} - {line.descr}")
                is_continue = input("Θελετε να δοκιμάσετε με άλλο κέιμενο [y/N]?")
                if is_continue == 'n' or is_continue == 'N':
                    break
                else:
                    os.system('cls' if os.name == 'nt' else 'clear')
            # Clear command depending on OS
            os.system('cls' if os.name == 'nt' else 'clear')

            if(len(lines) != 0):
                lineChoice = []
                for line in lines:
                    lineChoice.append({"name": f"{line.code} {line.descr}", "value": line.code})
                # Prompt user
                selected_line = inquirer.select(
                    message="Επιλέξτε Γραμμή:",
                    choices=lineChoice,
                    pointer="*"
                ).execute()
                return selected_line
            else:
                return None
        except KeyboardInterrupt:
            print("\nΑκύρωση από τον χρήστη (Ctrl+C).")
            return None
        

    def prompt_line(self) -> bool:
        self.line_code = self._promt_seacrh_line()
        if self.line_code == None:
            return False
        routes = self.resourceSrv().getRoutesByLineCode(self.line_code)

        routeChoices = []
        for route in routes:
            routeType = route['route_type']
            if routeType == 2:
                routeType = 0
            routeChoices.append({"name": route['descr'],
                                    "value": {"code" : route['code'], "direction": routeType}})

        # Prompt user
        selectedRouteRec = inquirer.select(
            message="Επιλέξτε διαδρομή:",
            choices=routeChoices,
            pointer="*"
        ).execute()

        self.route_code = selectedRouteRec["code"]
        self.direction = selectedRouteRec["direction"]
        return True


def main():
    print("  ___    _    ____    _                                                         ")
    print(" / _ \\  / \\  / ___|  / \\                                                        ")
    print("| | | |/ _ \\ \\___ \\ / _ \\                                                       ")
    print("| |_| / ___ \\ ___) / ___ \\                                                      ")
    print(" \\___/_/___\\_\\____/_/_  \\_\\                                                     ")
    print("         _____  ____  ___  ____  _     _____       ____ ___  _   _ _   _ _____  ")
    print("         |  _ \\| ____/ _ \\|  _ \\| |   | ____|     / ___/ _ \\| | | | \\ | |_   _| ")
    print("         | |_) |  _|| | | | |_) | |   |  _|      | |  | | | | | | |  \\| | | |   ")
    print("         |  __/| |__| |_| |  __/| |___| |___     | |__| |_| | |_| | |\\  | | |   ")
    print("         |_|   |_____\\___/|_|   |_____|_____|     \\____\\___/ \\___/|_| \\_| |_|   ")
    container = Container()
    if not container.prompt_line():
        return
    container.run()

    
    

    # Για κάθε κάμερα θα δημιουργούμε ένα thread το οποίο θα μετράει τους 
    # επιβάτες και θα ενημερώνει την κεντρική κλάσση. Αυτή θα ενημερώνει και 
    # τον Server.

    # for camera_info in enumerate_cameras(cv2.CAP_MSMF):
    #     print(f'{camera_info.index}: {camera_info.name}')
    
    # logger().initialization()
    # logger().logger.info("Logger Initialized and start main container.")
    # obj = PeopleCount(busId, busCapacity, server)
    # obj.run()
    


if __name__ == "__main__":
    main()