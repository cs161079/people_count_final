from dataclasses import dataclass
from datetime import datetime
import os
import time
from typing import Any, Dict, List
from dotenv import load_dotenv
import requests
from dependency_injector import providers

from detection.models.line import Line
from detection.models.route import Route, Stop
from utils.opsw_logger import OpswLogger

@dataclass
class Schedule:
    line_code: int
    sdc_code: int
    start_time: time 
    end_time: time
    sort: int
    direction: int

class AuthService:
    logger = providers.Singleton(OpswLogger)
    def __init__(self):
        self.url = None
        self.client_id = None
        self.username = None
        self.password = None

    def inialize(self):
        # Load Application Properties
        load_dotenv()
    
class ResourceService:
    logger = providers.Singleton(OpswLogger)
    def __init__(self):
        self.url = None
    def initialization(self):
        # Load Application Properties
        load_dotenv()
        tmpUrl = os.getenv("SERVER_URL")
        if(tmpUrl == None):
            raise "Enviroment variable with SERVER_URL key does not exists"
        self.url = tmpUrl
        self.logger().logger.info(f"Resourece Server url set {self.url}")

    def postCapacity(self, routeId: int, busId: int, sdc_code: int, start_time: datetime, busCapacity: int,
                    passengers: int, currentTime: datetime):     
        url = f"{self.url}/api/v1/ext/capacity/{routeId}/{busId}"
        try:
            data = {
                # "start_time": f"{start_time.isoformat()}Z",
                "sdc_code": sdc_code,
                "capacity": busCapacity,
                "passengers": passengers,
                "time": currentTime.isoformat(timespec="seconds").replace("+03:00", "Z")
            }

            headers = {
            }
            r = requests.post(url, json=data, headers=headers)
            # if r.status_code == 401:
            #     return self.postCapacity(busId, busCapacity, sdc_code, start_time, passengers, currentTime)
            # else:
            self.logger().logger.info(f"{str(r.status_code)}: {r.text}")
        except Exception as e:
            self.logger().logger.info(f"Error: {e}")

    @staticmethod
    def _to_stop(s: Dict[str, Any]) -> Stop:
        # Map API keys -> dataclass fields. Adjust keys to match your API.
        return Stop(
            stop_code=s.get("stop_code"),
            stop_descr=s.get("stop_descr"),
            stop_lat=s.get("stop_lat"),
            stop_lng=s.get("stop_lng"),
            stop_senu=s.get("stop_senu")
        )

    def getRouteDetails(self, route_id) -> Route:
        result: Route
        stops: List[Stop] = []
        url = f"{self.url}/api/v1/ext/stops/{route_id}"
        try:
            headers = {
            }
            r = requests.get(url, headers = headers)
            bd = r.json()
            # if r.status_code == 401:
            #     return self.getRouteDetails(route_id)
            if r.status_code == 200:
                raw_stops = bd['stops']
                for s in raw_stops:
                    stops.append(self._to_stop(s))
                result = Route(bd['code'], bd['descr'], stops)
            else:
                raise requests.exceptions.HTTPError(bd['error'])
        except requests.exceptions.HTTPError as e:
            raise Exception("Resource Server Error. " + e.args[0])
        except requests.exceptions.RequestException as e:
            print("⚠️ Request failed:", e)
        except Exception as e:
            raise e
        return result
    
    @staticmethod
    def _to_line(s: Dict[str, Any]) -> Line:
        # Map API keys -> dataclass fields. Adjust keys to match your API.
        return Line(
            id=s.get("id"),
            code=s.get("line_code"),
            descr = s.get("line_descr")
        )
    
    def getLineList(self, line_search) -> List[Line]:
        lines: List[Line] = []
        url = f"{self.url}/api/v1/lines/search?text={line_search}"
        try:
            headers = {
            }
            r = requests.get(url, headers = headers)
            bd = r.json()
            # if r.status_code == 401:
            #     return self.getLineList(line_search)
            if r.status_code == 200:
                raw_lines = bd['data']
                for l in raw_lines:
                    lines.append(self._to_line(l))
            else:
                raise requests.exceptions.HTTPError(bd['error'])
        except requests.exceptions.HTTPError as e:
            raise Exception("Resource Server Error. " + e.args[0])
        except requests.exceptions.RequestException as e:
            print("⚠️ Request failed:", e)
        except Exception as e:
            raise e
        return lines
    
    def getRoutesByLineCode(self, line_code):
        routes = []
        url = f"{self.url}/api/v1/ext/routes/{line_code}"
        try:
            headers = {
            }
            r = requests.get(url, headers = headers)
            bd = r.json()
            # if r.status_code == 401:
            #     return self.getRoutesByLineCode(line_code)
            if r.status_code == 200:
                routes = bd
            else:
                raise requests.exceptions.HTTPError(bd['error'])
        except requests.exceptions.HTTPError as e:
            raise Exception("Resource Server Error. " + e.args[0])
        except requests.exceptions.RequestException as e:
            print("⚠️ Request failed:", e)
        except Exception as e:
            raise e
        return routes
    
    def getScheduleProgram(self, line_code, direction) -> list[Schedule]:
        scheduleTimes: list[Schedule] = []
        url = f"{self.url}/api/v1/ext/schedule/{line_code}/{direction}"
        try:
            headers = {
            }
            r = requests.get(url, headers = headers)
            bd = r.json()
            # if r.status_code == 401:
            #     return self.getScheduleProgram(line_code)
            if r.status_code == 200:
                scheduleTimes = [
                    Schedule(
                        line_code=item["line_code"],
                        sdc_code=item["sdc_code"],
                        start_time=datetime.strptime(item["start_time"], "%H:%M:%S").time(),
                        end_time=datetime.strptime(item["end_time"], "%H:%M:%S").time(),
                        sort=item["sort"],
                        direction=item["direction"]
                    )
                    for item in bd
                ]
            else:
                raise requests.exceptions.HTTPError(bd['error'])
        except requests.exceptions.HTTPError as e:
            raise Exception("Resource Server Error. " + e.args[0])
        except requests.exceptions.RequestException as e:
            print("⚠️ Request failed:", e)
        except Exception as e:
            raise e
        return scheduleTimes